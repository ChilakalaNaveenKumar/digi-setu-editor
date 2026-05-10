"""
Per-workspace storage statistics + cleanup helpers.

What this module owns
---------------------
Every kind of artifact we persist *per workspace* gets a stats fn
and a cleanup fn here. The frontend's Storage panel walks the
unified ``workspace_storage_summary`` to render one row per
category with size + a Clean button.

Categories (desktop)
--------------------
1. **chats** — per-session JSONL transcripts under
   ``<DATA_ROOT>/chats/<sid>/``. Keep newest 100 chats per
   workspace by ``last_used`` DESC. Implementation:
   ``stats_for_workspace`` / ``cleanup_workspace``.

2. **audits** — append-only JSONL at
   ``<DATA_ROOT>/audits/<wsid>.jsonl`` recording every AI tool
   call (allow / deny / failed / blocked). Keep the newest 90
   days by line ``ts`` field. Trimming = rewrite the file with
   only the recent rows. Implementation: ``audits_stats`` /
   ``cleanup_audits``.

3. **uploads** — files the user attached to chats, parked at
   ``<workspace_path>/uploads/`` (desktop: inside the picked
   folder). Keep newest 30 days by file mtime. Implementation:
   ``uploads_stats`` / ``cleanup_uploads``.

4. **shadows** — shadow git repo at
   ``<DATA_ROOT>/shadows/<workspace-key>/`` powering the
   "revert AI edit" / undo system. **DESTRUCTIVE** to remove —
   wipes every snapshot the AI ever took of this workspace, no
   way to undo past edits afterwards. Surface only behind a
   prominent confirm dialog. Implementation: ``shadows_stats`` /
   ``purge_shadows``.

Design choices
--------------
* Manual only — the UI shows current size; deletion runs on
  explicit POST. Auto-cleanup of user data is the kind of feature
  that earns one-star reviews when it surprises someone.
* Disk size is measured BEFORE the cleanup runs (post-deletion
  the directory is gone, so we have to size it first to report
  "freed N bytes" correctly).
* Each cleanup function returns the same shape:
  ``{"deleted_count": int, "freed_bytes": int, "deleted_ids": [...]}``
  — even when "ids" don't apply (audits return synthetic line
  numbers, shadows return ``[]``). Keeps the route handler simple.

What we deliberately DON'T cleanup
----------------------------------
* ``.env`` — user-edited BYOK config.
* ``.session_id`` — Clerk session cache; deleting forces re-login.
* ``registry.json`` — workspace + session catalog (mutated by the
  cleanups above as a side effect).
* ``users/<uid>/`` — per-user prefs, < 1 KB.
* ``pi-runtime/`` — managed by ``services/pi_integrity``;
  appears in the UI under a separate "App runtime" row that's
  read-only.
* Terminal output — purely in-memory pty stream, never
  persisted (see ``services/pty_terminal.py``).

Web flavour
-----------
``web/backend/services/chat_storage.py`` mirrors this contract
but collapses to an account-wide budget because web sessions have
no real folder.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import DATA_ROOT
from services.registry import Registry

logger = logging.getLogger(__name__)


# ── Keep-policy defaults ───────────────────────────────────────────
# Each category has its own default. Operators can override via env
# (``PI_CHAT_KEEP``, ``PI_AUDIT_KEEP_DAYS``, ``PI_UPLOAD_KEEP_DAYS``)
# for tests / CI / power users. The UI doesn't expose tuning yet —
# Cursor / Claude Code / VSCode all hide retention dials too because
# 99 % of users never touch them and 1 % know enough to edit env.
DEFAULT_KEEP = 100
DEFAULT_AUDIT_KEEP_DAYS = 90
DEFAULT_UPLOAD_KEEP_DAYS = 30


# ── Public types ───────────────────────────────────────────────────
def _empty_stats(keep: int) -> dict[str, Any]:
    return {
        "category": "chats",
        "keep": keep,
        "total_chats": 0,
        "eligible_chats": 0,
        "eligible_bytes": 0,
        "scope": "workspace",
    }


# ── Disk size ──────────────────────────────────────────────────────
def chat_dir_size(sid: str) -> int:
    """Total bytes used by ``<DATA_ROOT>/chats/<sid>/`` (recursive).

    Returns 0 when the directory doesn't exist (e.g. the session was
    created but the user never sent a prompt — pi never wrote any
    JSONL). Tolerates per-file ``OSError`` so a single permission
    glitch can't blow up the whole stat call.
    """
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
                    # Symlink to nowhere, file just deleted under us, …
                    continue
    except OSError:
        return 0
    return total


# ── Stats ──────────────────────────────────────────────────────────
def stats_for_workspace(workspace_id: str, *, keep: int = DEFAULT_KEEP) -> dict[str, Any]:
    """How much disk would freeing-everything-beyond-the-newest-N reclaim?

    Sessions are ranked by ``last_used`` DESC (same order the chat
    picker shows). The first ``keep`` are protected; the rest are
    eligible for cleanup.

    Returns:
        keep:           the policy threshold (100 unless overridden)
        total_chats:    every session in this workspace
        eligible_chats: how many would be deleted (= total - keep, or 0)
        eligible_bytes: cumulative size on disk of those eligible chats
        scope:          "workspace"
        oldest_kept_at: ISO-8601 last_used of the oldest chat we'd keep
                        (so the UI can say "older than 12 Mar 2024 →")
    """
    keep = max(1, int(keep))
    sessions = Registry.instance().list_sessions(workspace_id=workspace_id)
    total = len(sessions)
    if total <= keep:
        out = _empty_stats(keep)
        out["total_chats"] = total
        return out

    eligible = sessions[keep:]
    bytes_total = sum(chat_dir_size(s["id"]) for s in eligible)
    oldest_kept = sessions[keep - 1]
    return {
        "category": "chats",
        "keep": keep,
        "total_chats": total,
        "eligible_chats": len(eligible),
        "eligible_bytes": bytes_total,
        "scope": "workspace",
        "oldest_kept_at": oldest_kept.get("last_used"),
    }


# ── Cleanup ────────────────────────────────────────────────────────
def cleanup_workspace(
    workspace_id: str,
    *,
    keep: int = DEFAULT_KEEP,
) -> dict[str, Any]:
    """Delete every chat beyond the newest ``keep`` in this workspace.

    Ownership: the route-level ``workspace_for_user_or_404`` ALWAYS
    runs before this helper is called, so by the time we get here
    the workspace is verified to belong to the caller. Sessions in
    desktop registry don't carry their own ``owner_user_id``
    (ownership is transitive through workspace), so there's nothing
    further to filter on.

    Returns:
        deleted_count:  how many sessions were actually removed
        freed_bytes:    sum of chat-dir sizes BEFORE deletion (post-
                        deletion the dirs are gone, so we have to
                        measure first)
        deleted_ids:    the session ids we removed (for client logging)
    """
    keep = max(1, int(keep))
    sessions = Registry.instance().list_sessions(workspace_id=workspace_id)
    if len(sessions) <= keep:
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}

    return _delete_sessions(sessions[keep:])


def _delete_sessions(eligible: list[dict[str, Any]]) -> dict[str, Any]:
    reg = Registry.instance()
    freed_bytes = 0
    deleted_ids: list[str] = []
    for sess in eligible:
        sid = sess.get("id")
        if not isinstance(sid, str):
            continue
        # Measure BEFORE deletion — registry.delete_session rmtree's
        # the chat dir as part of its work, so we can't size it after.
        size = chat_dir_size(sid)
        try:
            reg.delete_session(sid)
        except KeyError:
            # Already gone (parallel delete from another tab); ignore.
            continue
        except Exception as exc:
            logger.warning(
                "chat_storage: failed to delete session %s: %s "
                "(continuing with remaining cleanup)",
                sid,
                exc,
            )
            continue
        freed_bytes += size
        deleted_ids.append(sid)

    if deleted_ids:
        logger.info(
            "chat_storage: cleaned up %d chats freeing %s bytes",
            len(deleted_ids),
            freed_bytes,
        )
    return {
        "deleted_count": len(deleted_ids),
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_ids,
    }


# ── Audits (per-workspace JSONL, age-based trim) ───────────────────
# The audit log at <DATA_ROOT>/audits/<wsid>.jsonl is append-only and
# grows ~1 line per AI tool call. At ~100 calls/day a moderately
# active user accumulates ~10 MB/year — small but not free, and the
# rows older than ~90 days have no active value (the user can't
# meaningfully review three-month-old tool prompts).
#
# Trim by reading all rows, dropping ones older than the cutoff, and
# rewriting atomically. We do NOT use truncate() — that'd race against
# the audit writer (services.audit.record) on concurrent writes.
def _audit_path(wsid: str) -> Path:
    return DATA_ROOT / "audits" / f"{wsid}.jsonl"


def audits_stats(wsid: str, *, days_to_keep: int = DEFAULT_AUDIT_KEEP_DAYS) -> dict[str, Any]:
    """How many audit rows + bytes would a 90-day trim free?

    We walk the file once, classifying each row by ``ts``. Row with a
    parseable ts older than the cutoff counts toward eligible. Rows
    we can't parse are KEPT (defensive — corruption shouldn't trigger
    silent deletion).
    """
    days_to_keep = max(1, int(days_to_keep))
    path = _audit_path(wsid)
    if not path.exists() or not path.is_file():
        return {
            "category": "audits",
            "days_to_keep": days_to_keep,
            "total_rows": 0,
            "eligible_rows": 0,
            "eligible_bytes": 0,
            "total_bytes": 0,
        }

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    eligible_rows = 0
    eligible_bytes = 0
    total_rows = 0
    total_bytes = 0
    try:
        with path.open("rb") as fh:
            for raw in fh:
                total_rows += 1
                total_bytes += len(raw)
                ts = _parse_audit_ts(raw)
                if ts is not None and ts < cutoff:
                    eligible_rows += 1
                    eligible_bytes += len(raw)
    except OSError as exc:
        logger.warning("chat_storage: audits_stats(%s): %s", wsid, exc)
        return {
            "category": "audits",
            "days_to_keep": days_to_keep,
            "total_rows": 0,
            "eligible_rows": 0,
            "eligible_bytes": 0,
            "total_bytes": 0,
        }

    return {
        "category": "audits",
        "days_to_keep": days_to_keep,
        "total_rows": total_rows,
        "eligible_rows": eligible_rows,
        "eligible_bytes": eligible_bytes,
        "total_bytes": total_bytes,
    }


def cleanup_audits(wsid: str, *, days_to_keep: int = DEFAULT_AUDIT_KEEP_DAYS) -> dict[str, Any]:
    """Drop audit rows older than the cutoff. Atomic rewrite via temp
    file → rename so a concurrent ``services.audit.record`` write
    never sees a half-trimmed file."""
    days_to_keep = max(1, int(days_to_keep))
    path = _audit_path(wsid)
    if not path.exists() or not path.is_file():
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
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
        # ``Path.replace`` is atomic on POSIX + Windows for same-fs
        # operations — both files live under ``audits/`` so we're fine.
        tmp_path.replace(path)
    except OSError as exc:
        logger.warning(
            "chat_storage: cleanup_audits(%s) failed during rewrite: %s",
            wsid,
            exc,
        )
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}

    if deleted_count:
        logger.info(
            "chat_storage: trimmed %d audit rows (%d bytes) for ws=%s",
            deleted_count,
            freed_bytes,
            wsid,
        )
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": [],
    }


def _parse_audit_ts(raw: bytes) -> datetime | None:
    """Extract the ``ts`` field from one audit row.

    Audit rows are tiny (< 1 KB typical) so JSON-decoding the whole
    line is cheap; we don't try to be clever with byte-level parsing.
    Returns None when the row is unparseable, missing ``ts``, or has
    a malformed timestamp — caller treats None as "keep this row".
    """
    try:
        row = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(row, dict):
        return None
    ts = row.get("ts")
    if not isinstance(ts, str):
        return None
    # services.audit writes "%Y-%m-%dT%H:%M:%SZ" (no microseconds, no
    # offset suffix beyond Z). Older rows may carry "+00:00".
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Uploads (per-workspace folder, age-based trim) ─────────────────
# Files under ``<workspace_path>/uploads/`` are user-attached files
# the AI got to see. Most are screenshots / one-off PDFs the user
# sent and never reopened — but some users park PDF references they
# want to keep around. We only trim by mtime, never by content type
# or filename pattern.
#
# IMPORTANT: this folder lives INSIDE the user's picked workspace
# folder (e.g. ``~/MyProject/uploads/``), not in DATA_ROOT. Even
# though the AI placed those files there originally, the user can
# move things in / out — so we ONLY look at files actually inside
# ``uploads/`` and ONLY by mtime.
def uploads_stats(wsid: str, *, days_to_keep: int = DEFAULT_UPLOAD_KEEP_DAYS) -> dict[str, Any]:
    days_to_keep = max(1, int(days_to_keep))
    uploads_dir = _resolve_uploads_dir(wsid)
    if uploads_dir is None or not uploads_dir.is_dir():
        return {
            "category": "uploads",
            "days_to_keep": days_to_keep,
            "total_files": 0,
            "eligible_files": 0,
            "eligible_bytes": 0,
            "total_bytes": 0,
        }

    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).timestamp()
    eligible_files = 0
    eligible_bytes = 0
    total_files = 0
    total_bytes = 0
    for entry in uploads_dir.iterdir():
        # Top-level only — uploads/ is intentionally flat. If the user
        # made subdirs in here we don't recurse (might be intentional
        # organization).
        if not entry.is_file():
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        total_files += 1
        total_bytes += stat.st_size
        if stat.st_mtime < cutoff_ts:
            eligible_files += 1
            eligible_bytes += stat.st_size

    return {
        "category": "uploads",
        "days_to_keep": days_to_keep,
        "total_files": total_files,
        "eligible_files": eligible_files,
        "eligible_bytes": eligible_bytes,
        "total_bytes": total_bytes,
    }


def cleanup_uploads(wsid: str, *, days_to_keep: int = DEFAULT_UPLOAD_KEEP_DAYS) -> dict[str, Any]:
    days_to_keep = max(1, int(days_to_keep))
    uploads_dir = _resolve_uploads_dir(wsid)
    if uploads_dir is None or not uploads_dir.is_dir():
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}

    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).timestamp()
    deleted_count = 0
    freed_bytes = 0
    deleted_names: list[str] = []
    for entry in uploads_dir.iterdir():
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
            # Log size + ws only — user filenames stay out of logs
            # (they can be sensitive: "tax_return_2024.pdf",
            # "passport_scan.jpg", …).
            logger.warning(
                "chat_storage: failed to delete an upload (%d bytes) "
                "in ws=%s: %s",
                size,
                wsid,
                exc,
            )
            continue
        deleted_count += 1
        freed_bytes += size
        deleted_names.append(entry.name)

    if deleted_count:
        logger.info(
            "chat_storage: removed %d uploads (%d bytes) for ws=%s",
            deleted_count,
            freed_bytes,
            wsid,
        )
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_names,
    }


def _resolve_uploads_dir(wsid: str) -> Path | None:
    """Return ``<workspace_path>/uploads/`` if the workspace exists,
    else None. We DON'T call ``Registry.ensure_uploads_dir`` because
    that would create the folder as a side effect — stat fns must
    not have side effects.
    """
    rec = Registry.instance().get_workspace(wsid)
    if not rec:
        return None
    base = Path(rec.get("path", "")).expanduser()
    if not base.exists():
        return None
    if rec.get("mode") == "desktop":
        return base / "uploads"
    return base / "workspace" / "uploads"


# ── Shadows (per-workspace, DESTRUCTIVE purge) ─────────────────────
# Shadow git lives at ``<DATA_ROOT>/shadows/<key>/`` and stores every
# AI edit as a git commit. Purging this kills the user's ability to
# revert past AI changes. The UI must surface a prominent confirm
# before calling this — language like "PERMANENT — you won't be able
# to revert AI edits made before this cleanup."
def shadows_stats(wsid: str) -> dict[str, Any]:
    path = _resolve_shadow_dir(wsid)
    if path is None or not path.exists():
        return {
            "category": "shadows",
            "destructive": True,
            "total_bytes": 0,
            "eligible_bytes": 0,
        }
    size = _dir_size(path)
    return {
        "category": "shadows",
        "destructive": True,
        "total_bytes": size,
        "eligible_bytes": size,
    }


def purge_shadows(wsid: str) -> dict[str, Any]:
    path = _resolve_shadow_dir(wsid)
    if path is None or not path.exists():
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}
    size = _dir_size(path)
    try:
        shutil.rmtree(path)
    except OSError as exc:
        logger.warning(
            "chat_storage: purge_shadows(%s) failed: %s", wsid, exc
        )
        return {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}
    logger.info(
        "chat_storage: purged shadow git (%d bytes) for ws=%s — "
        "AI edits made before this point are no longer revertable",
        size,
        wsid,
    )
    return {"deleted_count": 1, "freed_bytes": size, "deleted_ids": []}


def _resolve_shadow_dir(wsid: str) -> Path | None:
    """Compute the on-disk shadow folder for this workspace.

    Shadow keys are derived from the canonical workspace PATH (not
    the wsid) — see ``services.shadow_git._shadow_key_for``. We
    delegate to that helper so the two views can never drift.
    """
    rec = Registry.instance().get_workspace(wsid)
    if not rec:
        return None
    workspace_path = Path(rec.get("path", "")).expanduser()
    try:
        from services.shadow_git import _shadow_root_for  # type: ignore[attr-defined]
    except ImportError:
        return None
    try:
        return _shadow_root_for(workspace_path)
    except Exception:
        return None


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
    except OSError:
        return 0
    return total


# ── Unified summary ────────────────────────────────────────────────
# Single endpoint payload the frontend Storage panel renders. The
# shape is deliberately uniform across categories so the panel can
# loop over a list and render one row per ``{category, total_*,
# eligible_*}`` triple.
def workspace_storage_summary(wsid: str) -> dict[str, Any]:
    return {
        "workspace_id": wsid,
        "categories": [
            stats_for_workspace(wsid, keep=default_keep()),
            audits_stats(wsid, days_to_keep=default_audit_keep_days()),
            uploads_stats(wsid, days_to_keep=default_upload_keep_days()),
            shadows_stats(wsid),
        ],
    }


def cleanup_categories(
    wsid: str, *, categories: list[str]
) -> dict[str, Any]:
    """Run each requested category cleanup and return a per-category
    result map. Unknown category names are ignored (forward-compat
    so a future SPA targeting the same backend doesn't 400 if it
    asks for something we don't know about yet)."""
    results: dict[str, dict[str, Any]] = {}
    for cat in categories:
        cat_norm = (cat or "").strip().lower()
        if cat_norm == "chats":
            results["chats"] = cleanup_workspace(wsid, keep=default_keep())
        elif cat_norm == "audits":
            results["audits"] = cleanup_audits(
                wsid, days_to_keep=default_audit_keep_days()
            )
        elif cat_norm == "uploads":
            results["uploads"] = cleanup_uploads(
                wsid, days_to_keep=default_upload_keep_days()
            )
        elif cat_norm == "shadows":
            results["shadows"] = purge_shadows(wsid)
        else:
            logger.info("chat_storage: ignoring unknown category %r", cat)
    return {"results": results}


# ── Misc ───────────────────────────────────────────────────────────
def chats_root() -> Path:
    """Where every per-session chat dir lives. Exposed for tests."""
    return DATA_ROOT / "chats"


def default_keep() -> int:
    raw = (os.environ.get("PI_CHAT_KEEP", "") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_KEEP


def default_audit_keep_days() -> int:
    raw = (os.environ.get("PI_AUDIT_KEEP_DAYS", "") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_AUDIT_KEEP_DAYS


def default_upload_keep_days() -> int:
    raw = (os.environ.get("PI_UPLOAD_KEEP_DAYS", "") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_UPLOAD_KEEP_DAYS
