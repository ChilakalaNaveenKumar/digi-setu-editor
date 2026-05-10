"""
Tests for ``services.chat_storage`` — the rolling-90-day auto-cleanup
cycle on web.

The cycle runs in three phases:
  1. cycle_status_for_user(uid) — banner data
  2. run_cycle_for_user(uid, force=False) — only sweeps when due
  3. run_cycle_for_user(uid, force=True)  — manual "Clean now"

We isolate per test by pointing PI_DATA_ROOT at tmp_path and
reloading config + registry + chat_storage so the singleton picks
up the new path. ``stamp_sandbox_dir`` is a no-op when SANDBOX_UID
== 0 (which is the test default when PI_SANDBOX_UID is unset).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


# ── Fixtures ───────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate_data_root(tmp_path, monkeypatch):
    monkeypatch.setenv("PI_DATA_ROOT", str(tmp_path))
    monkeypatch.delenv("PI_SANDBOX_UID", raising=False)
    monkeypatch.delenv("PI_STORAGE_CYCLE_DAYS", raising=False)
    monkeypatch.delenv("PI_STORAGE_BANNER_LEAD_DAYS", raising=False)

    import importlib

    import config as _config
    importlib.reload(_config)
    import services.sandbox_layout as _layout
    importlib.reload(_layout)
    import services.registry as _registry
    importlib.reload(_registry)
    import services.chat_storage as _chat_storage
    importlib.reload(_chat_storage)

    _registry.Registry._instance = None  # type: ignore[attr-defined]
    yield
    _registry.Registry._instance = None  # type: ignore[attr-defined]


def _seed_workspace(*, owner: str = "u_a") -> str:
    from services.registry import Registry
    rec = Registry.instance().create_web_workspace(
        name="ws", owner_user_id=owner
    )
    return rec["id"]


def _seed_session(
    wsid: str,
    *,
    last_used: str | None = None,
    chat_bytes: int = 0,
) -> str:
    from services.registry import Registry
    rec = Registry.instance().create_session(wsid, title="")
    sid = rec["id"]

    if last_used is not None:
        Registry.instance()._data["sessions"][sid]["last_used"] = last_used  # type: ignore[attr-defined]
        Registry.instance()._flush()  # type: ignore[attr-defined]

    if chat_bytes > 0:
        chat_dir = Registry.instance().session_chat_dir(sid)
        (chat_dir / "synthetic.jsonl").write_bytes(b"x" * chat_bytes)

    return sid


def _audit_row(ts_iso: str) -> bytes:
    return (
        json.dumps({
            "ts": ts_iso,
            "sid": "s_test",
            "uid": "u_a",
            "tool": "bash",
            "event": "completed",
        }).encode("utf-8")
        + b"\n"
    )


def _seed_audit_file(wsid: str, rows: list[bytes]) -> Path:
    from config import DATA_ROOT
    audits_dir = DATA_ROOT / "audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    path = audits_dir / f"{wsid}.jsonl"
    path.write_bytes(b"".join(rows))
    return path


def _seed_upload(wsid: str, name: str, *, age_days: int, size: int = 100) -> Path:
    from services.registry import Registry
    rec = Registry.instance().get_workspace(wsid)
    assert rec is not None
    base = Path(rec["path"]) / "workspace" / "uploads"
    base.mkdir(parents=True, exist_ok=True)
    f = base / name
    f.write_bytes(b"x" * size)
    if age_days > 0:
        backdated = time.time() - (age_days * 86400)
        os.utime(f, (backdated, backdated))
    return f


# ── Cycle status (banner data) ─────────────────────────────────────
def test_cycle_status_fresh_account_no_banner():
    """A brand-new user (no last_cycle_at) gets a full 90-day window
    before their first sweep — no banner on day 1."""
    from services.chat_storage import cycle_status_for_user
    out = cycle_status_for_user("u_new")
    assert out["cycle_days"] == 90
    assert out["banner_lead_days"] == 5
    # Fresh account: next cycle is ~90 days away; banner lead is 5d
    # so days_until_cycle (≈90) ≫ banner_lead → no banner.
    assert out["days_until_cycle"] > out["banner_lead_days"]
    assert out["show_banner"] is False
    assert out["last_cycle_at"] is None
    assert out["pending"]["total_count"] == 0
    assert out["pending"]["total_bytes"] == 0


def test_cycle_status_pending_window_triggers_banner(monkeypatch):
    """User whose last_cycle_at is 86 days ago → 4 days from due
    → banner shows (4 ≤ banner_lead = 5)."""
    from services.chat_storage import _write_cycle_state, cycle_status_for_user
    last = datetime.now(timezone.utc) - timedelta(days=86)
    _write_cycle_state("u_a", {"last_cycle_at": last.isoformat()})

    out = cycle_status_for_user("u_a")
    assert out["show_banner"] is True
    assert out["days_until_cycle"] <= out["banner_lead_days"]


def test_cycle_status_past_due_still_renders():
    """If the scheduler missed a tick and the cycle is overdue, the
    banner is still shown (days_until_cycle = 0) and we don't crash."""
    from services.chat_storage import _write_cycle_state, cycle_status_for_user
    last = datetime.now(timezone.utc) - timedelta(days=200)  # 110d overdue
    _write_cycle_state("u_overdue", {"last_cycle_at": last.isoformat()})

    out = cycle_status_for_user("u_overdue")
    assert out["show_banner"] is True
    assert out["days_until_cycle"] == 0


def test_cycle_status_pending_counts_old_artifacts():
    """The banner copy needs accurate pending counts BEFORE the
    sweep runs — the user reads "we'll free 12 MB across 4 chats,
    7 audit rows, 2 uploads" and decides whether to act."""
    wsid = _seed_workspace()
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()

    # 2 old chats + 1 fresh
    _seed_session(wsid, last_used=old, chat_bytes=400)
    _seed_session(wsid, last_used=old, chat_bytes=200)
    _seed_session(wsid, last_used=fresh, chat_bytes=100)

    # 3 old audit rows + 1 fresh
    _seed_audit_file(wsid, [
        _audit_row("2024-01-01T00:00:00Z"),
        _audit_row("2024-01-02T00:00:00Z"),
        _audit_row("2024-01-03T00:00:00Z"),
        _audit_row("2099-06-01T00:00:00Z"),
    ])

    # 1 old upload + 1 fresh
    _seed_upload(wsid, "stale.png", age_days=120, size=500)
    _seed_upload(wsid, "today.png", age_days=0, size=200)

    from services.chat_storage import cycle_status_for_user
    out = cycle_status_for_user("u_a")
    pending = out["pending"]
    assert pending["chats"]["count"] == 2
    assert pending["chats"]["bytes"] == 600
    assert pending["audits"]["count"] == 3
    assert pending["uploads"]["count"] == 1
    assert pending["uploads"]["bytes"] == 500
    assert pending["total_count"] == 6
    assert pending["total_bytes"] >= 1100


# ── Cycle execute: not due ─────────────────────────────────────────
def test_run_cycle_skips_when_not_due():
    """Default behavior: if the cycle isn't due, return ran=False
    and don't touch any data. Protects the public POST endpoint
    from being abused as a delete-everything button."""
    wsid = _seed_workspace()
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    sid = _seed_session(wsid, last_used=old, chat_bytes=400)

    from services.chat_storage import run_cycle_for_user
    out = run_cycle_for_user("u_a", force=False)
    assert out["ran"] is False
    assert out["reason"] == "not_due"
    assert out["results"] == {}

    # Old chat is still on disk.
    from services.registry import Registry
    assert Registry.instance().get_session(sid) is not None


# ── Cycle execute: force run ───────────────────────────────────────
def test_run_cycle_force_sweeps_old_artifacts():
    wsid = _seed_workspace()
    old_iso = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    fresh_iso = datetime.now(timezone.utc).isoformat()

    old_sid = _seed_session(wsid, last_used=old_iso, chat_bytes=400)
    fresh_sid = _seed_session(wsid, last_used=fresh_iso, chat_bytes=200)
    _seed_audit_file(wsid, [
        _audit_row("2024-01-01T00:00:00Z"),
        _audit_row("2099-06-01T00:00:00Z"),
    ])
    _seed_upload(wsid, "stale.png", age_days=120, size=500)
    _seed_upload(wsid, "today.png", age_days=0, size=200)

    from services.chat_storage import run_cycle_for_user
    out = run_cycle_for_user("u_a", force=True)
    assert out["ran"] is True
    assert out["ran_at"]
    assert out["next_cycle_at"]

    # Chats: only old one deleted.
    assert out["results"]["chats"]["deleted_count"] == 1
    assert old_sid in out["results"]["chats"]["deleted_ids"]

    # Audits: 1 old row trimmed.
    assert out["results"]["audits"]["deleted_count"] == 1

    # Uploads: 1 file removed.
    assert out["results"]["uploads"]["deleted_count"] == 1
    assert "stale.png" in out["results"]["uploads"]["deleted_ids"]

    # Fresh session survives.
    from services.registry import Registry
    assert Registry.instance().get_session(fresh_sid) is not None
    assert Registry.instance().get_session(old_sid) is None


def test_run_cycle_force_persists_last_cycle_at():
    wsid = _seed_workspace()
    _seed_session(wsid, chat_bytes=100)

    from services.chat_storage import (
        cycle_status_for_user,
        run_cycle_for_user,
    )
    before = cycle_status_for_user("u_a")
    assert before["last_cycle_at"] is None

    run_cycle_for_user("u_a", force=True)
    after = cycle_status_for_user("u_a")
    assert after["last_cycle_at"] is not None
    # Now that the cycle just ran, the banner should be far away again.
    assert after["show_banner"] is False
    assert after["days_until_cycle"] > 0


def test_run_cycle_isolates_users():
    """User A's cycle run must NOT touch User B's data."""
    ws_a = _seed_workspace(owner="u_a")
    ws_b = _seed_workspace(owner="u_b")
    old_iso = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    sid_a = _seed_session(ws_a, last_used=old_iso, chat_bytes=400)
    sid_b = _seed_session(ws_b, last_used=old_iso, chat_bytes=400)

    from services.chat_storage import run_cycle_for_user
    out = run_cycle_for_user("u_a", force=True)
    assert out["results"]["chats"]["deleted_count"] == 1
    assert sid_a in out["results"]["chats"]["deleted_ids"]
    assert sid_b not in out["results"]["chats"]["deleted_ids"]

    from services.registry import Registry
    assert Registry.instance().get_session(sid_a) is None
    assert Registry.instance().get_session(sid_b) is not None


def test_run_cycle_scheduled_runs_when_due():
    """Once enough time has passed (we backdate last_cycle_at), the
    non-forced call should actually run."""
    wsid = _seed_workspace()
    old_iso = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    _seed_session(wsid, last_used=old_iso, chat_bytes=400)

    # Backdate last_cycle_at by 100 days (cycle = 90 → due 10 days ago).
    from services.chat_storage import _write_cycle_state, run_cycle_for_user
    backdated = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    _write_cycle_state("u_a", {"last_cycle_at": backdated})

    out = run_cycle_for_user("u_a", force=False)
    assert out["ran"] is True
    assert out["results"]["chats"]["deleted_count"] == 1


def test_cycle_days_env_override(monkeypatch):
    """Operator can shorten the cycle for testing/debugging."""
    monkeypatch.setenv("PI_STORAGE_CYCLE_DAYS", "7")

    import importlib
    import services.chat_storage as _chat_storage
    importlib.reload(_chat_storage)

    assert _chat_storage.cycle_days() == 7


def test_banner_lead_days_env_override(monkeypatch):
    monkeypatch.setenv("PI_STORAGE_BANNER_LEAD_DAYS", "10")

    import importlib
    import services.chat_storage as _chat_storage
    importlib.reload(_chat_storage)

    assert _chat_storage.banner_lead_days() == 10


# ── Legacy keep-100 endpoints still work ───────────────────────────
def test_legacy_stats_for_user_still_works():
    """Older SPA bundles call ``stats_for_user`` (keep-newest-100);
    we must keep it working until those bundles roll out."""
    wsid = _seed_workspace()
    for i in range(3):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid, last_used=ts, chat_bytes=100)

    from services.chat_storage import stats_for_user
    out = stats_for_user("u_a", keep=2)
    assert out["category"] == "chats"
    assert out["total_chats"] == 3
    assert out["eligible_chats"] == 1
    assert out["scope"] == "global"


def test_legacy_cleanup_for_user_still_deletes_oldest():
    wsid = _seed_workspace()
    for i in range(3):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid, last_used=ts, chat_bytes=100)

    from services.chat_storage import cleanup_for_user
    out = cleanup_for_user("u_a", keep=2)
    assert out["deleted_count"] == 1
    assert out["freed_bytes"] == 100
