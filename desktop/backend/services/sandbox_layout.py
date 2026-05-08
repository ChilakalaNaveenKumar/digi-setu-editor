"""
sandbox_layout — dual-uid permission helpers for /srv/pi/data subtrees.

The web container runs two non-root users:

    app      uid 1100 / gid 1100   — FastAPI backend (this process)
    sandbox  uid 1000 / gid 1000   — pi --mode rpc + AI's bash subprocess

When the backend creates a new workspace / chat / shadow directory, it
needs to chown+chmod the freshly-created tree so the sandbox uid can rw
it via owner permission while the backend keeps rw via secondary group
membership (`app` is a member of group `sandbox`).

This module is the single source of truth for "what mode + ownership does
a sandbox-shared directory get". Every site that mkdir's into the
shared subtrees (workspaces/, chats/, shadows/) calls
`stamp_sandbox_dir` instead of doing chown / chmod by hand.

Behaviour matrix:

    PI_SANDBOX_UID == 0           → no-op. Used on the operator's
                                    laptop where pi runs as the same
                                    user as the backend (no sandbox).

    PI_SANDBOX_UID > 0,           → chown {uid}:{gid}, chmod 2770
    container has CAP_CHOWN         (SGID + rwx for owner+group, none
                                    for other). Files inside inherit
                                    gid {gid} via SGID.

    PI_SANDBOX_UID > 0,           → log a one-shot warning and fall
    container LACKS CAP_CHOWN       through to mkdir-only. The kernel
                                    will refuse the chown with EPERM,
                                    so we don't even attempt it (saves
                                    a noisy stack trace per workspace
                                    creation).

The capability check is done lazily on first use and memoised.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────
# Set via Dockerfile ENV in production (1000) and unset/0 in dev. The
# `os.environ.get` reads happen ONCE at import time so toggling them at
# runtime requires a process restart — fine for our use case (the values
# are baked into the deployed image, not per-request config).
def _read_uid_env(name: str) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return 0
    try:
        value = int(raw)
        return value if value > 0 else 0
    except ValueError:
        logger.warning("ignoring non-integer %s=%r", name, raw)
        return 0


SANDBOX_UID: int = _read_uid_env("PI_SANDBOX_UID")
SANDBOX_GID: int = _read_uid_env("PI_SANDBOX_GID")

# 2770 = setgid + rwx for owner + rwx for group + nothing for other.
# Setgid on a directory makes new files/subdirs inherit the parent's
# gid — that's what makes the dual-uid model work without a chown
# call on every single file written by either side.
SANDBOX_DIR_MODE = 0o2770

# Whether chown actually works inside this container. Probed lazily.
_chown_works: Optional[bool] = None


def _probe_chown() -> bool:
    """
    Test whether the process actually has CAP_CHOWN. The Linux
    chown(2) cap check is only triggered when you ATTEMPT to change
    the uid/gid to a different value than the file currently has —
    `os.chown(path, -1, -1)` is a no-op syscall that doesn't exercise
    the cap, so we can't probe with it.

    Strategy: create a temp file, try to chown it to a uid we can't
    possibly already own (the SANDBOX_UID), then unlink. If the
    chown raises PermissionError we know CAP_CHOWN is missing.

    Cached after first call (the answer is process-lifetime stable).
    """
    global _chown_works
    if _chown_works is not None:
        return _chown_works

    if SANDBOX_UID == 0:
        _chown_works = False
        return False

    import tempfile

    try:
        fd, probe_path = tempfile.mkstemp(prefix=".sandbox_chown_probe_")
        os.close(fd)
    except OSError as exc:
        # Can't even create a temp file — assume chown works and let
        # the actual call surface the real error. Probably an unusual
        # filesystem layout (read-only /tmp without our tmpfs etc.).
        logger.debug("sandbox_layout: probe couldn't create temp file: %s", exc)
        _chown_works = True
        return True

    try:
        os.chown(probe_path, SANDBOX_UID, SANDBOX_GID)
        _chown_works = True
    except PermissionError:
        logger.warning(
            "sandbox_layout: container is running without CAP_CHOWN — "
            "new workspaces will inherit backend ownership and the AI's "
            "bash will hit EACCES on file writes. Add `cap_add: [CHOWN, "
            "FOWNER, SETUID, SETGID]` to the docker-compose backend "
            "service. Falling back to no-op (single-uid mode)."
        )
        _chown_works = False
    except OSError as exc:
        # Unexpected error (e.g. ENOENT after a race). Conservative:
        # assume the cap is present and let real calls surface specifics.
        logger.debug("sandbox_layout: probe got unexpected %s; assuming cap present", exc)
        _chown_works = True
    finally:
        try:
            os.unlink(probe_path)
        except OSError:
            pass

    return _chown_works


def is_active() -> bool:
    """
    True iff the dual-uid sandbox is wired up AND the container has
    the capabilities to chown new dirs. Other modules can use this
    to log informative diagnostics ("running with sandbox isolation")
    or to skip dual-uid-specific code paths in unit tests.
    """
    return SANDBOX_UID > 0 and _probe_chown()


def stamp_sandbox_dir(path: Path) -> None:
    """
    chown(path, SANDBOX_UID, SANDBOX_GID) + chmod(path, 2770).

    Idempotent: re-stamping a dir already in the right state is cheap
    (two syscalls, same metadata).

    No-op when SANDBOX_UID == 0 (development mode where pi runs as
    the operator's uid — nothing to isolate).

    Errors are logged and swallowed: a one-off failure to stamp a
    fresh dir is recoverable by the next call (or by the boot-time
    pi-prepare migration sweep), so we don't want to take the
    request down for a chown EPERM. The probe up-front catches the
    common "CAP_CHOWN missing" case and short-circuits the whole
    helper.
    """
    if SANDBOX_UID == 0:
        return
    if not _probe_chown():
        return
    try:
        os.chown(path, SANDBOX_UID, SANDBOX_GID)
        os.chmod(path, SANDBOX_DIR_MODE)
    except OSError as exc:
        logger.warning("stamp_sandbox_dir(%s) failed: %s", path, exc)


def stamp_sandbox_tree(path: Path) -> None:
    """
    Walk `path` and stamp every directory underneath it. Files keep
    their default ownership but pick up gid SANDBOX_GID via SGID
    inheritance — call this on top of an existing tree (e.g. when a
    pre-existing workspace is found at boot time, or after restoring
    from a GCS backup) to bring it into compliance.
    """
    if SANDBOX_UID == 0:
        return
    if not _probe_chown():
        return
    try:
        stamp_sandbox_dir(path)
        for root, dirs, files in os.walk(path):
            root_p = Path(root)
            for d in dirs:
                stamp_sandbox_dir(root_p / d)
            for f in files:
                fp = root_p / f
                try:
                    os.chown(fp, SANDBOX_UID, SANDBOX_GID)
                    # 0660 = rw owner + rw group, nothing for other.
                    # Matches what the SGID dir would produce for new
                    # files created with umask 0007, but force-applied
                    # for legacy files that may have looser bits.
                    os.chmod(fp, 0o660)
                except OSError as exc:
                    logger.debug("stamp_sandbox_tree file %s: %s", fp, exc)
    except OSError as exc:
        logger.warning("stamp_sandbox_tree(%s) failed: %s", path, exc)
