"""
Tests for ``services.chat_storage`` — the keep-last-100-chats-per-
workspace cleanup helper.

We build a fresh registry under tmp_path for each test (overriding
``DATA_ROOT`` via env) so the developer's real ~/.digi-setu doesn't
get touched. The Registry singleton is reset between tests via the
autouse fixture below.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# ── Fixtures ───────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate_data_root(tmp_path, monkeypatch):
    """Point every storage helper at a fresh tmp_path so tests can
    create / delete sessions without contaminating the developer's
    real ~/.digi-setu/.

    We also clear the Registry singleton between tests — it's a
    process-wide cache that'd otherwise return stale entries from
    a previous test's tmp_path.
    """
    monkeypatch.setenv("PI_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("PI_MODE", "desktop")
    # PI_CHAT_KEEP overrides the 100 default; we want explicit
    # control per test.
    monkeypatch.delenv("PI_CHAT_KEEP", raising=False)

    import importlib

    import config as _config
    importlib.reload(_config)
    import services.registry as _registry
    importlib.reload(_registry)
    import services.chat_storage as _chat_storage
    importlib.reload(_chat_storage)

    # Reset the singleton between tests.
    _registry.Registry._instance = None  # type: ignore[attr-defined]
    yield
    _registry.Registry._instance = None  # type: ignore[attr-defined]


def _seed_workspace(name: str, *, owner: str = "user_a") -> str:
    """Register a desktop workspace pointing at a real (empty) folder.

    Desktop's registry refuses to register a non-existent path
    (``register_desktop_workspace`` calls ``Path.is_dir()``), so the
    test creates the dir under tmp_path before registering.
    """
    from services.registry import Registry
    folder = Path(os.environ["PI_DATA_ROOT"]) / "ws-folders" / name
    folder.mkdir(parents=True, exist_ok=True)
    rec = Registry.instance().register_desktop_workspace(
        path=str(folder),
        name=name,
        owner_user_id=owner,
    )
    return rec["id"]


def _seed_session(
    wsid: str,
    *,
    title: str = "",
    last_used: str | None = None,
    chat_bytes: int = 0,
) -> str:
    """Create a session record + (optionally) a chat dir of given size.

    Desktop sessions don't carry ``owner_user_id`` directly —
    ownership is transitive through the parent workspace.
    """
    from services.registry import Registry
    rec = Registry.instance().create_session(wsid, title=title)
    sid = rec["id"]

    if last_used is not None:
        # Reach into the registry's internal store to backdate. Only
        # tests do this; production goes through ``touch_session``.
        Registry.instance()._data["sessions"][sid]["last_used"] = last_used  # type: ignore[attr-defined]
        Registry.instance()._flush()  # type: ignore[attr-defined]

    if chat_bytes > 0:
        chat_dir = Registry.instance().session_chat_dir(sid)
        # Write a single jsonl file of the requested size. Pi normally
        # writes structured JSONL but for size-accounting we just need
        # the bytes on disk.
        (chat_dir / "synthetic.jsonl").write_bytes(b"x" * chat_bytes)

    return sid


# ── Stats: empty workspace ─────────────────────────────────────────
def test_stats_empty_workspace_returns_zeroes():
    wsid = _seed_workspace("ws-empty")

    from services.chat_storage import stats_for_workspace

    out = stats_for_workspace(wsid, keep=100)
    assert out == {
        "category": "chats",
        "keep": 100,
        "total_chats": 0,
        "eligible_chats": 0,
        "eligible_bytes": 0,
        "scope": "workspace",
    }


# ── Stats: under threshold = nothing eligible ──────────────────────
def test_stats_under_keep_threshold_eligible_is_zero():
    wsid = _seed_workspace("ws-small")
    for i in range(50):
        _seed_session(wsid, chat_bytes=10)

    from services.chat_storage import stats_for_workspace

    out = stats_for_workspace(wsid, keep=100)
    assert out["total_chats"] == 50
    assert out["eligible_chats"] == 0
    assert out["eligible_bytes"] == 0


# ── Stats: over threshold = eligible bytes accurate ────────────────
def test_stats_over_threshold_reports_eligible_size():
    wsid = _seed_workspace("ws-big")

    # Build 5 sessions, KEEP=2.
    # Session A is the OLDEST (lowest last_used) → eligible.
    # The list is sorted by last_used DESC so newest go to keep
    # window; we backdate the older ones explicitly.
    sids = []
    for i in range(5):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        sids.append(_seed_session(wsid, last_used=ts, chat_bytes=1000))

    from services.chat_storage import stats_for_workspace

    out = stats_for_workspace(wsid, keep=2)
    assert out["total_chats"] == 5
    assert out["eligible_chats"] == 3  # the 3 oldest
    assert out["eligible_bytes"] == 3000


# ── Cleanup: deletes only beyond keep window ───────────────────────
def test_cleanup_keeps_newest_n_and_deletes_rest():
    wsid = _seed_workspace("ws-cleanup")
    for i in range(5):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid, last_used=ts, chat_bytes=2000)

    from services.chat_storage import cleanup_workspace
    from services.registry import Registry

    out = cleanup_workspace(wsid, keep=2)
    assert out["deleted_count"] == 3
    assert out["freed_bytes"] == 6000
    assert len(out["deleted_ids"]) == 3

    remaining = Registry.instance().list_sessions(workspace_id=wsid)
    assert len(remaining) == 2


# ── Cleanup: no-op when under threshold ────────────────────────────
def test_cleanup_under_threshold_is_noop():
    wsid = _seed_workspace("ws-small")
    for i in range(10):
        _seed_session(wsid, chat_bytes=100)

    from services.chat_storage import cleanup_workspace
    from services.registry import Registry

    out = cleanup_workspace(wsid, keep=100)
    assert out == {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}
    assert len(Registry.instance().list_sessions(workspace_id=wsid)) == 10


# ── Cleanup: deletes chat dir on disk too ──────────────────────────
def test_cleanup_removes_chat_dirs_on_disk(tmp_path):
    wsid = _seed_workspace("ws-disk")
    for i in range(3):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid, last_used=ts, chat_bytes=500)

    chats_root = tmp_path / "chats"
    assert len(list(chats_root.iterdir())) == 3

    from services.chat_storage import cleanup_workspace
    cleanup_workspace(wsid, keep=1)

    # Two chat dirs gone, one remains.
    assert len(list(chats_root.iterdir())) == 1


# ── Cross-workspace isolation ──────────────────────────────────────
def test_cleanup_does_not_touch_other_workspaces():
    """Cleanup is scoped per-workspace by design. Two workspaces
    with chats over their threshold each get their own keep-N
    treatment; one workspace's cleanup must NEVER reach into the
    other's session list."""
    wsid_a = _seed_workspace("ws-a")
    wsid_b = _seed_workspace("ws-b")
    for i in range(3):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid_a, last_used=ts, chat_bytes=100)
    for i in range(3):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid_b, last_used=ts, chat_bytes=100)

    from services.chat_storage import cleanup_workspace
    from services.registry import Registry

    cleanup_workspace(wsid_a, keep=1)

    # ws-b is untouched.
    assert len(Registry.instance().list_sessions(workspace_id=wsid_b)) == 3
    # ws-a kept the newest 1.
    assert len(Registry.instance().list_sessions(workspace_id=wsid_a)) == 1


# ── Default keep override via env var ──────────────────────────────
def test_default_keep_honours_env_override(monkeypatch):
    monkeypatch.setenv("PI_CHAT_KEEP", "7")
    import importlib
    import services.chat_storage as _cs
    importlib.reload(_cs)
    assert _cs.default_keep() == 7


def test_default_keep_falls_back_on_garbage_env(monkeypatch):
    monkeypatch.setenv("PI_CHAT_KEEP", "not-a-number")
    import importlib
    import services.chat_storage as _cs
    importlib.reload(_cs)
    assert _cs.default_keep() == 100


# ── chat_dir_size: handles missing dir cleanly ─────────────────────
def test_chat_dir_size_returns_zero_for_missing_dir():
    from services.chat_storage import chat_dir_size
    assert chat_dir_size("nonexistent_session_id") == 0


def test_chat_dir_size_recurses_subdirs(tmp_path):
    wsid = _seed_workspace("ws-nested")
    sid = _seed_session(wsid, chat_bytes=0)
    chat_dir = tmp_path / "chats" / sid
    (chat_dir / "subdir").mkdir(parents=True, exist_ok=True)
    (chat_dir / "a.jsonl").write_bytes(b"x" * 100)
    (chat_dir / "subdir" / "b.jsonl").write_bytes(b"y" * 200)

    from services.chat_storage import chat_dir_size
    assert chat_dir_size(sid) == 300


# ── Audits: age-based trim ─────────────────────────────────────────
def _audit_row(ts_iso: str, *, body: str = "x") -> bytes:
    """Synthesize one audit row in the shape ``services.audit.record``
    writes (ts + minimum required fields)."""
    return (
        json.dumps({
            "ts": ts_iso,
            "sid": "s_test",
            "uid": "u_test",
            "tool": "bash",
            "event": "completed",
            "body": body,
        }).encode("utf-8")
        + b"\n"
    )


def _seed_audit_file(wsid: str, rows: list[bytes]) -> Path:
    audits_dir = Path(os.environ["PI_DATA_ROOT"]) / "audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    path = audits_dir / f"{wsid}.jsonl"
    path.write_bytes(b"".join(rows))
    return path


def test_audits_stats_counts_old_rows():
    wsid = _seed_workspace("ws-audits")

    # 3 fresh rows, 2 old rows. cutoff = 90 days.
    rows = [
        _audit_row("2024-01-01T00:00:00Z"),  # very old → eligible
        _audit_row("2024-01-02T00:00:00Z"),  # very old → eligible
    ]
    fresh_iso = "2099-01-01T00:00:00Z"  # future-proof — always within window
    rows += [_audit_row(fresh_iso) for _ in range(3)]
    _seed_audit_file(wsid, rows)

    from services.chat_storage import audits_stats
    out = audits_stats(wsid, days_to_keep=90)
    assert out["category"] == "audits"
    assert out["total_rows"] == 5
    assert out["eligible_rows"] == 2
    assert out["eligible_bytes"] > 0
    assert out["total_bytes"] >= out["eligible_bytes"]


def test_audits_cleanup_drops_only_old_rows():
    wsid = _seed_workspace("ws-audits-clean")
    fresh = _audit_row("2099-06-01T00:00:00Z")
    rows = [
        _audit_row("2024-01-01T00:00:00Z"),
        fresh,
        _audit_row("2024-01-02T00:00:00Z"),
        fresh,
    ]
    path = _seed_audit_file(wsid, rows)

    from services.chat_storage import cleanup_audits
    out = cleanup_audits(wsid, days_to_keep=90)
    assert out["deleted_count"] == 2
    assert out["freed_bytes"] > 0

    # File survives, only fresh rows remain.
    surviving = path.read_bytes().splitlines()
    assert len(surviving) == 2
    for raw in surviving:
        assert b"2099-06-01" in raw


def test_audits_cleanup_preserves_unparseable_rows():
    """Defensive: corruption shouldn't trigger silent deletion."""
    wsid = _seed_workspace("ws-audits-corrupt")
    rows = [
        _audit_row("2024-01-01T00:00:00Z"),  # eligible
        b"this is not json\n",  # unparseable → preserve
        b"{}\n",  # parses but no ts → preserve
    ]
    path = _seed_audit_file(wsid, rows)

    from services.chat_storage import cleanup_audits
    cleanup_audits(wsid, days_to_keep=90)

    surviving = path.read_bytes()
    # Old parseable row gone; the two unparseable / ts-less rows survive.
    assert b"this is not json" in surviving
    assert b"{}" in surviving
    assert b"2024-01-01" not in surviving


def test_audits_stats_empty_when_file_missing():
    wsid = _seed_workspace("ws-audits-none")
    from services.chat_storage import audits_stats
    out = audits_stats(wsid)
    assert out["total_rows"] == 0
    assert out["eligible_rows"] == 0


# ── Uploads: age-based trim ────────────────────────────────────────
def _seed_upload(wsid: str, name: str, *, age_days: int, size: int = 100) -> Path:
    """Create an uploads/ file with backdated mtime."""
    from services.registry import Registry
    rec = Registry.instance().get_workspace(wsid)
    assert rec is not None
    base = Path(rec["path"])
    uploads = base / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    f = uploads / name
    f.write_bytes(b"x" * size)
    if age_days > 0:
        # os.utime with (atime, mtime) tuple of unix-ts seconds.
        import time
        backdated = time.time() - (age_days * 86400)
        os.utime(f, (backdated, backdated))
    return f


def test_uploads_stats_counts_old_files():
    wsid = _seed_workspace("ws-uploads")
    _seed_upload(wsid, "old1.png", age_days=60, size=500)
    _seed_upload(wsid, "old2.pdf", age_days=45, size=200)
    _seed_upload(wsid, "fresh.txt", age_days=0, size=100)

    from services.chat_storage import uploads_stats
    out = uploads_stats(wsid, days_to_keep=30)
    assert out["category"] == "uploads"
    assert out["total_files"] == 3
    assert out["eligible_files"] == 2
    assert out["eligible_bytes"] == 700


def test_uploads_cleanup_removes_old_files_only():
    wsid = _seed_workspace("ws-uploads-clean")
    old = _seed_upload(wsid, "stale.png", age_days=60, size=500)
    fresh = _seed_upload(wsid, "today.png", age_days=0, size=200)

    from services.chat_storage import cleanup_uploads
    out = cleanup_uploads(wsid, days_to_keep=30)
    assert out["deleted_count"] == 1
    assert out["freed_bytes"] == 500
    assert "stale.png" in out["deleted_ids"]
    assert not old.exists()
    assert fresh.exists()


def test_uploads_stats_no_uploads_dir_returns_zero():
    wsid = _seed_workspace("ws-no-uploads")
    from services.chat_storage import uploads_stats
    out = uploads_stats(wsid)
    # The fixture seeds the workspace folder but uploads/ doesn't
    # exist until something writes there.
    assert out["total_files"] == 0
    assert out["eligible_files"] == 0


# ── Shadows: destructive purge ─────────────────────────────────────
def test_shadows_stats_returns_size_when_present():
    wsid = _seed_workspace("ws-shadows")
    # Fake a shadow git dir at the canonical location.
    from services.chat_storage import _resolve_shadow_dir  # type: ignore[attr-defined]
    shadow = _resolve_shadow_dir(wsid)
    assert shadow is not None
    shadow.mkdir(parents=True, exist_ok=True)
    (shadow / "objects").mkdir()
    (shadow / "objects" / "x.pack").write_bytes(b"y" * 1000)

    from services.chat_storage import shadows_stats
    out = shadows_stats(wsid)
    assert out["category"] == "shadows"
    assert out["destructive"] is True
    assert out["total_bytes"] == 1000
    assert out["eligible_bytes"] == 1000


def test_shadows_purge_removes_dir_and_reports_size():
    wsid = _seed_workspace("ws-shadows-purge")
    from services.chat_storage import _resolve_shadow_dir  # type: ignore[attr-defined]
    shadow = _resolve_shadow_dir(wsid)
    assert shadow is not None
    shadow.mkdir(parents=True, exist_ok=True)
    (shadow / "data").write_bytes(b"x" * 500)

    from services.chat_storage import purge_shadows
    out = purge_shadows(wsid)
    assert out["deleted_count"] == 1
    assert out["freed_bytes"] >= 500
    assert not shadow.exists()


def test_shadows_purge_noop_when_dir_missing():
    wsid = _seed_workspace("ws-no-shadows")
    from services.chat_storage import purge_shadows
    out = purge_shadows(wsid)
    assert out == {"deleted_count": 0, "freed_bytes": 0, "deleted_ids": []}


# ── Unified summary ────────────────────────────────────────────────
def test_workspace_summary_returns_all_four_categories():
    wsid = _seed_workspace("ws-summary")

    from services.chat_storage import workspace_storage_summary
    out = workspace_storage_summary(wsid)
    assert out["workspace_id"] == wsid
    cats = [c["category"] for c in out["categories"]]
    assert cats == ["chats", "audits", "uploads", "shadows"]


def test_cleanup_categories_runs_only_requested_ones():
    """Multi-select: ``cleanup_categories`` should run exactly the
    categories the caller asks for, no more, no less."""
    wsid = _seed_workspace("ws-multi")

    # Seed all four categories with deletable content.
    for i in range(5):
        ts = f"2024-{i+1:02d}-01T00:00:00+00:00"
        _seed_session(wsid, last_used=ts, chat_bytes=100)
    _seed_audit_file(wsid, [_audit_row("2024-01-01T00:00:00Z")])
    _seed_upload(wsid, "old.png", age_days=60, size=200)

    from services.chat_storage import cleanup_categories

    out = cleanup_categories(wsid, categories=["chats", "audits"])
    # Both ran.
    assert "chats" in out["results"]
    assert "audits" in out["results"]
    # Uploads + shadows did NOT run (we didn't ask).
    assert "uploads" not in out["results"]
    assert "shadows" not in out["results"]


def test_cleanup_categories_ignores_unknown_names():
    wsid = _seed_workspace("ws-bogus")
    from services.chat_storage import cleanup_categories
    out = cleanup_categories(wsid, categories=["chats", "bogus", ""])
    # Only "chats" ran (workspace has no chats so it's a no-op, but
    # the key should be present). "bogus" + "" are dropped silently.
    assert "chats" in out["results"]
    assert "bogus" not in out["results"]
    assert "" not in out["results"]
