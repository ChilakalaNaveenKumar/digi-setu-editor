"""
FastAPI app factory.

Boring on purpose: this module wires the app together but contains no
business logic. Routes live in `routes/`, services in `services/`, models
in `models/`. To add a new endpoint, drop a file in `routes/` exporting an
APIRouter and `include_router` it here.

Production layout: Caddy on the host serves the Vue SPA from
/srv/pi/www and reverse-proxies /api/* + /ws/* to this FastAPI on
127.0.0.1:8788. We never serve static files from here — the
`PI_FRONTEND_DIST` mount that briefly lived here is gone with the
single-container Cloud Run plan.
"""

from __future__ import annotations

# ── .env loader ────────────────────────────────────────────────────────────
# Load web/backend/.env so PI_TYPST_ROUTER_MODEL, ADMIN_EMAILS, Stripe keys
# etc. take effect without operators having to remember `set -a; source .env`.
# Earlier-set env vars win (matches `dotenv.load_dotenv(override=False)` and
# scripts/env.sh's pattern), so prod can still override via stack.env without
# editing this file.
#
# We deliberately do this BEFORE any other imports so that modules which read
# os.environ at import time (config.py, services/*) see the fully populated
# environment. Without this, web/backend/.env was dead weight and Flash-Lite
# silently leaked in via scripts/env.sh's TYPST_AGENT_ROUTER_MODEL chain.
import os as _os
from pathlib import Path as _Path


def _bootstrap_env() -> None:
    env_file = _Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in _os.environ:
            _os.environ[key] = value


_bootstrap_env()


# ruff: noqa: E402  -- imports below intentionally follow _bootstrap_env()
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS, DEPLOY_MODE
from routes import (
    attachments,
    auth_webhook,
    bg,
    billing,
    chat_sse,
    chat_ws,
    config as config_route,
    desktop_auth,
    feedback,
    files,
    fs,
    health,
    internal,
    llm_proxy,
    models as models_route,
    prefs,
    sessions,
    snapshots,
    terminal_ws,
    terminals,
    usage,
    workspaces,
)
from services import container_pool, dotenv_watcher, egress_proxy


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """
    Backend lifespan. On startup:
      1. Sweep up any pi-session containers left running by a previous
         backend instance that crashed without graceful shutdown
         (services/container_pool.cleanup_orphaned_containers).
      2. Spawn the egress proxy thread (services/egress_proxy) — the
         single chokepoint between every per-session container and
         the outside world.
    On shutdown the egress proxy is torn down. We do NOT kill live
    per-session containers on shutdown: PiSession.close() already
    handles that on per-WS-disconnect, and a clean shutdown sequence
    sends close() to every active session via the chat_ws router's
    own teardown.

    Failure to start the proxy is logged but does not abort backend
    boot — local dev without /srv/pi/state writeable still needs the
    rest of the API to come up. Per-session containers in that mode
    fall back to the subprocess runtime where this proxy isn't on
    the path anyway.
    """
    # Desktop mode runs the agent as a plain subprocess on the user's
    # own machine — no Docker, no per-session containers, no egress
    # MITM proxy. Skipping the container pool sweep + egress proxy
    # avoids spurious "/srv/pi/state read-only" warnings on first
    # launch and keeps the boot fast.
    #
    # In desktop mode we DO start the dotenv watcher: it polls
    # ~/.digi-setu/.env and refreshes BYOK state without requiring
    # the user to restart the app every time they drop a key.
    if DEPLOY_MODE == "desktop":
        dotenv_watcher.start()
    if DEPLOY_MODE != "desktop":
        try:
            await container_pool.cleanup_orphaned_containers()
        except Exception as exc:
            # Cleanup failures are non-fatal — orphans burn a little
            # memory until the next manual `docker rm` but don't break
            # new chats.
            import sys as _sys
            print(f"[lifespan] container_pool cleanup failed: {exc}", file=_sys.stderr)

        egress_proxy.start_egress_proxy()

    # Boot the per-session runtime reaper. Idle pi subprocesses
    # are evicted after IDLE_TIMEOUT_SECONDS (default 10 min). The
    # reaper runs in BOTH desktop and cloud deploy modes — in
    # desktop the user benefits from faster shutdown when they
    # close a workspace; in cloud it bounds resident pi memory.
    from services.session_runtime import session_runtime_registry as _srr
    await _srr().start_reaper()

    # File-watcher reaper — see web/backend/app.py for full
    # rationale. Sweeps unreferenced WorkspaceWatchers within
    # REAPER_GRACE_SECS so observer threads + inotify watches
    # don't outlive the SessionRuntime that owned them on any
    # crash path that bypasses the explicit release.
    from services.file_watcher import WatcherRegistry as _WR
    await _WR.instance().start_reaper()

    try:
        yield
    finally:
        if DEPLOY_MODE == "desktop":
            dotenv_watcher.stop()
        if DEPLOY_MODE != "desktop":
            egress_proxy.stop_egress_proxy()
        try:
            from services.session_runtime import session_runtime_registry as _srr
            await _srr().stop_reaper()
        except Exception as exc:  # noqa: BLE001
            import sys as _sys
            print(f"[lifespan] reaper stop failed: {exc}", file=_sys.stderr)
        try:
            from services.file_watcher import WatcherRegistry as _WR
            await _WR.instance().stop_reaper()
        except Exception as exc:  # noqa: BLE001
            import sys as _sys
            print(f"[lifespan] fswatcher reaper stop failed: {exc}", file=_sys.stderr)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Digi Setu desktop sidecar",
        version="0.4.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Order doesn't matter functionally; grouped by concern for readability.
    app.include_router(health.router)
    app.include_router(config_route.router)
    # Loopback-only routes consumed by the spawned pi child (read_doc
    # → markitdown). NOT proxied to the public internet — see
    # routes/internal.py for the full threat model + auth.
    app.include_router(internal.router)

    app.include_router(workspaces.router)
    app.include_router(sessions.router)
    app.include_router(files.router)
    app.include_router(fs.router)
    app.include_router(attachments.router)
    app.include_router(snapshots.router)

    app.include_router(bg.router)
    app.include_router(terminals.router)

    app.include_router(chat_ws.router)
    # SSE-based chat (POST + EventSource). Lives alongside chat_ws
    # during cutover; once the SPA stops opening WS we delete the
    # WS route file. See web/backend/app.py for the rationale.
    app.include_router(chat_sse.router)
    app.include_router(terminal_ws.router)

    # Public (unauth) auth-side endpoints: webhook + feedback +
    # desktop deep-link exchange.
    # auth_webhook is Clerk-signature-verified; feedback requires a
    # signed-in user; desktop-exchange validates a one-time Clerk
    # ticket from the deep-link callback and stamps a session in the
    # local sidecar — only relevant when PI_MODE=desktop.
    app.include_router(auth_webhook.router)
    app.include_router(desktop_auth.router)
    app.include_router(feedback.router)
    app.include_router(usage.router)
    app.include_router(models_route.router)
    app.include_router(billing.router)
    app.include_router(prefs.router)
    # Localhost LLM proxy — JWT-injecting forwarder for non-BYOK
    # signed-in users running pi locally. Targets the cloud relay at
    # ${PI_CLOUD_API_BASE}/v1/relay/* (see web/backend/routes/llm_relay.py).
    # Bound to 127.0.0.1 by the sidecar's listen address; not reachable
    # from the network.
    app.include_router(llm_proxy.router)

    return app


app = create_app()
