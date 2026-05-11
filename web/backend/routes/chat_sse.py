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


# ── auto-titling ────────────────────────────────────────────────────
#
# Mirror of routes/chat_ws.py's title flow, ported to SSE: on the first
# user prompt of a chat we set a heuristic title in the registry, fan
# `_session_titled` out via the runtime's event ring so the active SPA
# tab updates its picker without a full reload, then fire a background
# task that asks the title-gen LLM for a polished version and CAS-
# replaces the heuristic. Without this the picker shows "Untitled chat"
# forever on SSE-only clients (the WS handler is the only place that
# used to do this).


def _title_heuristic(prompt: str) -> str:
    """Same heuristic the WS handler uses. Lazy import to avoid cycles."""
    from routes.chat_ws import _derive_title  # local import to avoid cycles
    return _derive_title(prompt)


async def _upgrade_title_via_llm(
    rt: SessionRuntime,
    prompt_text: str,
    heuristic_title: str,
) -> None:
    """Background task: ask the title-gen LLM for a polished title and
    CAS-swap it in place of the heuristic. Best-effort; never raises."""
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
        return
    rt.broadcast_meta_event({
        "type": "_session_titled",
        "sessionId": rt.session_id,
        "title": rec["title"],
        "workspaceId": rec.get("workspace_id"),
    })


def _kick_title_flow(rt: SessionRuntime, msg: str) -> None:
    """Place the heuristic title and schedule the LLM upgrade. Idempotent."""
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
        rt._title_kicked = True  # type: ignore[attr-defined]
        return
    rt._title_kicked = True  # type: ignore[attr-defined]
    rt.broadcast_meta_event({
        "type": "_session_titled",
        "sessionId": rt.session_id,
        "title": placed["title"],
        "workspaceId": placed.get("workspace_id"),
    })
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
    # for plan).
    from services.billing import CreditLedger  # local to avoid cycles
    plan_id = CreditLedger.instance().get_plan_id(user_id)
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

    # BYOK gate — if no key path exists for the model, refuse.
    if BYOK_MODE and active_model_spec is not None:
        from services.byok import byok_provider_for as _byok_pf  # noqa: E402
        if _byok_pf(active_model_spec) is None:
            log_error(
                "setup_required",
                session_id=session_id,
                user_id=user_id,
                where="sse_byok_gate",
                model=active_model_id,
            )
            raise HTTPException(
                status_code=402,
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

    # Burst cap + per-user concurrent-chat cap (the latter pegs to
    # this runtime's lifetime — released by the reaper, not by the
    # request).
    if not rl.try_take(user_id, "ws.connect"):
        raise HTTPException(status_code=429, detail=bridge_error("rate_limit"))

    # Chat-slot budget: only count this runtime once. The slot is
    # released when the runtime is closed (see _release_slot below).
    # We use a sentinel attribute on the runtime to track "this
    # runtime owns a slot for user X".
    if not getattr(rt, "_chat_slot_held", False):
        granted, current, cap = rl.acquire_chat_slot(user_id)
        if not granted:
            raise HTTPException(
                status_code=409,
                detail={
                    **bridge_error("too_many_chats"),
                    "current": current,
                    "cap": cap,
                },
            )
        # Mark the runtime so we know to release on close.
        rt._chat_slot_held = True  # type: ignore[attr-defined]

        # Patch close() to release the slot.
        original_close = rt.close

        async def close_and_release() -> None:
            try:
                await original_close()
            finally:
                if getattr(rt, "_chat_slot_held", False):
                    RateLimiter.instance().release_chat_slot(user_id)
                    rt._chat_slot_held = False  # type: ignore[attr-defined]

        rt.close = close_and_release  # type: ignore[method-assign]

    # Pi spawn rate-limit (separate bucket so a spammy reconnecter
    # can't burn the spawn budget — but here it only triggers on
    # FIRST prompt, since pi stays alive between prompts).
    if rt._pi is None and not rl.try_take(user_id, "pi.spawn"):  # noqa: SLF001
        raise HTTPException(status_code=429, detail=bridge_error("rate_limit"))

    # Auto-title the chat from the first user prompt. Idempotent across
    # subsequent prompts in the same runtime — see `_kick_title_flow`
    # for the guards.
    _kick_title_flow(rt, body.message)

    try:
        request_id = await rt.send_prompt(body.message, request_id=body.request_id)
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

    try:
        while True:
            if await request.is_disconnected():
                break

            now = asyncio.get_event_loop().time()
            timeout = max(0.5, next_keepalive - now)

            try:
                ev_id, evt = await asyncio.wait_for(
                    stream_iter.__anext__(), timeout=timeout
                )
            except asyncio.TimeoutError:
                # No event in the keepalive window — emit a comment.
                yield _KEEPALIVE
                next_keepalive = asyncio.get_event_loop().time() + _KEEPALIVE_INTERVAL_SECONDS
                continue
            except StopAsyncIteration:
                # rt closed — emit a final marker and exit.
                # Same SSE-format rule as _format_sse: NO `event:`
                # field, the marker rides on the JSON `type` so it
                # lands on `onmessage` and the chat.ts dispatcher.
                yield b'data: {"type":"_runtime_ended"}\n\n'
                break

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
