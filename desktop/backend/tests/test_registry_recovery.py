"""
Regression tests for ``services.registry``'s self-heal on corrupt
``registry.json``.

Why this exists: a malformed registry would otherwise crash the
sidecar on every boot, and the Tauri watchdog would respawn it into
the same crash — "Lost connection to chat backend" with no way out.
The quarantine path lets the sidecar boot cleanly into an empty
registry while preserving the bad file for manual recovery.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_data_root(tmp_path, monkeypatch):
    monkeypatch.setenv("PI_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("PI_MODE", "desktop")

    import importlib

    import config as _config
    importlib.reload(_config)
    import services.registry as _registry
    importlib.reload(_registry)

    _registry.Registry._instance = None  # type: ignore[attr-defined]
    yield
    _registry.Registry._instance = None  # type: ignore[attr-defined]


def _registry_path() -> Path:
    from config import DATA_ROOT
    return DATA_ROOT / "registry.json"


def _bak_files() -> list[Path]:
    return sorted(_registry_path().parent.glob("registry.json.corrupt-*.bak"))


def test_corrupt_json_quarantines_and_starts_empty():
    rp = _registry_path()
    rp.parent.mkdir(parents=True, exist_ok=True)
    # Half-written JSON — common after a power loss / app force-quit
    # mid-flush.
    rp.write_text('{"workspaces": {"ws_a":', encoding="utf-8")

    from services.registry import Registry
    reg = Registry.instance()

    assert reg.list_workspaces() == []
    assert _bak_files(), "corrupt file should have been quarantined"

    # The .bak must contain the ORIGINAL bad bytes, not be silently
    # overwritten — manual recovery depends on this.
    backup = _bak_files()[0]
    assert backup.read_text(encoding="utf-8").startswith('{"workspaces"')


def test_wrong_top_level_shape_is_quarantined():
    """A registry that's valid JSON but a list (rather than an
    object) is just as broken — must not be silently accepted."""
    rp = _registry_path()
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text('["not", "a", "registry"]', encoding="utf-8")

    from services.registry import Registry
    reg = Registry.instance()

    assert reg.list_workspaces() == []
    assert _bak_files()


def test_workspaces_being_a_list_recovers_to_empty_dict():
    """Half-corruption: outer dict OK but `workspaces` is the wrong
    type. We coerce to {} rather than crash on the next write."""
    rp = _registry_path()
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(
        json.dumps({"workspaces": ["bad"], "sessions": {}}),
        encoding="utf-8",
    )

    from services.registry import Registry
    reg = Registry.instance()

    # Loaded cleanly; workspaces was coerced to empty.
    assert reg.list_workspaces() == []

    # Subsequent writes don't blow up — the dict shape was repaired
    # in memory and the next flush will rewrite the file correctly.
    folder = Path(os.environ["PI_DATA_ROOT"]) / "ws-folder"
    folder.mkdir()
    rec = reg.register_desktop_workspace(
        path=str(folder), name="recovered", owner_user_id="u_a"
    )
    assert rec["id"]
    assert rp.read_text(encoding="utf-8")  # was rewritten


def test_missing_file_is_not_quarantined():
    """First launch — registry.json doesn't exist yet. We must NOT
    leave a stray .bak in that case (would confuse `ls -la` for new
    users)."""
    from services.registry import Registry
    reg = Registry.instance()
    assert reg.list_workspaces() == []
    assert _bak_files() == []


def test_valid_registry_loads_normally():
    rp = _registry_path()
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(
        json.dumps({"workspaces": {}, "sessions": {}}),
        encoding="utf-8",
    )
    from services.registry import Registry
    reg = Registry.instance()
    assert reg.list_workspaces() == []
    assert _bak_files() == []
