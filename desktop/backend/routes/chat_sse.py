"""
Chat over POST + Server-Sent Events.

Replaces routes/chat_ws.py's WebSocket transport. Runtime concerns
(pi process, billing, snapshot, fanout) live in
services/session_runtime.SessionRuntime — this module is just the
HTTP wiring.

Endpoint surface
----------------
    POST /api/sessions/{sid}/prompt        body: {message: str, request_id?: str}
    POST /api/sessions/{sid}/abort
    POST /api/sessions/{sid}/permission    body: {prompt_id: str, granted: bool}
    GET  /api/sessions/{sid}/stream        SSE; supports Last-Event-ID
    GET  /api/sessions/{sid}/runtime       JSON status (was pi alive? in-flight?)

Why HTTP+SSE instead of WS
--------------------------
* No reconnect state machine in the client — `EventSource` does
  Last-Event-ID resume natively.
* No "is the connection alive between turns" question — the GET
  /stream is just a tail of the per-session ring buffer; multiple
  consumers can subscribe (e.g. devtools), the request is the only
  state.
* pi spawns lazily on first POST /prompt. An idle reconnect costs
  zero subprocess CPU/RAM. (Old WS path spawned pi on every WS
  upgrade — the prod loop you saw spawned ~340 zombie pi processes
  in a minute.)
* Browser, proxy, CDN, and `curl` all speak SSE without special
  config.

Auth
----
HTTP request auth (`require_user`) covers cookies AND bearer tokens.
EventSource sends cookies automatically for same-origin; for cross-
origin dev (5173 → 8000) the SPA sets `withCredentials: true` and
the CORS middleware in app.py emits `Allow-Credentials: true`.

Rate limit + capacity gates
---------------------------
Moved from "WS open" to "POST /prompt". An idle reconnect doesn't
burn the chat slot; only sending a prompt does. Slot is released
when the runtime is reaped (idle timeout) or `DELETE /runtime`.

iOS Safari
----------
Idle SSE dies after ~30s if no events arrive. We emit a
`:keepalive\\n\\n` comment line every 20s so the connection stays
warm even mid-thought.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import BYOK_MODE
from services.auth import require_user
from services.error_codes import bridge_error, log_error
from services.models_registry import (
    DEFAULT_MODEL_ID,
    get_model,
    is_allowed,
    pick_default_for_plan,
)
from services.rate_limit import RateLimiter
from services.registry import Registry
from services.sandbox_layout import stamp_sandbox_dir
from services.session_runtime import (
    SENTINEL_SINCE,
    SessionRuntime,
    session_runtime_registry,
)
from services.title_gen import generate_title
from services.user_prefs import user_prefs


router = APIRouter()


# Re-use the WS handler's title heuristic so the picker shows the SAME
# initial title regardless of which transport the client is on. Single
# source of truth lives in routes/chat_ws.py — importing into the SSE
# module would create a cycle if chat_ws ever imports back, so we pull
# the function out via a local import inside the helper. Cheap once
# (Python caches the module).
def _title_heuristic(prompt: str) -> str:
    from routes.chat_ws import _derive_title  # local import to avoid cycles
    return _derive_title(prompt)


async def _upgrade_title_via_llm(
    rt: SessionRuntime,
    prompt_text: str,
    heuristic_title: str,
) -> None:
    """Background task: ask the title-gen LLM for a polished title and
    CAS-swap it in place of the heuristic.

    Mirrors ``routes.chat_ws._upgrade_title_via_llm`` minus the WS-
    specific ``ws.send_json`` hop. We push the resulting envelope into
    the runtime's event ring instead, so all attached SSE consumers
    pick it up the same way they pick up agent events.

    Never raises — title generation is best-effort. The heuristic title
    stays in place on any failure.
    """
    try:
        llm_title = await generate_title(prompt_text)
    except Exception as exc:  # noqa: BLE001
        print(
            f"[sse {rt.session_id}] title_gen raised: {exc!r}",
            file=sys.stderr,
        )
        return
    if not llm_title:
        return
    reg = Registry.instance()
    rec = reg.maybe_replace_heuristic_title(rt.session_id, heuristic_title, llm_title)
    if not rec:
        # User renamed the chat (or another tab raced us) before the
        # LLM responded — keep their version.
        return
    rt.broadcast_meta_event({
        "type": "_session_titled",
        "sessionId": rt.session_id,
        "title": rec["title"],
        "workspaceId": rec.get("workspace_id"),
    })


def _kick_title_flow(rt: SessionRuntime, msg: str) -> None:
    """Place the heuristic title and schedule the LLM upgrade.

    No-op if ``msg`` is blank, the registry already has a title, or
    we've already kicked off the LLM upgrade for this runtime. Idempotent
    across multiple prompts in the same chat — we only auto-title from
    the FIRST user message.

    Side effects:
      * Persists the heuristic to the registry (visible to /sessions
        listing immediately).
      * Broadcasts ``_session_titled`` with the heuristic so the active
        SPA tab updates its picker without waiting for the LLM round-trip.
      * Schedules the background LLM upgrade.
    """
    if getattr(rt, "_title_kicked", False):
        return
    text = (msg or "").strip()
    if not text:
        return
    heuristic = _title_heuristic(text)
    if not heuristic:
        return
    reg = Registry.instance()
    placed = reg.maybe_set_initial_title(rt.session_id, heuristic)
    if not placed:
        # User already named the chat from the picker — leave it alone
        # AND don't fire the LLM upgrade (we'd just race their title).
        rt._title_kicked = True  # type: ignore[attr-defined]
        return
    rt._title_kicked = True  # type: ignore[attr-defined]
    rt.broadcast_meta_event({
        "type": "_session_titled",
        "sessionId": rt.session_id,
        "title": placed["title"],
        "workspaceId": placed.get("workspace_id"),
    })
    # Fire-and-forget the LLM upgrade. We deliberately don't keep a
    # handle — the background task survives the request lifecycle and
    # broadcasts via the runtime's ring (no per-request WebSocket to
    # close on us). If the runtime is reaped before the LLM responds
    # the broadcast is a silent no-op (broadcast_meta_event guards on
    # `_closed`).
    asyncio.create_task(
        _upgrade_title_via_llm(rt, text, placed["title"]),
        name=f"title_gen[{rt.session_id}]",
    )


# ── helpers ─────────────────────────────────────────────────────────


async def _resolve_runtime(
    session_id: str,
    user_id: str,
    *,
    create: bool,
) -> SessionRuntime:
    """Look up the runtime for `(session_id, user_id)`.

    `create=True` materialises a fresh SessionRuntime if none exists
    (used by POST /prompt — first prompt of a tab). `create=False`
    returns the existing one or 404s (used by /stream subscribers
    that should never be the first hit).

    All the gating that the old WS handler did at open-time is done
    here so we surface the right HTTP status code:

        404  unknown session / not your session
        503  workspace_missing on disk + can't recreate
        402  upgrade_required (BYOK gate trips)
    """
    reg = Registry.instance()
    sess_rec = reg.get_session(session_id)
    if not sess_rec:
        log_error(
            "session_unknown",
            session_id=session_id,
            user_id=user_id,
            where="sse_resolve",
        )
        raise HTTPException(status_code=404, detail=bridge_error("session_unknown"))

    ws_rec = reg.get_workspace(sess_rec["workspace_id"])
    if not ws_rec:
        log_error(
            "workspace_missing",
            session_id=session_id,
            user_id=user_id,
            workspace_id=sess_rec["workspace_id"],
            where="sse_resolve",
        )
        raise HTTPException(
            status_code=503,
            detail=bridge_error("workspace_missing"),
        )

    # Owner check — collapse into "session_unknown" so a hostile
    # client can't enumerate session ids belonging to other users.
    if ws_rec.get("owner_user_id") != user_id:
        log_error(
            "session_unknown",
            session_id=session_id,
            user_id=user_id,
            where="sse_owner_check",
            actual_owner=ws_rec.get("owner_user_id"),
        )
        raise HTTPException(status_code=404, detail=bridge_error("session_unknown"))

    workspace_path = Path(ws_rec["path"])

    # Self-heal a missing workspace dir (same affordance as the old
    # WS handler — registry rows can outlive disk if someone wiped
    # web/data/workspaces/ during dev).
    if not workspace_path.exists():
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
            stamp_sandbox_dir(workspace_path)
        except OSError as exc:
            log_error(
                "workspace_missing",
                session_id=session_id,
                user_id=user_id,
                exc=exc,
                where="sse_recreate_workspace_dir",
                workspace_path=str(workspace_path),
            )
            raise HTTPException(
                status_code=503, detail=bridge_error("workspace_missing")
            ) from exc

    runtime_reg = session_runtime_registry()
    existing = runtime_reg.get(session_id)
    if existing is not None:
        return existing
    if not create:
        # Stream subscriber arrived before any prompt was sent.
        # Build a runtime so the SPA can attach to events the
        # moment pi spawns; we don't auto-spawn pi here.
        pass

    # Decide which model to use — same logic the old WS handler had
    # (pinned model on session, else workspace default, else cheapest
    # for plan). Desktop has no local CreditLedger (Stripe/credit
    # state lives in the cloud); we use the cloud-cached plan id
    # exactly like routes/chat_ws.py does.
    from services.plan_cache import get_plan_id as _get_plan_id  # local to avoid cycles
    plan_id = _get_plan_id(user_id)
    pinned_model = (sess_rec.get("model") or "").strip()
    workspace_default = (
        user_prefs().get_workspace_model(user_id, sess_rec["workspace_id"]) or ""
    )
    if pinned_model and is_allowed(pinned_model, plan_id):
        active_model_id = pinned_model
    elif workspace_default and is_allowed(workspace_default, plan_id):
        active_model_id = workspace_default
    else:
        active_model_id = pick_default_for_plan(plan_id)
    active_model_spec = get_model(active_model_id) or get_model(DEFAULT_MODEL_ID)
    pi_provider = active_model_spec.pi_provider if active_model_spec else None

    # BYOK fallback (same as WS path).
    if (
        BYOK_MODE
        and not pinned_model
        and not workspace_default
        and active_model_spec is not None
    ):
        from services.byok import (  # noqa: E402
            byok_default_model,
            byok_provider_for,
        )
        from services.models_registry import _MODELS as _ALL_MODELS  # noqa: E402
        if byok_provider_for(active_model_spec) is None:
            fallback = byok_default_model(list(_ALL_MODELS))
            if fallback is not None:
                active_model_id = fallback
                active_model_spec = get_model(fallback) or active_model_spec
                pi_provider = (
                    active_model_spec.pi_provider if active_model_spec else None
                )

    # ── Spawn-route decision ──────────────────────────────────────
    # Decide where the LLM call goes BEFORE we acquire a runtime, so
    # the runtime is constructed with the right `use_cloud_relay` bit
    # from the start. The matrix is shared with the WS handler via
    # services/relay_spawn.decide_spawn_route — keep both call sites
    # using the helper so a future routing change lands in one place.
    #
    # Why surface a hard error on ws_relay / setup_required instead of
    # silently spawning pi: pi without credentials returns a single
    # `{"type":"response","success":false,"error":"No API key..."}`
    # envelope that the SPA dispatcher discards (it's a command-ack,
    # not an agent turn). The user then sees a chat that "looks fine"
    # but produces no AI response — exactly the bug we're fixing here.
    # Fail loudly at /prompt time so the UI can show a sign-in /
    # upgrade card.
    from routes.desktop_auth import get_cached_desktop_session  # noqa: E402
    from services.relay_spawn import decide_spawn_route  # noqa: E402

    cached_session = get_cached_desktop_session()
    route = decide_spawn_route(
        spec=active_model_spec,
        byok_mode=BYOK_MODE,
        signed_in=cached_session is not None,
    )

    if route.kind == "setup_required":
        log_error(
            "setup_required",
            session_id=session_id,
            user_id=user_id,
            where="sse_route_setup_required",
            model=active_model_id,
            byok_mode=BYOK_MODE,
        )
        raise HTTPException(
            status_code=402 if BYOK_MODE else 401,
            detail={**bridge_error("setup_required"), "code": "upgrade_required"},
        )

    if route.kind == "ws_relay":
        # The SSE transport can't service the legacy WS-relay branch
        # (which requires a bidirectional pi-on-VM channel). Today no
        # production model lands here — keep the explicit error so a
        # future model that does immediately surfaces instead of
        # silently failing. If/when a model needs ws_relay we'll add
        # an SSE-compatible cloud spawn (likely the same /v1/relay
        # endpoint pi already uses for vertex passthrough, just for
        # the new provider).
        log_error(
            "setup_required",
            session_id=session_id,
            user_id=user_id,
            where="sse_route_ws_relay_unsupported",
            model=active_model_id,
        )
        raise HTTPException(
            status_code=503,
            detail={**bridge_error("setup_required"), "code": "upgrade_required"},
        )

    permission_mode = user_prefs().get_permission_mode(user_id, plan_id=plan_id)
    permission_mode_file = user_prefs().ensure_live_file(user_id, permission_mode)

    chats_dir = reg.session_chat_dir(session_id)

    rt = await runtime_reg.acquire(
        session_id=session_id,
        user_id=user_id,
        workspace_path=workspace_path,
        chats_dir=chats_dir,
        model_id=active_model_id,
        provider=pi_provider,
        permission_mode=permission_mode,
        permission_mode_file=permission_mode_file,
        workspace_id=sess_rec["workspace_id"],
        use_cloud_relay=route.use_cloud_relay,
    )

    reg.touch_session(session_id)
    return rt


# ── POST /api/sessions/{sid}/prompt ─────────────────────────────────


class PromptBody(BaseModel):
    message: str = Field(..., max_length=200_000)
    request_id: Optional[str] = None


@router.post("/api/sessions/{sid}/prompt")
async def post_prompt(
    sid: str, body: PromptBody, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    rt = await _resolve_runtime(sid, user_id, create=True)

    rl = RateLimiter.instance()

    # Burst cap. Desktop has no per-user concurrent-chat cap (single-
    # user app — `acquire_chat_slot` exists only in the multi-tenant
    # web RateLimiter). The cloud relay still rate-limits per Clerk
    # user id at its layer, so a runaway client can't burn through
    # the org quota by spinning chats locally.
    if not rl.try_take(user_id, "ws.connect"):
        raise HTTPException(status_code=429, detail=bridge_error("rate_limit"))

    # Pi spawn rate-limit (separate bucket so a spammy reconnecter
    # can't burn the spawn budget — but here it only triggers on
    # FIRST prompt, since pi stays alive between prompts).
    if rt._pi is None and not rl.try_take(user_id, "pi.spawn"):  # noqa: SLF001
        raise HTTPException(status_code=429, detail=bridge_error("rate_limit"))

    # Probe the user's machine + seed `.digi-setu/AGENTS.md` + the
    # `compile-loop` skill on first prompt per workspace (or whenever
    # AGENTS.md is older than a week). Fire-and-forget on errors —
    # missing skills should never block a chat.
    try:
        from services import skills as _skills

        await _skills.ensure_workspace_skills(Path(rt.workspace_path))
        prefix = _skills.assemble_turn_prefix(Path(rt.workspace_path), body.message)
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[chat_sse] skill prep failed: {exc}", file=sys.stderr)
        prefix = ""

    augmented_message = (prefix + body.message) if prefix else body.message

    # Auto-title the chat from the first user prompt. Idempotent across
    # subsequent prompts in the same runtime — see `_kick_title_flow`
    # for the matrix. Title generation reads the raw user text, not the
    # skill-augmented one.
    _kick_title_flow(rt, body.message)

    try:
        request_id = await rt.send_prompt(augmented_message, request_id=body.request_id)
    except RuntimeError as exc:
        # session runtime closed mid-flight (raced with reaper)
        log_error(
            "internal",
            session_id=sid,
            user_id=user_id,
            exc=exc,
            where="post_prompt",
        )
        raise HTTPException(status_code=503, detail=bridge_error("internal")) from exc

    return {"request_id": request_id, "session_id": sid}


# ── POST /api/sessions/{sid}/abort ──────────────────────────────────


@router.post("/api/sessions/{sid}/abort")
async def post_abort(
    sid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    rt = session_runtime_registry().get(sid)
    if rt is None:
        # No-op if no live runtime — abort on idle is a safe success.
        return {"ok": True, "noop": True}
    # Owner check via _resolve_runtime (cheap repeat is fine here —
    # protects against a hostile client guessing other people's sids).
    await _resolve_runtime(sid, user_id, create=False)
    await rt.abort()
    return {"ok": True}


# ── POST /api/sessions/{sid}/permission ─────────────────────────────


class PermissionBody(BaseModel):
    prompt_id: str
    granted: bool


@router.post("/api/sessions/{sid}/permission")
async def post_permission(
    sid: str,
    body: PermissionBody,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    await _resolve_runtime(sid, user_id, create=False)
    rt = session_runtime_registry().get(sid)
    if rt is None:
        raise HTTPException(status_code=404, detail=bridge_error("session_unknown"))
    ok = await rt.answer_permission(body.prompt_id, body.granted)
    if not ok:
        raise HTTPException(status_code=410, detail={"code": "stale_prompt"})
    return {"ok": True}


# ── GET /api/sessions/{sid}/runtime ─────────────────────────────────


@router.get("/api/sessions/{sid}/runtime")
async def get_runtime_status(
    sid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    await _resolve_runtime(sid, user_id, create=False)
    rt = session_runtime_registry().get(sid)
    return {
        "alive": rt is not None and rt._pi is not None,  # noqa: SLF001
        "in_flight": rt is not None and rt._in_flight,  # noqa: SLF001
        "next_event_id": rt._next_id if rt is not None else 0,  # noqa: SLF001
    }


# ── GET /api/sessions/{sid}/stream (SSE) ────────────────────────────


def _format_sse(ev_id: int, evt: dict[str, Any]) -> bytes:
    """Format one event as an SSE block.

    Spec footgun: if you emit `event: <name>` then EventSource
    routes the event to `addEventListener(<name>, …)` ONLY, and
    the default `onmessage` handler never fires. Our frontend
    listens on `onmessage` and dispatches based on the JSON
    payload's `type` field, so we deliberately omit `event:` —
    every event lands on `onmessage` and the dispatcher in
    chat.ts picks it apart.

    `id:` is kept so EventSource sends it as `Last-Event-ID` on
    automatic reconnects and the backend's ring buffer can
    replay missed events.
    """
    payload = json.dumps(evt, separators=(",", ":"), ensure_ascii=False)
    return (
        f"id: {ev_id}\n"
        f"data: {payload}\n\n"
    ).encode("utf-8")


_KEEPALIVE = b": keepalive\n\n"
_KEEPALIVE_INTERVAL_SECONDS = 20.0


async def _sse_body(
    rt: SessionRuntime,
    *,
    since: int,
    request: Request,
) -> AsyncIterator[bytes]:
    """Generator powering the StreamingResponse.

    Two interleaved sources:
      1. rt.stream(since=…) — events from the ring buffer
      2. asyncio.sleep(20) — keepalive pings (iOS Safari)

    Closes when the client disconnects (request.is_disconnected())
    or when the runtime is closed.
    """
    # Initial comment makes some buggy proxies flush headers
    # immediately so the EventSource onopen fires.
    yield b": connected\n\n"

    stream_iter = rt.stream(since=since).__aiter__()
    next_keepalive = asyncio.get_event_loop().time() + _KEEPALIVE_INTERVAL_SECONDS

    # ── DO NOT inline `await asyncio.wait_for(stream_iter.__anext__(),
    # timeout=…)` here. `wait_for` cancels the inner coroutine on
    # timeout, which propagates a CancelledError *into* the underlying
    # async generator (`rt.stream`) and finalises it — so the next
    # `__anext__()` call raises StopAsyncIteration even though the
    # runtime is perfectly healthy. The user sees a `_runtime_ended`
    # event ~20s after every reconnect and the SPA reopens the stream
    # in a hot loop (mirror of the web-backend fix on 2026-05-16).
    #
    # Fix: hold the pending `__anext__()` as a long-lived task and
    # *shield* it from `wait_for`'s cancellation.
    pending: Optional[asyncio.Task[tuple[int, dict[str, Any]]]] = None
    try:
        while True:
            if await request.is_disconnected():
                break

            if pending is None:
                pending = asyncio.ensure_future(stream_iter.__anext__())

            now = asyncio.get_event_loop().time()
            timeout = max(0.5, next_keepalive - now)

            try:
                ev_id, evt = await asyncio.wait_for(
                    asyncio.shield(pending), timeout=timeout
                )
            except asyncio.TimeoutError:
                # No event in the keepalive window — emit a comment;
                # `pending` keeps running for the next iteration.
                yield _KEEPALIVE
                next_keepalive = asyncio.get_event_loop().time() + _KEEPALIVE_INTERVAL_SECONDS
                continue
            except StopAsyncIteration:
                # rt closed — emit a final marker and exit.
                # Same SSE-format rule as _format_sse: NO `event:`
                # field, the marker rides on the JSON `type` so it
                # lands on `onmessage` and the chat.ts dispatcher.
                pending = None
                yield b'data: {"type":"_runtime_ended"}\n\n'
                break

            # Successful event — re-arm pending for the next read.
            pending = None
            yield _format_sse(ev_id, evt)
            next_keepalive = asyncio.get_event_loop().time() + _KEEPALIVE_INTERVAL_SECONDS
    except asyncio.CancelledError:
        # Client disconnected mid-yield — fine. Don't propagate.
        return
    except Exception as exc:  # noqa: BLE001
        log_error(
            "internal",
            session_id=rt.session_id,
            user_id=rt.user_id,
            exc=exc,
            where="sse_body",
        )
        try:
            yield _format_sse(0, bridge_error("internal"))
        except Exception:  # noqa: BLE001
            pass
    finally:
        # Cancel & drain the pending __anext__() task on any exit
        # path so we don't leak a dangling task on the event loop.
        if pending is not None and not pending.done():
            pending.cancel()
            try:
                await pending
            except (
                asyncio.CancelledError,
                StopAsyncIteration,
                Exception,  # noqa: BLE001
            ):
                pass


@router.get("/api/sessions/{sid}/stream")
async def get_stream(
    sid: str,
    request: Request,
    user_id: str = Depends(require_user),
) -> StreamingResponse:
    # Acquire (or build) the runtime — does NOT spawn pi by itself.
    # Pi spawns when the first POST /prompt arrives.
    rt = await _resolve_runtime(sid, user_id, create=True)

    # Arm the fs+bg fanout NOW so the file tree starts receiving
    # change events the instant the chat pane mounts — without this,
    # the user has to send a prompt (which calls ensure_started)
    # before the tree can refresh on agent writes. See
    # SessionRuntime.ensure_fanout_started() for the full rationale.
    await rt.ensure_fanout_started()

    # Resume from `Last-Event-ID` if the browser is reconnecting.
    last_id_header = request.headers.get("last-event-id") or request.query_params.get("since") or ""
    try:
        since = int(last_id_header) if last_id_header else SENTINEL_SINCE
    except ValueError:
        since = SENTINEL_SINCE

    headers = {
        # Tell ANY intermediary (Cloudflare, Caddy, nginx) not to
        # buffer SSE chunks. Caddy doesn't by default but let's be
        # explicit so a future proxy swap doesn't silently break.
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }

    return StreamingResponse(
        _sse_body(rt, since=since, request=request),
        media_type="text/event-stream",
        headers=headers,
    )


# ── DELETE /api/sessions/{sid}/runtime ──────────────────────────────
# Explicit teardown — currently unused by the SPA (the reaper handles
# it) but useful for tests + admin tooling.


@router.delete("/api/sessions/{sid}/runtime")
async def delete_runtime(
    sid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    await _resolve_runtime(sid, user_id, create=False)
    await session_runtime_registry().evict(sid)
    return {"ok": True}
