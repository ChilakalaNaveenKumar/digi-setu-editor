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

from config import CORS_ORIGINS
from routes import (
    attachments,
    auth_webhook,
    bg,
    billing,
    chat_ws,
    config as config_route,
    feedback,
    files,
    fs,
    health,
    models as models_route,
    prefs,
    sessions,
    snapshots,
    terminal_ws,
    terminals,
    usage,
    workspaces,
)
from services import container_pool, egress_proxy


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
    try:
        await container_pool.cleanup_orphaned_containers()
    except Exception as exc:
        # Cleanup failures are non-fatal — orphans burn a little
        # memory until the next manual `docker rm` but don't break
        # new chats.
        import sys as _sys
        print(f"[lifespan] container_pool cleanup failed: {exc}", file=_sys.stderr)

    egress_proxy.start_egress_proxy()
    try:
        yield
    finally:
        egress_proxy.stop_egress_proxy()


def create_app() -> FastAPI:
    app = FastAPI(
        title="pi-typst-test web bridge",
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

    app.include_router(workspaces.router)
    app.include_router(sessions.router)
    app.include_router(files.router)
    app.include_router(fs.router)
    app.include_router(attachments.router)
    app.include_router(snapshots.router)

    app.include_router(bg.router)
    app.include_router(terminals.router)

    app.include_router(chat_ws.router)
    app.include_router(terminal_ws.router)

    # Public (unauth) auth-side endpoints: webhook + feedback.
    # The webhook is signature-verified, the feedback endpoint requires
    # a signed-in user — they're grouped here only for module locality.
    app.include_router(auth_webhook.router)
    app.include_router(feedback.router)
    app.include_router(usage.router)
    app.include_router(models_route.router)
    app.include_router(billing.router)
    app.include_router(prefs.router)

    return app


app = create_app()
