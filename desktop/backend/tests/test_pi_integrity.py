"""
Tests for ``services.pi_integrity`` — the boot hook that mirrors the
bundle's pi-runtime into the user's writable app-data folder, repairs
patch drift, and migrates the legacy ``~/.digi-setu/`` directory.

The fixture in this file builds a tiny but realistic bundle vendor
tree under tmp_path so we never touch the developer's real bundle or
their real data root. ``monkeypatch.setenv`` keeps the platform-
detection helpers honest (we always test against an explicit
``darwin-arm64`` layout regardless of the host running the test).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Fixtures ───────────────────────────────────────────────────────
def _build_bundle(tmp_path: Path, *, anthropic_vertex_body: bytes = b"// canonical\n") -> Path:
    """Build a minimal but layout-correct bundle vendor tree.

    Returns the path to the ``vendor/`` dir (= ``PI_DESKTOP_BUNDLE_VENDOR_DIR``).
    """
    vendor = tmp_path / "bundle" / "vendor"
    vendor.mkdir(parents=True)

    # Bundled Node binary (we just need a file at the right path).
    node_dir = vendor / "node-darwin-arm64" / "bin"
    node_dir.mkdir(parents=True)
    node_bin = node_dir / "node"
    node_bin.write_bytes(b"#!/bin/sh\necho fake-node\n")
    node_bin.chmod(0o755)

    # Pi tree.
    pi_root = vendor / "pi"
    pi_root.mkdir()
    (pi_root / "package.json").write_text(
        json.dumps({"name": "pi-runtime-bundle", "version": "0.1.0"}),
        encoding="utf-8",
    )
    (pi_root / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3}),
        encoding="utf-8",
    )

    # The patched provider file (deep path).
    providers = pi_root / "node_modules" / "@mariozechner" / "pi-ai" / "dist" / "providers"
    providers.mkdir(parents=True)
    (providers / "anthropic-vertex.js").write_bytes(anthropic_vertex_body)

    # Extensions.
    extensions = vendor / "extensions"
    extensions.mkdir()
    (extensions / "typst-tools.ts").write_text("// noop\n", encoding="utf-8")

    # Patch sources staged alongside (the install-pi.sh self-heal step).
    patches = vendor / "patches" / "files"
    patches.mkdir(parents=True)
    (patches / "anthropic-vertex.js").write_bytes(anthropic_vertex_body)
    (vendor / "patches" / "apply-edits.mjs").write_text("// patcher\n", encoding="utf-8")

    return vendor


@pytest.fixture
def force_darwin_arm64(monkeypatch):
    """Pin ``sys.platform`` + machine arch so the layout helper picks
    ``node-darwin-arm64`` regardless of the host CI runner."""
    monkeypatch.setattr("sys.platform", "darwin")

    class _UnameStub:
        machine = "arm64"

    def _uname_stub() -> _UnameStub:
        return _UnameStub()

    import os as _os
    monkeypatch.setattr(_os, "uname", _uname_stub, raising=False)


@pytest.fixture(autouse=True)
def _scrub_runtime_env():
    """Every test starts AND ends with a clean PI_DESKTOP_* env.

    ``ensure_runtime`` deliberately mutates ``os.environ`` (that's how
    pi_session learns which pi to spawn — env is the contract). So we
    snapshot the pre-test env and restore it on teardown, otherwise a
    test that exercises the env-export branch leaks
    ``PI_DESKTOP_PI_DIR`` into unrelated tests in other files
    (``test_llm_proxy`` then sees a bundled-app env without a PORT
    and the local_proxy_base()'s fail-loud branch raises).
    """
    import os
    keys = (
        "PI_DESKTOP_NODE_BIN",
        "PI_DESKTOP_PI_DIR",
        "PI_DESKTOP_VENDOR_DIR",
        "PI_DESKTOP_BUNDLE_VENDOR_DIR",
        "DIGI_SETU_HOME",
        "PI_DATA_ROOT",
    )
    snapshot = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ.pop(k, None)
    try:
        yield
    finally:
        for k, v in snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ── ensure_runtime: fresh install ──────────────────────────────────
def test_fresh_install_mirrors_bundle_into_data_root(tmp_path, force_darwin_arm64):
    bundle = _build_bundle(tmp_path)
    data_root = tmp_path / "user-data"
    data_root.mkdir()

    from services.pi_integrity import ensure_runtime

    node_bin, pi_dir = ensure_runtime(
        bundle_vendor_dir=bundle,
        data_root=data_root,
        legacy_data_root=None,
    )

    # The mirror landed in <data_root>/pi-runtime/.
    runtime = data_root / "pi-runtime"
    assert runtime.exists()
    assert (runtime / "pi" / "package.json").exists()
    assert (runtime / "node-darwin-arm64" / "bin" / "node").exists()
    assert (runtime / "patches" / "files" / "anthropic-vertex.js").exists()

    # Returned paths point at the user folder (NOT the bundle).
    assert node_bin == runtime / "node-darwin-arm64" / "bin" / "node"
    assert pi_dir == runtime / "pi"

    # Manifest written.
    manifest = json.loads((runtime / "MANIFEST.json").read_text())
    assert manifest["manifest_version"] == 1
    assert manifest["bundle_hash"]


def test_fresh_install_exports_user_folder_env(tmp_path, force_darwin_arm64, monkeypatch):
    bundle = _build_bundle(tmp_path)
    data_root = tmp_path / "user-data"

    from services.pi_integrity import ensure_runtime

    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    import os
    runtime = data_root / "pi-runtime"
    assert os.environ["PI_DESKTOP_NODE_BIN"] == str(runtime / "node-darwin-arm64" / "bin" / "node")
    assert os.environ["PI_DESKTOP_PI_DIR"] == str(runtime / "pi")
    assert os.environ["PI_DESKTOP_VENDOR_DIR"] == str(runtime)


# ── ensure_runtime: idempotent on second boot ──────────────────────
def test_second_boot_no_remirror_when_bundle_unchanged(tmp_path, force_darwin_arm64):
    bundle = _build_bundle(tmp_path)
    data_root = tmp_path / "user-data"

    from services.pi_integrity import ensure_runtime
    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    runtime = data_root / "pi-runtime"
    sentinel = runtime / "pi" / "user_marker.txt"
    sentinel.write_text("user wrote this between boots", encoding="utf-8")

    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    # The user-folder copy was preserved (not wiped), so our sentinel
    # survives. This is the contract for "bundle unchanged" — we MUST
    # NOT nuke the user-folder pi-runtime on every boot.
    assert sentinel.exists()
    assert sentinel.read_text() == "user wrote this between boots"


# ── ensure_runtime: bundle bumped → user folder rebuilt ────────────
def test_bundle_version_bump_triggers_remirror(tmp_path, force_darwin_arm64):
    bundle = _build_bundle(tmp_path)
    data_root = tmp_path / "user-data"

    from services.pi_integrity import ensure_runtime
    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    runtime = data_root / "pi-runtime"
    stale = runtime / "pi" / "stale_marker.txt"
    stale.write_text("from old bundle", encoding="utf-8")

    # Simulate a pi version bump: rewrite package.json so the bundle
    # hash differs.
    (bundle / "pi" / "package.json").write_text(
        json.dumps({"name": "pi-runtime-bundle", "version": "0.2.0"}),
        encoding="utf-8",
    )

    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    # The user-folder copy got wiped + rebuilt → stale marker is gone.
    assert not stale.exists()


# ── Patch verify + repair ──────────────────────────────────────────
def test_patch_repair_when_user_folder_drifted(tmp_path, force_darwin_arm64):
    """If something rewrote the patched anthropic-vertex.js in the
    user folder (npm self-update, manual edit, …), the next boot
    must restore the canonical patched version from the bundle."""
    bundle = _build_bundle(tmp_path, anthropic_vertex_body=b"// CANONICAL_PATCH_v1\n")
    data_root = tmp_path / "user-data"

    from services.pi_integrity import ensure_runtime
    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    runtime = data_root / "pi-runtime"
    target = runtime / "pi" / "node_modules" / "@mariozechner" / "pi-ai" / "dist" / "providers" / "anthropic-vertex.js"

    # Simulate drift: something replaced the patched file with an
    # upstream-vanilla version.
    target.write_bytes(b"// upstream-vanilla -- patch lost\n")

    # Run again: bundle hash hasn't changed (no rewrite of source
    # files), so no full mirror — but verify-and-repair must catch
    # the drift on the patch file specifically.
    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    assert target.read_bytes() == b"// CANONICAL_PATCH_v1\n"


def test_patch_install_when_user_file_missing(tmp_path, force_darwin_arm64):
    bundle = _build_bundle(tmp_path)
    data_root = tmp_path / "user-data"

    from services.pi_integrity import ensure_runtime
    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)

    runtime = data_root / "pi-runtime"
    target = runtime / "pi" / "node_modules" / "@mariozechner" / "pi-ai" / "dist" / "providers" / "anthropic-vertex.js"
    target.unlink()
    assert not target.exists()

    ensure_runtime(bundle_vendor_dir=bundle, data_root=data_root)
    assert target.exists()


# ── Legacy migration ───────────────────────────────────────────────
def test_legacy_data_root_migrates_to_new_path(tmp_path, force_darwin_arm64):
    legacy = tmp_path / ".digi-setu"
    legacy.mkdir()
    (legacy / ".env").write_text("ANTHROPIC_API_KEY=sk-ant-test\n", encoding="utf-8")
    (legacy / ".session_id").write_text("sess_abc123\n", encoding="utf-8")
    (legacy / "registry.json").write_text("{}", encoding="utf-8")
    chats = legacy / "chats"
    chats.mkdir()
    (chats / "ws_xxx.jsonl").write_text("{\"hi\": 1}\n", encoding="utf-8")

    bundle = _build_bundle(tmp_path)
    new_root = tmp_path / "Application Support" / "com.digi-setu.desktop"

    from services.pi_integrity import ensure_runtime
    ensure_runtime(
        bundle_vendor_dir=bundle,
        data_root=new_root,
        legacy_data_root=legacy,
    )

    # User data carried over.
    assert (new_root / ".env").read_text() == "ANTHROPIC_API_KEY=sk-ant-test\n"
    assert (new_root / ".session_id").read_text() == "sess_abc123\n"
    assert (new_root / "registry.json").read_text() == "{}"
    assert (new_root / "chats" / "ws_xxx.jsonl").exists()

    # Legacy folder has the marker, so subsequent boots short-circuit.
    assert (legacy / ".migrated_to").exists()
    # Source files were moved (not copied), so legacy is now mostly empty.
    assert not (legacy / ".env").exists()


def test_legacy_migration_skipped_when_target_already_populated(tmp_path, force_darwin_arm64):
    legacy = tmp_path / ".digi-setu"
    legacy.mkdir()
    (legacy / ".env").write_text("LEGACY=1", encoding="utf-8")

    new_root = tmp_path / "new-root"
    new_root.mkdir()
    (new_root / ".env").write_text("FRESH=1", encoding="utf-8")

    bundle = _build_bundle(tmp_path)

    from services.pi_integrity import ensure_runtime
    ensure_runtime(
        bundle_vendor_dir=bundle,
        data_root=new_root,
        legacy_data_root=legacy,
    )

    # Don't trample fresh.
    assert (new_root / ".env").read_text() == "FRESH=1"
    # Legacy untouched (no marker, no move).
    assert (legacy / ".env").read_text() == "LEGACY=1"
    assert not (legacy / ".migrated_to").exists()


def test_legacy_migration_only_moves_known_entries(tmp_path, force_darwin_arm64):
    """``~/.digi-setu/`` is a shared Unix-hidden dotpath; people put
    foreign things there (personal CI tokens, scratch JSON, …). The
    migration MUST only move paths the app itself owns."""
    legacy = tmp_path / ".digi-setu"
    legacy.mkdir()
    (legacy / ".env").write_text("OURS=1", encoding="utf-8")
    (legacy / "registry.json").write_text("{}", encoding="utf-8")
    (legacy / "ci-sa.json").write_text("{\"foreign\": true}", encoding="utf-8")
    (legacy / "gh-mirror-token").write_text("ghp_personal", encoding="utf-8")

    new_root = tmp_path / "new-root"
    bundle = _build_bundle(tmp_path)

    from services.pi_integrity import ensure_runtime
    ensure_runtime(
        bundle_vendor_dir=bundle,
        data_root=new_root,
        legacy_data_root=legacy,
    )

    # Ours moved.
    assert (new_root / ".env").read_text() == "OURS=1"
    assert (new_root / "registry.json").read_text() == "{}"
    assert not (legacy / ".env").exists()

    # Foreign files stayed put — we don't own these.
    assert (legacy / "ci-sa.json").read_text() == "{\"foreign\": true}"
    assert (legacy / "gh-mirror-token").read_text() == "ghp_personal"
    assert not (new_root / "ci-sa.json").exists()
    assert not (new_root / "gh-mirror-token").exists()


def test_legacy_migration_idempotent_via_marker(tmp_path, force_darwin_arm64):
    legacy = tmp_path / ".digi-setu"
    legacy.mkdir()
    (legacy / ".migrated_to").write_text("already done", encoding="utf-8")
    # File that LOOKS like data but should NOT be migrated because
    # the marker is already there.
    (legacy / "stale_chat.jsonl").write_text("ignore me", encoding="utf-8")

    new_root = tmp_path / "new-root"
    bundle = _build_bundle(tmp_path)

    from services.pi_integrity import ensure_runtime
    ensure_runtime(
        bundle_vendor_dir=bundle,
        data_root=new_root,
        legacy_data_root=legacy,
    )

    assert not (new_root / "stale_chat.jsonl").exists()
    assert (legacy / "stale_chat.jsonl").exists()


# ── Bundle missing → graceful no-op ────────────────────────────────
def test_missing_bundle_does_not_crash(tmp_path, force_darwin_arm64):
    """If PI_DESKTOP_BUNDLE_VENDOR_DIR points at a nonexistent path
    (dev loop, testing in a stripped sandbox, …), ensure_runtime must
    log + return safely without writing anything to data_root."""
    nonexistent = tmp_path / "no-such-bundle"
    data_root = tmp_path / "user-data"

    from services.pi_integrity import ensure_runtime
    node_bin, pi_dir = ensure_runtime(
        bundle_vendor_dir=nonexistent,
        data_root=data_root,
    )

    # Returned paths point at the (nonexistent) fallback. The caller
    # is expected to surface a clearer error if it actually tries to
    # spawn pi from these.
    assert "no-such-bundle" in str(node_bin)
    assert "no-such-bundle" in str(pi_dir)


# ── Hash determinism ───────────────────────────────────────────────
def test_bundle_hash_changes_on_patch_source_edit(tmp_path):
    """Editing patches/files/anthropic-vertex.js MUST change the
    bundle hash so the next boot wipes + re-mirrors. Otherwise a
    patch update would silently leave old patches on user disks."""
    from services.pi_integrity import _hash_bundle  # type: ignore[attr-defined]

    bundle = _build_bundle(tmp_path, anthropic_vertex_body=b"// v1\n")
    h1 = _hash_bundle(bundle)

    (bundle / "patches" / "files" / "anthropic-vertex.js").write_bytes(b"// v2\n")
    h2 = _hash_bundle(bundle)

    assert h1 != h2
