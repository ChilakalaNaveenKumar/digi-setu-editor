"""
~/.digi-setu/.env file watcher (desktop mode only).

Why this exists:
    Originally the user had to restart Digi Setu every time they
    dropped (or edited) a BYOK key in ``~/.digi-setu/.env``. That
    restart-loop was friction enough that several users abandoned
    BYOK and just signed in instead — defeating the point of the
    BYOK escape hatch. This watcher polls the file every couple of
    seconds and, on mtime change, re-reads it into ``os.environ``
    and recomputes the BYOK module globals via
    ``config.refresh_byok_state``.

Polling, not inotify / FSEvents:
    Polling at 2s feels instant for a user-typed file edit, has zero
    OS-specific dependencies, and never deadlocks the way watchdog
    threads sometimes do under PyInstaller's bundled Python on
    Linux. The cost is one ``os.stat`` per second per running
    sidecar — negligible.

What changes when a refresh fires:
    - ``os.environ`` picks up the new keys (and drops any that the
      user removed from the file).
    - ``config.DETECTED_BYOK_KEYS`` / ``BYOK_MODE`` / ``AUTH_REQUIRED``
      module globals are re-evaluated.
    - The next ``GET /api/config`` returns the refreshed values
      because the route reads via ``import config`` attribute
      access (not the cached ``from config import …`` form).

What this doesn't do (intentionally):
    - Re-spawn the running pi subprocess. If a chat is mid-stream
      with the old keys, we let it finish; new turns pick up the
      new keys naturally.
    - Push a websocket notification to the frontend. The desktop
      app already calls ``/api/config`` on window focus + at boot,
      which is the natural moment for a "I just edited the .env"
      flow (the user is alt-tabbing from Finder back to Digi Setu).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import config


# 2 seconds: well under the human "I just clicked back to the app"
# threshold (typically 5–10s of editor → save → alt-tab) but long
# enough that we're not stat-ing the disk in a tight loop.
_POLL_INTERVAL_S = 2.0

_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _watch_loop(env_path: Path) -> None:
    last_mtime: Optional[float] = None
    try:
        if env_path.exists():
            last_mtime = env_path.stat().st_mtime
    except OSError:
        last_mtime = None

    while not _stop_event.is_set():
        try:
            if env_path.exists():
                current = env_path.stat().st_mtime
                if last_mtime is None or current != last_mtime:
                    last_mtime = current
                    new_state = config.refresh_byok_state()
                    print(
                        f"[dotenv_watcher] {env_path} changed; "
                        f"BYOK state refreshed: {new_state}",
                        file=sys.stderr,
                    )
            else:
                # User deleted the file (or it never existed). Drop
                # any cached BYOK state so we don't keep advertising
                # keys that aren't there anymore.
                if last_mtime is not None:
                    last_mtime = None
                    new_state = config.refresh_byok_state()
                    print(
                        f"[dotenv_watcher] {env_path} disappeared; "
                        f"BYOK state cleared: {new_state}",
                        file=sys.stderr,
                    )
        except Exception as exc:
            # Never let a watcher hiccup take down the sidecar.
            print(
                f"[dotenv_watcher] WARN: poll failed for {env_path}: {exc}",
                file=sys.stderr,
            )
        # Use Event.wait so a stop signal interrupts the sleep
        # immediately on shutdown — no half-second tail latency.
        _stop_event.wait(_POLL_INTERVAL_S)


def start() -> None:
    """Start the watcher thread. No-op outside desktop mode and a
    no-op if called twice (idempotent so the FastAPI startup hook
    doesn't accidentally spawn duplicates if it fires twice in dev
    mode reload scenarios).
    """
    global _thread
    if config.DEPLOY_MODE != "desktop":
        return
    if _thread is not None and _thread.is_alive():
        return

    home = os.environ.get("DIGI_SETU_HOME", "").strip()
    if home:
        env_path = Path(home).expanduser() / ".env"
    else:
        env_path = Path.home() / ".digi-setu" / ".env"

    _stop_event.clear()
    _thread = threading.Thread(
        target=_watch_loop,
        args=(env_path,),
        name="dotenv-watcher",
        daemon=True,
    )
    _thread.start()
    print(
        f"[dotenv_watcher] watching {env_path} for BYOK key changes "
        f"(poll every {_POLL_INTERVAL_S:g}s)",
        file=sys.stderr,
    )


def stop() -> None:
    """Signal the watcher thread to exit. Returns immediately; the
    thread is daemon so process exit will reap it regardless."""
    _stop_event.set()
