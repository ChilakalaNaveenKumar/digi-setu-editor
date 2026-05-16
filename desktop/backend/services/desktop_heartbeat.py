"""
Boot-time desktop → cloud heartbeat.

Why this module exists
----------------------
Until now the cloud had no idea which version of the desktop app any
given user was actually running. We could see *who downloaded what*
(via Caddy logs) but not *who's still running it* — and certainly
not "user X has v0.1.0 from May, time to nag them about v0.2.0".

This module is the smallest possible fix:

  1. On every desktop sidecar boot we generate (or re-read) a stable
     ``install_id`` UUID stored at ``$DIGI_SETU_HOME/install_id``.
     This identifies the *machine install*, not the user — a single
     user with three machines yields three install_ids.

  2. We POST ``{install_id, version, platform}`` to
     ``/api/desktop/heartbeat`` exactly once on boot, after auth
     refresh has plausibly completed. The cloud upserts a
     ``desktop_clients`` row keyed on (user_id, install_id).

  3. The cloud's response carries ``latest_version`` and an
     ``update_available`` flag; we don't act on it ourselves yet
     (the auto-updater plugin in the Tauri shell is the source of
     truth for upgrade UX), but we keep it logged so an operator
     can grep "user X is on v0.1.0, update available" out of the
     sidecar log.

What this module is NOT
-----------------------
* Not a polling loop. One POST per boot is enough; the cloud can
  always call us "still alive" via the cached desktop session id
  if it ever needs liveness signals.
* Not a chat / billing dependency. A failed heartbeat is logged
  and dropped — boot does not block on it. The whole point is to
  improve cloud-side observability, not to gate user-facing
  functionality.
* Not a privacy escalation. We send the same install_id every
  boot (so it's stable, useful for "is this client up to date?"
  questions) and the version + platform. Nothing else.

Module-level state
------------------
A class-level guard prevents the heartbeat from firing more than
once per process; if a future caller wires it into a polling
schedule they should call ``start()`` from the lifespan hook
instead.
"""

from __future__ import annotations

import asyncio
import os
import platform
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from config import DATA_ROOT


_HEARTBEAT_FIRED = False
_HEARTBEAT_LOCK = threading.Lock()


def _install_id_path() -> Path:
    """Where the persistent install_id lives. Same data root as the
    rest of the desktop's local-state files; survives app updates
    (the Tauri shell doesn't touch the data root on upgrade) so
    the cloud can correlate runs across versions.
    """
    return Path(DATA_ROOT) / "install_id"


def _read_or_create_install_id() -> str:
    """Read the install_id from disk; if missing, mint a fresh
    uuid4 and write it. Idempotent — concurrent boots (which can't
    happen given Tauri's single-instance plugin, but defensive
    against operator races) all see the same id because file
    creation uses ``x`` mode and we fall back to reading on
    EEXIST.
    """
    p = _install_id_path()
    try:
        return p.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        pass
    new_id = str(uuid.uuid4())
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Exclusive create — second writer races back to the read
        # branch above, and the first writer's value wins.
        with open(p, "x", encoding="utf-8") as fp:
            fp.write(new_id)
        return new_id
    except FileExistsError:
        return p.read_text(encoding="utf-8").strip()


def _platform_string() -> str:
    """Compact ``<system>-<machine>`` platform tag. Examples:
    ``darwin-arm64``, ``linux-x86_64``, ``win32-AMD64``. We
    normalise the system name to match Python's ``sys.platform``
    (lowercase) so the cloud can group cleanly by OS family
    without parsing.
    """
    machine = platform.machine() or "unknown"
    return f"{sys.platform}-{machine}"


def _resolve_version() -> str:
    """Read the bundle version handed in by the Tauri Rust shell
    via ``PI_DESKTOP_APP_VERSION``. Falls back to a sentinel so
    a bare ``python -m web.backend.app`` (i.e. desktop sidecar
    run outside Tauri, e.g. for backend dev) still sends *something*
    rather than failing the heartbeat outright.
    """
    return (os.environ.get("PI_DESKTOP_APP_VERSION", "").strip()
            or "0.0.0-dev")


def _do_heartbeat() -> Optional[dict[str, Any]]:
    """Synchronous, blocking heartbeat call. Returns the cloud's
    response dict on success, ``None`` on any failure. All
    failures are caught — auth not yet ready, network blip, cloud
    5xx — so this can be called speculatively without a try/except
    at the call site.
    """
    try:
        from services.cloud_api import (
            CloudApiAuthError,
            CloudApiError,
            post_json,
        )
    except ImportError as exc:
        print(
            f"[heartbeat] cloud_api unavailable, skipping: {exc}",
            file=sys.stderr,
        )
        return None

    body = {
        "install_id": _read_or_create_install_id(),
        "version": _resolve_version(),
        "platform": _platform_string(),
    }
    try:
        result = post_json("/api/desktop/heartbeat", body)
    except CloudApiAuthError:
        # Signed-out user. Heartbeat is per-user-scoped, so this
        # is a normal state at boot — sign-in usually completes
        # within a few seconds and the next boot picks it up.
        # NOT logged loudly to avoid alarm fatigue.
        return None
    except CloudApiError as exc:
        print(
            f"[heartbeat] cloud rejected heartbeat: {exc} (status={exc.status})",
            file=sys.stderr,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — last-resort guard
        print(f"[heartbeat] unexpected failure: {exc}", file=sys.stderr)
        return None

    if isinstance(result, dict):
        if result.get("update_available"):
            latest = result.get("latest_version", "?")
            print(
                f"[heartbeat] cloud says update available: "
                f"running={body['version']} latest={latest}",
                file=sys.stderr,
            )
        else:
            print(
                f"[heartbeat] cloud accepted heartbeat: "
                f"version={body['version']} platform={body['platform']}",
                file=sys.stderr,
            )
        return result
    return None


def start() -> None:
    """Fire the heartbeat in the background. Idempotent — second
    and subsequent calls in the same process are no-ops.

    Why a background task instead of a synchronous boot step:
    the Clerk JWT cache is populated *asynchronously* during boot
    (the Tauri shell stores the session id in the keychain and the
    sidecar refreshes it on first need). Firing synchronously from
    lifespan would consistently see no JWT and the heartbeat would
    silently 401 every boot. We instead schedule a small delay so
    the auth refresh has time to land.
    """
    global _HEARTBEAT_FIRED
    with _HEARTBEAT_LOCK:
        if _HEARTBEAT_FIRED:
            return
        _HEARTBEAT_FIRED = True

    async def _run() -> None:
        # Give the Tauri shell + auth refresh a couple of seconds
        # to land the cached JWT. We could be smarter here (poll
        # for a session) but the cost of guessing wrong is a
        # silent 401 on the heartbeat — recovered on the next
        # launch — so this is fine.
        await asyncio.sleep(3.0)
        # Hop the blocking urllib call off the event loop. Even
        # cheap calls (200 OK in 30 ms) shouldn't share the loop
        # with chat WS frames during boot.
        await asyncio.to_thread(_do_heartbeat)

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        # No event loop running yet (e.g. called pre-lifespan).
        # Fall back to a thread so we still fire eventually.
        threading.Thread(target=lambda: asyncio.run(_run()), daemon=True).start()
