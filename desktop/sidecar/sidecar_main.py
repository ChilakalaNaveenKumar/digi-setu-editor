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


def _run_pi_integrity() -> None:
    """Boot hook: mirror the bundle pi-runtime into ``$DIGI_SETU_HOME``
    and migrate the legacy ``~/.digi-setu/`` folder if applicable.

    Skipped silently when the necessary env vars aren't set — that
    happens when running this script by hand from a dev shell
    (``python sidecar_main.py``) rather than under the Tauri shell.
    In that mode the operator is using the local source tree
    directly, no mirroring needed.
    """
    bundle_vendor_str = os.environ.get("PI_DESKTOP_BUNDLE_VENDOR_DIR", "").strip()
    if not bundle_vendor_str:
        logging.info(
            "pi_integrity: PI_DESKTOP_BUNDLE_VENDOR_DIR not set "
            "(dev mode?); skipping mirror"
        )
        return

    from pathlib import Path

    data_root_str = (
        os.environ.get("DIGI_SETU_HOME", "").strip()
        or os.environ.get("PI_DATA_ROOT", "").strip()
    )
    if not data_root_str:
        logging.warning(
            "pi_integrity: neither DIGI_SETU_HOME nor PI_DATA_ROOT set; "
            "cannot determine data root, skipping mirror"
        )
        return

    bundle_vendor = Path(bundle_vendor_str).expanduser()
    data_root = Path(data_root_str).expanduser()

    # Legacy data root we may need to migrate from. Only attempt
    # migration when the new data root is different from
    # ``~/.digi-setu/`` (otherwise we'd self-migrate over and over
    # on a dev box that's still pinned to the legacy path).
    legacy_root = Path.home() / ".digi-setu"
    if legacy_root.resolve() == data_root.resolve():
        legacy_root = None  # no migration needed (dev pinned to legacy)

    from services.pi_integrity import ensure_runtime
    node_bin, pi_dir = ensure_runtime(
        bundle_vendor_dir=bundle_vendor,
        data_root=data_root,
        legacy_data_root=legacy_root,
    )
    logging.info(
        "pi_integrity: active runtime node=%s pi=%s",
        node_bin,
        pi_dir,
    )


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

    # Export the bound port to our OWN environment so child processes
    # (notably the spawned pi-coding-agent runtime) inherit it. Tauri
    # passes the port via `--port <free>` rather than the PORT env var,
    # which means relay_spawn._proxy_base_url() — the function that
    # tells pi where to reach the localhost JWT-injecting LLM proxy —
    # was falling back to its hardcoded "8000" default. On a developer
    # machine that often has another FastAPI listening on :8000 (left
    # over from `uvicorn --reload`), pi's first prompt round-trips to
    # the WRONG server and gets a generic FastAPI 404 in ~50 ms with
    # no entry in the desktop log (because our sidecar never sees the
    # request). End-user symptom: chat shows "Something went wrong"
    # instantly and the pi chat jsonl records `404 {"detail":"Not Found"}`.
    #
    # We set PORT here (not earlier) because args.port can be 0 if the
    # caller wants the OS to pick — uvicorn binds a real port on
    # startup but by then we've already spawned pi. Tauri always picks
    # a real port, so this is safe in practice; the 0-default branch
    # is dev-only (`python sidecar_main.py`).
    if args.port:
        os.environ["PORT"] = str(args.port)

    logging.info("Sidecar booting host=%s port=%s", args.host, args.port)
    logging.info("PI_MODE=%s PI_DATA_ROOT=%s", os.environ.get("PI_MODE"), os.environ.get("PI_DATA_ROOT"))

    # ── pi-runtime self-heal + legacy-folder migration ────────────
    # Mirror the read-only bundle pi-runtime into the user's writable
    # data folder, repair any drifted patches, and migrate
    # ``~/.digi-setu/`` → the new platform-standard data root if the
    # user is upgrading from a pre-app-data-dir build.
    #
    # Order matters: we run BEFORE ``from app import app`` so that
    # config.py picks up the post-migration data root and pi_session
    # reads the user-folder PI_DESKTOP_NODE_BIN / PI_DESKTOP_PI_DIR.
    # Failure here is logged but non-fatal — the worst case is the
    # bundle is used directly, which still works (we just lose the
    # self-heal safety net for that boot).
    try:
        _run_pi_integrity()
    except Exception:
        logging.exception("pi_integrity boot hook failed; continuing with bundle paths")

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
