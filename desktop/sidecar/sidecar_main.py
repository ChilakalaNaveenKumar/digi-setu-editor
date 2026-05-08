"""
Desktop sidecar entry point.

The Tauri shell spawns this binary (after PyInstaller has frozen it
into a single executable) with `--host 127.0.0.1 --port <free>`.
It then runs the same FastAPI app the web mode uses, but bypassing
`uvicorn.run("main:app", ...)`'s string-based import which PyInstaller
can't trace. Importing `app` directly here gives PyInstaller a static
reference it can follow.

This file lives under `desktop/sidecar/`; the PyInstaller spec adds
`desktop/backend/` to sys.path so the existing imports
(`from config import …`, `from routes import …`) keep working.
Web's `web/backend/` is no longer touched — desktop owns its
own fork.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys


def _ensure_backend_on_path() -> None:
    """
    PyInstaller's `pathex` in the spec already adds the desktop
    backend at build time, but in dev (running this script with
    plain `python sidecar_main.py`) we have to do it ourselves so
    `from app import app` resolves.

    Desktop now ships its own forked backend at desktop/backend/.
    The top-level web/backend tree is no longer referenced from
    here — separating the trees was the whole point of the fork.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    desktop_root = os.path.abspath(os.path.join(here, ".."))
    backend = os.path.join(desktop_root, "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)


def main() -> int:
    _ensure_backend_on_path()

    parser = argparse.ArgumentParser(
        description="Digi Setu desktop sidecar (FastAPI + uvicorn)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "0")),
        help="Bind port (0 = OS picks one). Tauri normally chooses one and "
        "passes it explicitly.",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("PI_DESKTOP_LOG_LEVEL", "info"),
        help="uvicorn log level (debug/info/warning/error)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="[sidecar:%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    logging.info("Sidecar booting host=%s port=%s", args.host, args.port)
    logging.info("PI_MODE=%s PI_DATA_ROOT=%s", os.environ.get("PI_MODE"), os.environ.get("PI_DATA_ROOT"))

    # Importing `app` triggers config.py + every route module → if
    # the user's environment is broken (missing dep, bad .env) we
    # surface it BEFORE uvicorn starts so the Tauri shell logs the
    # real cause instead of a port-bind error.
    try:
        from app import app  # type: ignore[import-not-found]
    except Exception:
        logging.exception("Could not import FastAPI app — backend boot failed")
        return 2

    # Tauri sends SIGTERM on app close. Without an explicit handler
    # uvicorn would still shut down (it installs its own) but we add
    # one here so any threads we own also get a chance to exit
    # cleanly.
    def _graceful_exit(signum: int, _frame: object) -> None:
        logging.info("Caught signal %s — exiting", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful_exit)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _graceful_exit)

    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
        workers=1,
        log_level=args.log_level,
        proxy_headers=False,
        access_log=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
