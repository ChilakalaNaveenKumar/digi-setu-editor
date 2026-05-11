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
    admin,
    attachments,
    auth_webhook,
    bg,
    billing,
    chat_sse,
    chat_ws,
    config as config_route,
    desktop_handoff,
    desktop_relay,
    feedback,
    files,
    fs,
    health,
    internal,
    llm_relay,
    models as models_route,
    typst_docs,
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

    # Boot the per-session runtime reaper. Idle pi subprocesses
    # are evicted after IDLE_TIMEOUT_SECONDS (default 10 min) so a
    # tab the user closed an hour ago doesn't keep a docker
    # container resident. See services/session_runtime.py.
    from services.session_runtime import session_runtime_registry as _srr
    await _srr().start_reaper()

    # Boot the file-watcher reaper. Belt-and-braces over the
    # session-runtime reaper above: if a SessionRuntime crash
    # path forgets to release its watcher reference, the watcher
    # reaper sweeps unreferenced WorkspaceWatchers within
    # REAPER_GRACE_SECS so the inotify watch + observer thread
    # don't outlive the session that owned them. Also gives a
    # short grace window so a tab refresh doesn't tear down the
    # observer for the same workspace it's about to re-acquire.
    from services.file_watcher import WatcherRegistry as _WR
    await _WR.instance().start_reaper()

    # ── Pre-warm the Gemini explicit context cache for search_docs ──
    # Per-package caches expire on a 24 h TTL; doing this in the
    # background here means the FIRST real user request finds them
    # already warm. Failures are logged inside the helper and never
    # propagate — startup must not block on a Vertex hiccup.
    import asyncio as _asyncio
    _asyncio.create_task(_prewarm_typst_cache())

    try:
        yield
    finally:
        egress_proxy.stop_egress_proxy()
        # Cancel the reaper. Active runtimes are NOT torn down on
        # backend shutdown (mirroring the existing WS path) — the
        # next backend boot will sweep orphaned containers via
        # container_pool.cleanup_orphaned_containers above.
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


async def _prewarm_typst_cache() -> None:
    """Build all 7 search_docs caches in lockstep at startup. Pulled out
    of the lifespan body so we can ``create_task`` it without the
    nested-function closure ceremony."""
    import sys as _sys

    try:
        from routes.llm_relay import (  # type: ignore
            _adc_token,
            _gcp_project,
            _resolve_google_location,
            _vertex_host,
        )
        from routes.typst_docs import (  # type: ignore
            _RULES,
            _ensure_corpus,
            _persona_for,
            _router_model,
        )
        from services import gemini_cache
    except ImportError as exc:
        print(f"[lifespan] typst-cache prewarm import failed: {exc}", file=_sys.stderr)
        return

    if gemini_cache.is_disabled():
        print("[lifespan] explicit cache disabled — skipping prewarm", file=_sys.stderr)
        return

    try:
        corpus = await _ensure_corpus()
    except Exception as exc:  # noqa: BLE001
        print(f"[lifespan] corpus load failed: {exc}", file=_sys.stderr)
        return

    project = _gcp_project()
    if not project:
        # Most likely a local dev env without GCP wired up — that's
        # fine, the search_docs route returns a clear 503 in that
        # case and there's nothing to cache anyway.
        print("[lifespan] GOOGLE_CLOUD_PROJECT unset; skipping cache prewarm", file=_sys.stderr)
        return

    model_id = _router_model()
    location = _resolve_google_location(model_id)
    host = _vertex_host(location)

    print(
        f"[lifespan] pre-warming typst-docs cache for {len(corpus)} package(s) "
        f"(model={model_id}, location={location})",
        file=_sys.stderr,
    )
    await gemini_cache.prewarm_caches(
        corpus=corpus,
        persona_for=_persona_for,
        rules=_RULES,
        model_id=model_id,
        project=project,
        location=location,
        host=host,
        token_provider=_adc_token,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Digi Setu web bridge",
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
    app.include_router(admin.router)
    app.include_router(config_route.router)
    # Loopback-only routes consumed by the spawned pi child (read_doc
    # → markitdown). NOT proxied by Caddy — see routes/internal.py for
    # the full threat model + auth.
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
    # during the cutover; once the SPA stops opening WS we delete
    # routes/chat_ws.py and services/session_locks.py.
    app.include_router(chat_sse.router)
    app.include_router(terminal_ws.router)
    # Desktop chat-relay WS — sits next to chat_ws because it shares
    # the same protocol surface (delegates to chat_ws.run_session_loop).
    # Requires services/auth's subprotocol-bearer support to be wired,
    # which it is (see _WsRequestish + _bearer_from_subprotocol).
    app.include_router(desktop_relay.router)
    # LLM relay — HTTP edge for desktop "local pi, cloud auth" mode.
    # Forwards Anthropic / Vertex calls with ADC injection, plan
    # gating, rate limiting, and per-call billing. See
    # routes/llm_relay.py for the full threat model.
    app.include_router(llm_relay.router)
    # Typst docs — server-side search_docs so the corpus stays here
    # (not on user laptops) and Vertex's prefix cache hits across
    # users. See routes/typst_docs.py for the full rationale.
    app.include_router(typst_docs.router)

    # Public (unauth) auth-side endpoints: webhook + feedback.
    # auth_webhook is Clerk-signature-verified; feedback requires a
    # signed-in user.
    app.include_router(auth_webhook.router)
    app.include_router(desktop_handoff.router)

    app.include_router(feedback.router)
    app.include_router(usage.router)
    app.include_router(models_route.router)
    app.include_router(billing.router)
    app.include_router(prefs.router)

    return app


app = create_app()
