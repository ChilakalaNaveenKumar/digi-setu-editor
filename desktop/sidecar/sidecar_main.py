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


def _ensure_ssl_certs() -> None:
    """Point Python's stdlib `ssl` at certifi's CA bundle.

    When PyInstaller freezes the interpreter on macOS / Windows the
    resulting binary doesn't ship the system Python's `Install
    Certificates.command` hook, and doesn't fall back to the OS
    keychain either. Symptom in the field: every `urllib.request.urlopen`
    against digi-setu.com (cloud-relay LLM proxy, /api/usage,
    /api/auth/whoami, plan_cache refresh, billing webhook fetch …)
    raises `CERTIFICATE_VERIFY_FAILED`, the cloud-relay handshake
    fails, pi exits immediately, and the chat shows "Something
    went wrong / internal" with no useful log line.

    `certifi` IS bundled (see `desktop/sidecar/pyinstaller.spec`'s
    `collect_data_files("certifi")`), but nothing wires the stdlib
    `ssl` default context to it. Setting `SSL_CERT_FILE` /
    `REQUESTS_CA_BUNDLE` BEFORE any module imports `ssl` makes the
    default context pick up certifi's bundle when it's first asked
    for a certificate. (Modules that have already cached an SSL
    context — e.g. via `urllib3.PoolManager()` at import time — will
    still need a process restart, which is why this runs as the
    first thing in `main()`.)

    On Linux we used to skip silently (distro OpenSSL has the system
    CA store wired up), but the `.deb` we ship via Bitbucket
    Pipelines runs the SAME PyInstaller-frozen Python, which doesn't
    inherit the system Python's `Install Certificates` hook. So we
    apply the same wiring on Linux. The `setdefault` below means any
    user/IT-set `SSL_CERT_FILE` still wins, which preserves corporate
    MITM CA chains where they exist.
    """
    try:
        import certifi  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        # Direct stderr write because the root logger isn't configured
        # yet at this point in the boot sequence — `logging.warning`
        # silently goes nowhere until uvicorn installs handlers.
        print(f"[sidecar] WARN: certifi not importable: {exc}", file=sys.stderr, flush=True)
        return
    ca_path = certifi.where()
    if not os.path.isfile(ca_path):
        print(
            f"[sidecar] WARN: certifi reports {ca_path} but file is missing",
            file=sys.stderr,
            flush=True,
        )
        return
    # `setdefault` so an explicit env override (e.g. corporate MITM
    # CA chain installed by IT) still wins.
    os.environ.setdefault("SSL_CERT_FILE", ca_path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_path)
    # Direct stderr write — see note above on logger not being ready.
    # This line is the smoking-gun proof in field logs that the SSL
    # fix shipped and ran. Don't lower this to a debug level.
    print(
        f"[sidecar] SSL bundle wired to certifi: {ca_path}",
        file=sys.stderr,
        flush=True,
    )


def _ensure_user_tool_paths() -> None:
    """Augment `PATH` so subprocesses can find user-installed tools.

    Problem: when the user launches Digi Setu from the Dock /
    Applications / Start menu, the GUI shell on macOS, Windows and
    most Linux DEs gives the spawned process a **minimal** `PATH`
    (`/usr/bin:/bin:/usr/sbin:/sbin` on macOS, `C:\\Windows\\…` on
    Windows). This does NOT include Homebrew (`/opt/homebrew/bin`,
    `/usr/local/bin`), TeX Live (`/Library/TeX/texbin`), Quarto's
    user install dir, or anywhere `~/.cargo/bin` lives. The user's
    `.zshrc` / `.bash_profile` is never sourced.

    Symptom in the field: pi's `bash` tool runs `quarto render foo.qmd`
    or `pdflatex foo.tex`, the subprocess gets a `command not found`,
    pi reports "I don't have quarto installed", user says "what do
    you mean, I literally just used it in Terminal".

    Fix: at sidecar startup, prepend every standard user-tool path
    that EXISTS on this machine to `PATH`. Existence check means we
    don't add bogus entries to `PATH` (which can slow tool lookup
    and confuse pi's "which tools do I have" probe).

    We prepend (not append) because if the user has BOTH a Homebrew
    Python and a system Python and pi shells out `python`, they
    almost certainly mean the Homebrew one (which their own scripts
    use). Same logic for `node`, `quarto`, every other tool with a
    "system fallback" version.

    Idempotent: re-calling never duplicates entries.
    """
    candidates: list[str] = []
    home = os.path.expanduser("~")

    if sys.platform == "darwin":
        candidates += [
            "/opt/homebrew/bin",                # Apple Silicon Homebrew
            "/opt/homebrew/sbin",
            "/usr/local/bin",                   # Intel Homebrew + manual installs
            "/usr/local/sbin",
            "/Library/TeX/texbin",              # MacTeX / BasicTeX (pdflatex, xelatex)
            f"{home}/.cargo/bin",               # rustup / cargo-install (typst, ripgrep)
            f"{home}/.local/bin",               # pipx, pip --user
            f"{home}/Library/Application Support/Quarto/bin",  # Quarto user install
            f"{home}/.npm-global/bin",          # npm prefix=~/.npm-global
            "/opt/local/bin",                   # MacPorts
            "/opt/local/sbin",
        ]
    elif sys.platform == "win32":
        # Windows installers usually update the system PATH, BUT the
        # Tauri-spawned process gets a snapshot of PATH from before
        # the user's last install. We add the standard scoop/cargo/
        # python-user-install locations as a safety net.
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        candidates += [
            os.path.join(home, "scoop", "shims"),                # Scoop
            os.path.join(home, ".cargo", "bin"),                 # cargo-install
            os.path.join(local_app_data, "Programs", "Quarto", "bin"),
            os.path.join(program_files, "Quarto", "bin"),
            os.path.join(program_files, "R", "R-4.4.0", "bin"),  # best-effort; users often have multiple R versions
            os.path.join(local_app_data, "Programs", "Python", "Python311", "Scripts"),
        ]
    else:
        # Linux .deb: GUI launchers don't source .bashrc, so the
        # spawned process gets only the Wayland/Xorg-set PATH which
        # is usually missing `~/.local/bin` and `~/.cargo/bin`.
        candidates += [
            f"{home}/.cargo/bin",
            f"{home}/.local/bin",
            "/snap/bin",
            "/usr/local/bin",
        ]

    existing = os.environ.get("PATH", "")
    existing_parts = existing.split(os.pathsep) if existing else []
    existing_set = {p for p in existing_parts if p}

    # Prepend in declared order, skipping non-existent dirs and dirs
    # already present (preserves any explicit user/IT-set ordering).
    to_prepend: list[str] = []
    for p in candidates:
        if not p or p in existing_set:
            continue
        if not os.path.isdir(p):
            continue
        to_prepend.append(p)
        existing_set.add(p)

    if to_prepend:
        new_path = os.pathsep.join(to_prepend + existing_parts)
        os.environ["PATH"] = new_path
        # Direct stderr write so this shows up in field logs without
        # depending on the not-yet-configured root logger.
        print(
            f"[sidecar] PATH augmented with: {os.pathsep.join(to_prepend)}",
            file=sys.stderr,
            flush=True,
        )


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
    # SSL certs MUST be wired before anything imports `ssl` for real
    # (urllib, requests, httpx, asyncio.ssl). Has to happen before
    # `_ensure_backend_on_path` because importing `app` later pulls in
    # routes that may construct an SSL context at module load time.
    _ensure_ssl_certs()
    # PATH augmentation MUST happen before pi sessions are spawned so
    # the inherited env passed to the pi child includes Homebrew /
    # Quarto / TeX dirs. Earlier this ran post-import which meant the
    # first `pi.spawn` of a fresh session saw the minimal GUI PATH
    # and reported "quarto not found" until the sidecar was restarted.
    _ensure_user_tool_paths()
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
        logging.info("Importing config...")
        import config as _cfg  # type: ignore[import-not-found]
        logging.info("config imported OK (AUTH_REQUIRED=%s, DEPLOY_MODE=%s)", _cfg.AUTH_REQUIRED, _cfg.DEPLOY_MODE)
        logging.info("Importing routes...")
        from app import app  # type: ignore[import-not-found]
        logging.info("app imported OK")
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
