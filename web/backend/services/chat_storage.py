"""
Web storage stats + rolling-90-day cleanup cycle.

Web vs desktop
--------------
Desktop's storage cleanup is **manual**: the user opens a panel,
ticks categories, hits Clean. We can do that on the desktop because
each workspace is a real user folder and the user has a clear mental
model of "this folder's chats".

Web has a different shape. Every chat auto-creates its own sandbox
workspace (1:1), there's no folder concept, and a steady cadence of
new chats means storage just grows. Asking the user to manually
visit a settings panel every quarter doesn't work — they won't.

So we do the inverse: a **rolling 90-day cycle** that automatically
sweeps every user-removable artifact older than the cycle window.
The frontend gets a banner 5 days before each sweep so power users
who want to opt out / "Clean now" / extend can do so.

What gets swept
---------------
Three categories, all aged out at 90 days:
  * **chats** — sessions whose ``last_used`` is older than 90 days.
    Cleanup deletes the session record + its chat dir.
  * **audits** — JSONL rows with ``ts`` older than 90 days. Append-
    only file rewritten without the old rows.
  * **uploads** — files in ``<ws>/workspace/uploads/`` older than
    90 days by mtime.

Things we deliberately don't touch
----------------------------------
  * BYOK config (per-user, never auto-clean).
  * Billing usage SQLite (compliance / reconciliation).
  * Workspace records themselves (they're cheap; the chats inside
    them are the actual disk pressure).

Cycle state
-----------
``cycle_status_for_user(uid)`` returns:
  next_cycle_at:    ISO-8601 of the next scheduled sweep
  days_until_cycle: floor((next - now).total_seconds() / 86400)
  last_cycle_at:    when the last sweep ran (or None on a fresh
                    account)
  eligible_*:       counts the SPA can show in the banner copy
                    BEFORE the sweep runs

The banner triggers 5 days before ``next_cycle_at`` and stops
showing once the sweep has run.

State store
-----------
We piggyback on user_prefs (already a per-user JSON store). One
key per user: ``last_storage_cycle_at`` = ISO-8601. Cycle math
reads that and adds 90 days to compute the next.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from config import DATA_ROOT
from services.registry import Registry

logger = logging.getLogger(__name__)


# ── Cycle defaults ─────────────────────────────────────────────────
DEFAULT_CYCLE_DAYS = 90
DEFAULT_BANNER_LEAD_DAYS = 5


def cycle_days() -> int:
    raw = (os.environ.get("PI_STORAGE_CYCLE_DAYS", "") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_CYCLE_DAYS


def banner_lead_days() -> int:
    raw = (os.environ.get("PI_STORAGE_BANNER_LEAD_DAYS", "") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return DEFAULT_BANNER_LEAD_DAYS


# ── Per-user session helpers ───────────────────────────────────────
def _user_sessions(user_id: str) -> list[dict[str, Any]]:
    """Every session whose parent workspace is owned by ``user_id``,
    sorted by ``last_used`` DESC (newest first).
    """
    reg = Registry.instance()
    owned = set(reg.workspaces_owned_by(user_id))
    return [
        s for s in reg.list_sessions(workspace_id=None)
        if s.get("workspace_id") in owned
    ]


def chat_dir_size(sid: str) -> int:
    chat_dir = DATA_ROOT / "chats" / sid
    if not chat_dir.is_dir():
        return 0
    total = 0
    try:
        for entry in chat_dir.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
    except OSError:
        return 0
    return total


# ── Cycle state (last/next sweep timestamp) ────────────────────────
def _cycle_state_path(user_id: str) -> Path:
    """Per-user cycle marker file. Lives next to the existing
    user_prefs JSON so the same backup/restore tooling covers both.
    """
    return DATA_ROOT / "users" / user_id / "storage_cycle.json"


def _read_cycle_state(user_id: str) -> dict[str, Any]:
    path = _cycle_state_path(user_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_cycle_state(user_id: str, payload: dict[str, Any]) -> None:
    path = _cycle_state_path(user_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("chat_storage: cannot persist cycle state for %s: %s", user_id, exc)


def _next_cycle_at(last_iso: str | None, days: int) -> datetime:
    """When the next sweep should fire. For a brand-new account
    (no ``last_iso``) we pretend the last cycle was "now" so the
    banner doesn't fire on day 1; new accounts get a full ``days``
    window before their first cleanup."""
    now = datetime.now(timezone.utc)
    last = _parse_iso(last_iso) or now
    return last + timedelta(days=days)


def _parse_iso(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Cycle status (frontend banner data) ────────────────────────────
def cycle_status_for_user(user_id: str) -> dict[str, Any]:
    """Snapshot the cycle state for the frontend.

    Always returns the same shape — even on a brand-new account or
    a corrupt state file — so the SPA can render unconditionally.
    """
    days = cycle_days()
    state = _read_cycle_state(user_id)
    last = state.get("last_cycle_at")
    next_at = _next_cycle_at(last, days)
    now = datetime.now(timezone.utc)
    days_until = max(0, (next_at - now).days)

    # Compute what WOULD be cleaned if the sweep ran right now.
    cutoff = now - timedelta(days=days)
    pending = _eligible_summary(user_id, cutoff)

    show_banner = days_until <= banner_lead_days()

    return {
        "cycle_days": days,
        "banner_lead_days": banner_lead_days(),
        "next_cycle_at": next_at.isoformat(),
        "last_cycle_at": last,
        "days_until_cycle": days_until,
        "show_banner": show_banner,
        "pending": pending,
    }


def _eligible_summary(user_id: str, cutoff: datetime) -> dict[str, Any]:
    """How many items / bytes would the sweep remove right now?"""
    cutoff_ts = cutoff.timestamp()

    # Chats
    sessions = _user_sessions(user_id)
    chat_count = 0
    chat_bytes = 0
    for s in sessions:
        last_used = _parse_iso(s.get("last_used") or s.get("created_at"))
        if last_used is None or last_used >= cutoff:
            continue
        chat_count += 1
        chat_bytes += chat_dir_size(s["id"])

    # Audits + uploads (per workspace)
    reg = Registry.instance()
    audit_rows = 0
    audit_bytes = 0
    upload_files = 0
    upload_bytes = 0
    for wsid in reg.workspaces_owned_by(user_id):
        ar, ab = _audit_eligible(wsid, cutoff)
        audit_rows += ar
        audit_bytes += ab
        uf, ub = _uploads_eligible(wsid, cutoff_ts)
        upload_files += uf
        upload_bytes += ub

    total_bytes = chat_bytes + audit_bytes + upload_bytes
    total_count = chat_count + audit_rows + upload_files

    return {
        "total_count": total_count,
        "total_bytes": total_bytes,
        "chats": {"count": chat_count, "bytes": chat_bytes},
        "audits": {"count": audit_rows, "bytes": audit_bytes},
        "uploads": {"count": upload_files, "bytes": upload_bytes},
    }


# ── Cycle execute (the actual sweep) ───────────────────────────────
def run_cycle_for_user(user_id: str, *, force: bool = False) -> dict[str, Any]:
    """Execute the rolling sweep for ``user_id``.

    By default we no-op if the next cycle is still in the future
    — protects the public POST endpoint from a malicious "run
    cycle every second" loop. ``force=True`` is the manual "Clean
    now" button: the user explicitly opted in.

    Returns a per-category result map plus the new cycle state.
    """
    days = cycle_days()
    state = _read_cycle_state(user_id)
    last = state.get("last_cycle_at")
    next_at = _next_cycle_at(last, days)
    now = datetime.now(timezone.utc)
    if not force and now < next_at:
        return {
            "ran": False,
            "reason": "not_due",
            "next_cycle_at": next_at.isoformat(),
            "results": {},
        }

    cutoff = now - timedelta(days=days)
    results = {
        "chats": _cleanup_chats(user_id, cutoff),
        "audits": _cleanup_audits(user_id, cutoff),
        "uploads": _cleanup_uploads(user_id, cutoff.timestamp()),
    }

    new_iso = now.isoformat()
    _write_cycle_state(user_id, {"last_cycle_at": new_iso})

    return {
        "ran": True,
        "ran_at": new_iso,
        "next_cycle_at": (now + timedelta(days=days)).isoformat(),
        "results": results,
    }


# ── Per-category sweep helpers ─────────────────────────────────────
def _cleanup_chats(user_id: str, cutoff: datetime) -> dict[str, Any]:
    reg = Registry.instance()
    deleted_count = 0
    freed_bytes = 0
    deleted_ids: list[str] = []
    for sess in _user_sessions(user_id):
        last_used = _parse_iso(sess.get("last_used") or sess.get("created_at"))
        if last_used is None or last_used >= cutoff:
            continue
        sid = sess.get("id")
        if not isinstance(sid, str):
            continue
        size = chat_dir_size(sid)
        try:
            reg.delete_session(sid)
        except KeyError:
            continue
        except Exception as exc:
            logger.warning("chat_storage: failed to delete %s: %s", sid, exc)
            continue
        freed_bytes += size
        deleted_count += 1
        deleted_ids.append(sid)
    if deleted_count:
        logger.info(
            "chat_storage: cycle deleted %d chats (%d bytes) for user=%s",
            deleted_count,
            freed_bytes,
            user_id,
        )
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_ids,
    }


def _cleanup_audits(user_id: str, cutoff: datetime) -> dict[str, Any]:
    reg = Registry.instance()
    deleted_count = 0
    freed_bytes = 0
    for wsid in reg.workspaces_owned_by(user_id):
        out = _trim_audit_file(wsid, cutoff)
        deleted_count += out["deleted_count"]
        freed_bytes += out["freed_bytes"]
    if deleted_count:
        logger.info(
            "chat_storage: cycle trimmed %d audit rows (%d bytes) for user=%s",
            deleted_count,
            freed_bytes,
            user_id,
        )
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": [],
    }


def _cleanup_uploads(user_id: str, cutoff_ts: float) -> dict[str, Any]:
    reg = Registry.instance()
    deleted_count = 0
    freed_bytes = 0
    deleted_names: list[str] = []
    for wsid in reg.workspaces_owned_by(user_id):
        out = _trim_uploads(wsid, cutoff_ts)
        deleted_count += out["deleted_count"]
        freed_bytes += out["freed_bytes"]
        deleted_names.extend(out["deleted_ids"])
    if deleted_count:
        logger.info(
            "chat_storage: cycle removed %d uploads (%d bytes) for user=%s",
            deleted_count,
            freed_bytes,
            user_id,
        )
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_names,
    }


# ── Audit-file helpers (shared with stats + cleanup) ───────────────
def _audit_path(wsid: str) -> Path:
    return DATA_ROOT / "audits" / f"{wsid}.jsonl"


def _audit_eligible(wsid: str, cutoff: datetime) -> tuple[int, int]:
    path = _audit_path(wsid)
    if not path.exists() or not path.is_file():
        return (0, 0)
    rows = 0
    bytes_ = 0
    try:
        with path.open("rb") as fh:
            for raw in fh:
                ts = _parse_audit_ts(raw)
                if ts is not None and ts < cutoff:
                    rows += 1
                    bytes_ += len(raw)
    except OSError:
        return (0, 0)
    return (rows, bytes_)


def _trim_audit_file(wsid: str, cutoff: datetime) -> dict[str, int]:
    path = _audit_path(wsid)
    if not path.exists() or not path.is_file():
        return {"deleted_count": 0, "freed_bytes": 0}
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    deleted_count = 0
    freed_bytes = 0
    try:
        with path.open("rb") as src, tmp_path.open("wb") as dst:
            for raw in src:
                ts = _parse_audit_ts(raw)
                if ts is not None and ts < cutoff:
                    deleted_count += 1
                    freed_bytes += len(raw)
                    continue
                dst.write(raw)
        tmp_path.replace(path)
    except OSError as exc:
        logger.warning(
            "chat_storage: trim_audit_file(%s) failed: %s", wsid, exc
        )
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return {"deleted_count": 0, "freed_bytes": 0}
    return {"deleted_count": deleted_count, "freed_bytes": freed_bytes}


def _parse_audit_ts(raw: bytes) -> Optional[datetime]:
    try:
        row = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(row, dict):
        return None
    ts = row.get("ts")
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Uploads helpers ────────────────────────────────────────────────
def _uploads_dir(wsid: str) -> Optional[Path]:
    rec = Registry.instance().get_workspace(wsid)
    if not rec:
        return None
    base = Path(rec.get("path", "")).expanduser()
    if not base.exists():
        return None
    if rec.get("mode") == "desktop":
        return base / "uploads"
    return base / "workspace" / "uploads"


def _uploads_eligible(wsid: str, cutoff_ts: float) -> tuple[int, int]:
    uploads = _uploads_dir(wsid)
    if uploads is None or not uploads.is_dir():
        return (0, 0)
    files = 0
    bytes_ = 0
    for entry in uploads.iterdir():
        if not entry.is_file():
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        if stat.st_mtime < cutoff_ts:
            files += 1
            bytes_ += stat.st_size
    return (files, bytes_)


def _trim_uploads(wsid: str, cutoff_ts: float) -> dict[str, Any]:
    uploads = _uploads_dir(wsid)
    if uploads is None or not uploads.is_dir():
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}
    deleted_count = 0
    freed_bytes = 0
    deleted_names: list[str] = []
    for entry in uploads.iterdir():
        if not entry.is_file():
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        if stat.st_mtime >= cutoff_ts:
            continue
        size = stat.st_size
        try:
            entry.unlink()
        except OSError as exc:
            # Don't log the entry path — user filenames can be
            # sensitive (tax docs, ID scans, etc.). wsid + size
            # is enough for support to triage.
            logger.warning(
                "chat_storage: failed to remove an upload "
                "(%d bytes) in ws=%s: %s",
                size,
                wsid,
                exc,
            )
            continue
        deleted_count += 1
        freed_bytes += size
        deleted_names.append(entry.name)
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_names,
    }


# ── Legacy single-bucket stats (kept for backwards compat) ─────────
# The earlier ``stats_for_user`` / ``cleanup_for_user`` API is still
# imported by routes/sessions.py; we keep it as thin wrappers that
# expose the new cycle-status data. Removing them outright would
# require a coordinated route+frontend rename, which we do as a
# separate change.
DEFAULT_KEEP = 100  # legacy chat-keep cap (unused by the cycle path)


def stats_for_user(user_id: str, *, keep: int = DEFAULT_KEEP) -> dict[str, Any]:
    """Legacy wrapper: collapse the cycle's chat bucket into the old
    ``{keep, total_chats, eligible_chats, eligible_bytes, scope}``
    shape. New code should call ``cycle_status_for_user`` instead.
    """
    keep = max(1, int(keep))
    sessions = _user_sessions(user_id)
    total = len(sessions)
    if total <= keep:
        return {
            "category": "chats",
            "keep": keep,
            "total_chats": total,
            "eligible_chats": 0,
            "eligible_bytes": 0,
            "scope": "global",
        }

    eligible = sessions[keep:]
    bytes_total = sum(chat_dir_size(s["id"]) for s in eligible)
    return {
        "category": "chats",
        "keep": keep,
        "total_chats": total,
        "eligible_chats": len(eligible),
        "eligible_bytes": bytes_total,
        "scope": "global",
        "oldest_kept_at": sessions[keep - 1].get("last_used"),
    }


def cleanup_for_user(user_id: str, *, keep: int = DEFAULT_KEEP) -> dict[str, Any]:
    """Legacy wrapper: keep-newest-N chat cleanup. Used by the
    pre-cycle web SPA. New SPAs should POST to /api/storage/cycle/run."""
    keep = max(1, int(keep))
    sessions = _user_sessions(user_id)
    if len(sessions) <= keep:
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}

    eligible = sessions[keep:]
    reg = Registry.instance()
    freed_bytes = 0
    deleted_ids: list[str] = []
    for sess in eligible:
        sid = sess.get("id")
        if not isinstance(sid, str):
            continue
        size = chat_dir_size(sid)
        try:
            reg.delete_session(sid)
        except KeyError:
            continue
        except Exception as exc:
            logger.warning("chat_storage: failed to delete %s: %s", sid, exc)
            continue
        freed_bytes += size
        deleted_ids.append(sid)
    return {
        "deleted_count": len(deleted_ids),
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_ids,
    }


def chats_root() -> Path:
    return DATA_ROOT / "chats"


def default_keep() -> int:
    raw = (os.environ.get("PI_CHAT_KEEP", "") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_KEEP
