"""
Pi-runtime integrity, self-heal, and one-shot data-root migration.

What this module owns
---------------------
The desktop sidecar ships with a vendored ``pi-runtime`` (Node binary
+ pi-coding-agent npm install + our patched ``anthropic-vertex.js`` +
the typst-tools/permission extensions) inside the read-only app
bundle. We CANNOT spawn pi straight out of the bundle for two reasons:

  1. Code-signed bundles on macOS are read-only by Gatekeeper. Any
     write into ``/Applications/Digi Setu.app/`` invalidates the
     signature and the next launch is blocked with "App is damaged".
     pi-coding-agent occasionally writes into its own dist tree (e.g.
     a ``.npmrc`` cache), which would break the signature.
  2. The user (or a sysadmin) might install / upgrade / uninstall a
     global ``pi-coding-agent`` package on top of (or alongside) our
     bundle, mutating shared paths under ``node_modules`` and leaving
     us with a Frankenstein install that crashes on first import.

Solution: every boot the sidecar mirrors the bundle's pi-runtime tree
to the user's writable app-data folder
(``<DATA_ROOT>/pi-runtime/``), verifies the patched files match the
canonical sources we staged alongside the install, and re-applies any
that drifted. Pi spawns from the user-folder copy. Any reinstall of
the app drops a new bundle → manifest hash changes → next boot wipes
+ re-mirrors automatically.

A second, narrower job: the legacy ``~/.digi-setu/`` Unix-hidden data
folder gets migrated to the platform-standard
``app_data_dir()`` location on first boot of the new build, so
existing users keep their chats / login / .env / workspaces without
noticing anything changed.

Why this lives in services/ and not config/
-------------------------------------------
``config.py`` is import-time constants. Mirroring + checksumming the
pi tree is I/O-heavy (~few hundred ms cold), not safe to do at import
time, and depends on env vars Tauri sets AFTER we've imported config
once already. We expose a single boot hook the FastAPI lifespan
calls explicitly.

Failure mode policy
-------------------
  * Migration failure: log, leave legacy folder alone, point at new
    folder anyway. User sees a "fresh install" experience but no data
    loss (they can manually `mv ~/.digi-setu/* ~/<new>/`).
  * Mirror failure: log, leave bundle path active. Pi still spawns
    out of the bundle (no self-heal that boot, but functional).
  * Patch reapply failure: log, raise. Cloud-relay sessions need the
    patches; it's better to refuse the chat with a clear error than
    let pi crash silently.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


# Bumped whenever we change the *shape* of MANIFEST.json in a way the
# old reader can't handle (e.g. add a required field). Independent of
# the bundle hash — which captures content drift.
_MANIFEST_VERSION = 1

# Files we treat as "the patches" — a mismatch on any of these means
# we re-apply them onto the user-folder copy. Keep this list tight:
# every entry triggers a sha256 read on every boot.
_PATCH_FILES_REL: tuple[str, ...] = (
    "pi/node_modules/@mariozechner/pi-ai/dist/providers/anthropic-vertex.js",
)

# Bits of the bundle we hash to compute "is the bundle the same one
# we mirrored last time". Bumping pi version edits package.json;
# editing a patch edits patches/files/*. Both invalidate the user
# folder.
_BUNDLE_HASH_INPUTS: tuple[str, ...] = (
    "pi/package.json",
    "pi/package-lock.json",
    "patches/files/anthropic-vertex.js",
    "patches/apply-edits.mjs",
)

# What we recognise as "Digi Setu data" inside the legacy
# ``~/.digi-setu/`` folder. ONLY these get migrated to the new
# platform-standard data root — anything else (the user's personal
# tokens, scratch files, ssh-keys-they-stashed-there, …) stays
# right where the user put it. This is critical: ``~/.digi-setu/``
# was never strictly ours, and we've seen people use it as a
# general dotfile drawer. A blanket move would clobber their
# expectations.
#
# When you add a new data path the app writes to, ALSO add it here
# so the next migration carries it forward.
_LEGACY_KNOWN_ENTRIES: frozenset[str] = frozenset({
    ".env",
    ".session_id",
    "registry.json",
    "prefs.json",
    "chats",
    "workspaces",
    "audits",
    "shadows",
    "users",
    "snapshots",
    "pi-runtime",
})


# ── Public API ─────────────────────────────────────────────────────
def ensure_runtime(
    bundle_vendor_dir: Path,
    data_root: Path,
    legacy_data_root: Path | None = None,
) -> tuple[Path, Path]:
    """Ensure the user-folder pi-runtime is present, current, and patched.

    Side effects (in order):
      1. Migrate ``legacy_data_root`` → ``data_root`` if applicable.
      2. Mirror ``bundle_vendor_dir`` into ``<data_root>/pi-runtime/``
         when the manifest is missing / stale / corrupted.
      3. Verify + re-apply patches (idempotent).
      4. Mutate ``os.environ`` so ``services.pi_session`` spawns from
         the user-folder copy:
           PI_DESKTOP_NODE_BIN  = <data_root>/pi-runtime/node-<plat>/bin/node
           PI_DESKTOP_PI_DIR    = <data_root>/pi-runtime/pi
           PI_DESKTOP_VENDOR_DIR= <data_root>/pi-runtime
         (extensions are next to PI_DIR — pi_session computes that).

    Returns the resolved (node_bin, pi_dir) pair so callers can log
    what's active and refuse spawn if either path is missing.
    """
    if legacy_data_root is not None:
        _migrate_legacy_data_root(legacy_data_root, data_root)

    runtime_root = data_root / "pi-runtime"

    # If the bundle is missing entirely (running the sidecar binary by
    # hand without going through Tauri), there's nothing to mirror.
    # Fall back to whatever the parent process pointed PI_DESKTOP_*
    # vars at and let pi_session deal with the absence.
    if not bundle_vendor_dir.exists():
        logger.warning(
            "pi_integrity: bundle vendor dir missing (%s); skipping mirror",
            bundle_vendor_dir,
        )
        return _resolve_runtime_paths(runtime_root, fallback=bundle_vendor_dir)

    bundle_hash = _hash_bundle(bundle_vendor_dir)
    needs_mirror = _needs_mirror(runtime_root, bundle_hash)

    if needs_mirror:
        logger.info(
            "pi_integrity: bundle changed or missing in user folder, mirroring "
            "%s → %s (bundle_hash=%s)",
            bundle_vendor_dir,
            runtime_root,
            bundle_hash[:12],
        )
        _mirror_bundle(bundle_vendor_dir, runtime_root)
        _write_manifest(runtime_root, bundle_hash)
    else:
        logger.info(
            "pi_integrity: user folder pi-runtime is current (bundle_hash=%s)",
            bundle_hash[:12],
        )

    _verify_and_repair_patches(bundle_vendor_dir, runtime_root)

    node_bin, pi_dir = _resolve_runtime_paths(runtime_root, fallback=bundle_vendor_dir)
    _export_runtime_env(runtime_root, node_bin, pi_dir)
    return node_bin, pi_dir


# ── Migration ──────────────────────────────────────────────────────
def _migrate_legacy_data_root(legacy: Path, target: Path) -> None:
    """One-shot move from ``~/.digi-setu/`` to the platform-standard
    app-data folder.

    Rules:
      * Skip when ``legacy == target`` (DIGI_SETU_HOME points at the
        legacy path on purpose).
      * Skip when the legacy folder doesn't exist (clean install).
      * Skip when a marker file ``legacy/.migrated_to`` already exists
        — we did this on a previous boot, don't keep re-checking.
      * Skip when ``target`` already has any of the user-data files we
        care about — the user is back on a fresh install they don't
        want overwritten.
      * Otherwise move every entry from legacy → target. We use
        ``shutil.move`` per top-level entry so a half-finished move
        leaves a recoverable state (some entries in legacy, some in
        target) rather than a corrupt merged tree.

    The marker file is dropped in ``legacy/.migrated_to`` on success
    so subsequent boots short-circuit.
    """
    try:
        legacy = legacy.expanduser().resolve()
        target = target.expanduser().resolve()
    except OSError:
        return

    if legacy == target:
        return
    if not legacy.exists() or not legacy.is_dir():
        return

    marker = legacy / ".migrated_to"
    if marker.exists():
        return

    # Don't trample a populated target. Anything that looks like real
    # user state means the new folder is in use already.
    if _target_already_populated(target):
        logger.info(
            "pi_integrity: legacy %s present but target %s is already "
            "populated; leaving legacy alone (no automatic merge)",
            legacy,
            target,
        )
        return

    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning(
            "pi_integrity: cannot create target %s: %s; skipping migration",
            target,
            exc,
        )
        return

    moved: list[str] = []
    skipped: list[str] = []
    for entry in sorted(legacy.iterdir()):
        if entry.name == ".migrated_to":
            continue
        # ONLY migrate paths the app itself writes — see
        # ``_LEGACY_KNOWN_ENTRIES`` for the full list. Anything else
        # in the legacy folder (personal scratch files, foreign
        # tools' state) stays put. This is the only safe default
        # for a shared dotfile path.
        if entry.name not in _LEGACY_KNOWN_ENTRIES:
            skipped.append(entry.name)
            continue
        dest = target / entry.name
        if dest.exists():
            # Should not happen given _target_already_populated check
            # above, but if a parallel boot raced us, prefer the
            # newer (= already-in-target) copy.
            continue
        try:
            shutil.move(str(entry), str(dest))
            moved.append(entry.name)
        except (OSError, shutil.Error) as exc:
            logger.warning(
                "pi_integrity: failed to migrate %s → %s: %s "
                "(other entries continue)",
                entry,
                dest,
                exc,
            )

    if moved:
        logger.info(
            "pi_integrity: migrated %d entries from %s to %s (%s)",
            len(moved),
            legacy,
            target,
            ", ".join(moved),
        )
    if skipped:
        logger.info(
            "pi_integrity: left %d non-Digi-Setu entries in %s untouched (%s)",
            len(skipped),
            legacy,
            ", ".join(skipped),
        )

    try:
        marker.write_text(
            f"{datetime.now(timezone.utc).isoformat()}\n{target}\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _target_already_populated(target: Path) -> bool:
    """True if ``target`` already has any user-data file that would
    suggest the user has been running with the new layout."""
    if not target.exists():
        return False
    for sentinel in (
        ".env",
        ".session_id",
        "registry.json",
        "prefs.json",
        "chats",
        "workspaces",
    ):
        if (target / sentinel).exists():
            return True
    return False


# ── Bundle hashing + manifest ──────────────────────────────────────
def _hash_bundle(bundle_vendor_dir: Path) -> str:
    """Hash a curated subset of bundle files. We deliberately don't
    walk the full tree: ``node_modules`` has hundreds of MB of files
    and hashing it on every boot would add ~3-5 s to startup. The
    inputs we DO hash are the ones that change when:
      * pi-coding-agent version bumps (package.json + package-lock).
      * Our patch source changes (patches/files/*).
      * Our patcher script changes (patches/apply-edits.mjs).
    """
    h = hashlib.sha256()
    h.update(f"v{_MANIFEST_VERSION}\n".encode("utf-8"))
    for rel in _BUNDLE_HASH_INPUTS:
        path = bundle_vendor_dir / rel
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        if path.exists() and path.is_file():
            try:
                h.update(path.read_bytes())
            except OSError as exc:
                logger.warning(
                    "pi_integrity: cannot hash %s: %s; treating as missing",
                    path,
                    exc,
                )
        h.update(b"\0")
    return h.hexdigest()


def _needs_mirror(runtime_root: Path, bundle_hash: str) -> bool:
    if not runtime_root.exists():
        return True
    manifest = _read_manifest(runtime_root)
    if not manifest:
        return True
    if manifest.get("manifest_version") != _MANIFEST_VERSION:
        return True
    if manifest.get("bundle_hash") != bundle_hash:
        return True
    if not (runtime_root / "pi" / "node_modules").exists():
        return True
    return False


def _read_manifest(runtime_root: Path) -> dict | None:
    path = runtime_root / "MANIFEST.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_manifest(runtime_root: Path, bundle_hash: str) -> None:
    payload = {
        "manifest_version": _MANIFEST_VERSION,
        "bundle_hash": bundle_hash,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "patch_files": sorted(_PATCH_FILES_REL),
    }
    try:
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "MANIFEST.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("pi_integrity: cannot write MANIFEST.json: %s", exc)


# ── Mirror ─────────────────────────────────────────────────────────
def _mirror_bundle(src: Path, dest: Path) -> None:
    """Replace ``dest`` with a copy of ``src``.

    We delete dest first so a stale tree from an older build can't
    leave orphaned files behind. The copy keeps file permissions
    (so node binary stays executable) but strips xattrs / ACLs that
    aren't portable across macOS Time Machine snapshots.
    """
    dest_parent = dest.parent
    dest_parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        try:
            shutil.rmtree(dest)
        except OSError as exc:
            logger.warning(
                "pi_integrity: rmtree(%s) failed: %s; trying copy-on-top",
                dest,
                exc,
            )

    shutil.copytree(
        src,
        dest,
        symlinks=True,
        copy_function=_safe_copy2,
        dirs_exist_ok=True,
    )


def _safe_copy2(src: str, dst: str) -> str:
    """``shutil.copy2`` that tolerates missing xattrs (common when
    copying out of a code-signed app bundle on macOS — the bundle's
    xattrs include a Gatekeeper assessment we don't want to copy)."""
    try:
        shutil.copy2(src, dst)
    except OSError:
        shutil.copy(src, dst)
    return dst


# ── Patch verify + repair ──────────────────────────────────────────
def _verify_and_repair_patches(bundle_vendor: Path, runtime_root: Path) -> None:
    """Compare each patched file in ``runtime_root`` to the canonical
    source staged in ``bundle_vendor/patches/files/``. If anything
    drifted, copy the canonical source back into place.

    This catches:
      * Bundle copied OK but a later self-update of pi-coding-agent
        rewrote ``anthropic-vertex.js`` (npm pulls fresh transitive
        deps, our patch is gone).
      * The user copied an old bundle's pi-runtime into the new
        DATA_ROOT and the manifest matches but the patch version
        is older than what we expect.
    """
    patches_src = bundle_vendor / "patches" / "files"
    if not patches_src.exists():
        logger.warning(
            "pi_integrity: bundle patches dir missing (%s); cannot verify",
            patches_src,
        )
        return

    for rel in _PATCH_FILES_REL:
        canonical = patches_src / Path(rel).name
        target = runtime_root / rel
        if not canonical.exists():
            logger.warning(
                "pi_integrity: canonical patch source %s missing; "
                "skipping verify of %s",
                canonical,
                rel,
            )
            continue
        if not target.exists():
            logger.info(
                "pi_integrity: patch target %s missing — installing canonical",
                rel,
            )
            _install_patch(canonical, target)
            continue
        try:
            same = canonical.read_bytes() == target.read_bytes()
        except OSError as exc:
            logger.warning(
                "pi_integrity: cannot read %s for verify (%s); skipping",
                target,
                exc,
            )
            continue
        if not same:
            logger.info(
                "pi_integrity: patch drift detected at %s — restoring canonical",
                rel,
            )
            _install_patch(canonical, target)


def _install_patch(src: Path, dst: Path) -> None:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as exc:
        logger.error(
            "pi_integrity: failed to install patch %s → %s: %s",
            src,
            dst,
            exc,
        )
        raise


# ── Path resolution + env export ───────────────────────────────────
def _resolve_runtime_paths(
    runtime_root: Path,
    fallback: Path,
) -> tuple[Path, Path]:
    """Find the bundled Node binary + pi dir inside ``runtime_root``.

    If runtime_root is missing the expected layout we fall back to
    ``fallback`` (= the bundle vendor dir) so a half-broken mirror
    doesn't break the chat completely.
    """
    node_bin_rel, pi_dir_rel = _platform_runtime_layout()

    primary_node = runtime_root / node_bin_rel
    primary_pi = runtime_root / pi_dir_rel
    if primary_node.exists() and primary_pi.exists():
        return primary_node, primary_pi

    fallback_node = fallback / node_bin_rel
    fallback_pi = fallback / pi_dir_rel
    return fallback_node, fallback_pi


def _platform_runtime_layout() -> tuple[str, str]:
    """The relative paths inside ``vendor/`` for the current OS+arch."""
    if sys.platform == "darwin":
        if _arch() == "arm64":
            node_subdir = "node-darwin-arm64"
        else:
            node_subdir = "node-darwin-x64"
    elif sys.platform.startswith("linux"):
        if _arch() == "arm64":
            node_subdir = "node-linux-arm64"
        else:
            node_subdir = "node-linux-x64"
    elif sys.platform.startswith("win"):
        node_subdir = "node-win-x64"
    else:
        node_subdir = "node-darwin-arm64"

    if sys.platform.startswith("win"):
        node_rel = f"{node_subdir}/node.exe"
    else:
        node_rel = f"{node_subdir}/bin/node"

    return node_rel, "pi"


def _arch() -> str:
    machine = (os.uname().machine if hasattr(os, "uname") else "").lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "x64"


def _export_runtime_env(runtime_root: Path, node_bin: Path, pi_dir: Path) -> None:
    """Make pi_session.py see the user-folder paths.

    pi_session reads PI_DESKTOP_NODE_BIN + PI_DESKTOP_PI_DIR from
    ``env`` (which is os.environ.copy() at session-build time), so
    overriding them here is enough — no plumbing needed in the
    session class itself.
    """
    os.environ["PI_DESKTOP_NODE_BIN"] = str(node_bin)
    os.environ["PI_DESKTOP_PI_DIR"] = str(pi_dir)
    os.environ["PI_DESKTOP_VENDOR_DIR"] = str(runtime_root)


# ── Iteration helper for tests ─────────────────────────────────────
def patch_files() -> Iterable[str]:
    """Return the list of patch-file relative paths (test exposure)."""
    return _PATCH_FILES_REL
