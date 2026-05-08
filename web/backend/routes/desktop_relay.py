"""
Desktop relay WebSocket — `wss://api.digi-setu.com/v1/ws/desktop-relay`.

Acts as the cloud bridge for desktop clients that have **no BYOK key**
in `~/.digi-setu/.env`. The desktop's local chat WS dispatcher
(``desktop/backend/routes/chat_ws.py``) opens a WebSocket to this
endpoint, forwards user prompts, and streams tokens back. The relay
runs ``pi`` server-side using the operator's existing Vertex
credentials brokered through ``services/egress_proxy.py`` — so the
operator's service-account JSON **never** ships to user laptops.

The full relay-side ``pi`` lifecycle (per-session container, tool
brokering, file round-trip) lands in M3/M4 of
``docs/desktop-architecture.md``. This M2 scaffold proves the wire:

    1. WebSocket upgrade.
    2. Clerk session verification.
    3. Plan / BYOK-state echo so the desktop can render UX.
    4. Heartbeat (ping/pong) so the SPA's connection-status pill works
       end-to-end before any chat traffic flows.

The wire format mirrors the local chat WS schema 1:1 — when M3 lands,
the only thing that changes is which side of the relay drives the
``pi`` subprocess.

Auth contract:
    The browser ``new WebSocket(...)`` API doesn't allow custom
    headers, so the desktop sends the Clerk session token in the
    ``Sec-WebSocket-Protocol: bearer.<token>`` subprotocol. We accept
    that subprotocol on the upgrade and verify the token via the
    existing ``services/auth.py:user_for_websocket`` helper, which
    already understands both the cookie and bearer paths.

    In dev mode (``CLERK_SECRET_KEY`` empty) auth is best-effort: the
    helper returns ``DEV_USER_ID`` so local smoke tests don't need a
    real Clerk session.

Versioning:
    The route is mounted at ``/v1/ws/desktop-relay``. Future protocol
    changes go to ``/v2/...`` so a desktop binary shipped today keeps
    working without a forced upgrade. Don't break v1 — branch the
    schema, don't extend it in place.

Origin / CORS:
    The desktop sends ``Origin: tauri://localhost`` (macOS) or
    ``Origin: https://tauri.localhost`` (Windows). Caddy doesn't gate
    WebSocket Origin by default, but we MAY want to add an allowlist
    once we have a stable list of expected Origins. For v1 we accept
    any Origin and rely on Clerk auth to gate access — same as the
    existing ``/ws/sessions/{sid}`` endpoint.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import BYOK_MODE, DEPLOY_MODE
from services.auth import user_for_websocket
from services.billing import CreditLedger
from services.models_registry import DEFAULT_MODEL_ID, get_model

router = APIRouter()

# Heartbeat cadence. The desktop dispatcher (M3) sends a ``{type:
# "ping"}`` every 25 s; if no message of any kind reaches us in
# IDLE_TIMEOUT_S we assume the connection is dead and close. These
# numbers are conservative — Caddy's ``write_timeout 24h`` covers the
# slow streaming case, but we don't need to keep dead WSs around.
_PING_INTERVAL_S = 25.0
_IDLE_TIMEOUT_S = 90.0


@router.websocket("/v1/ws/desktop-relay")
async def desktop_relay_ws(ws: WebSocket) -> None:
    """
    Cloud-relay WebSocket for desktop clients without BYOK keys.

    M2 scaffold — accepts upgrade, verifies user, sends a
    ``relay_hello`` describing plan + entitlements, then enters a
    ping/pong heartbeat loop. M3 will replace the loop body with the
    actual chat dispatcher (per-session ``PiSession`` + token stream).
    """
    # 1. Accept the subprotocol the desktop will use to ship the Clerk
    #    JWT. Browsers don't allow custom headers on WS upgrade, so the
    #    bearer rides as a subprotocol token: e.g.
    #        Sec-WebSocket-Protocol: bearer.eyJhbGciOi...
    #    The standard `user_for_websocket` already pulls a token from
    #    headers OR query params; we extend it here with the
    #    subprotocol path before delegating.
    requested_protos = ws.headers.get("sec-websocket-protocol", "")
    bearer_token = ""
    accepted_proto = None
    for proto in (p.strip() for p in requested_protos.split(",")):
        if proto.startswith("bearer."):
            bearer_token = proto[len("bearer.") :]
            accepted_proto = proto
            break
    if bearer_token:
        # Mutate the query params view via a wrapper so
        # `user_for_websocket` finds the token without us reaching
        # into Clerk verifier internals.
        ws.scope.setdefault("query_string", b"")
        existing = ws.scope["query_string"].decode("utf-8") if ws.scope["query_string"] else ""
        sep = "&" if existing else ""
        ws.scope["query_string"] = (existing + sep + f"clerk_token={bearer_token}").encode("utf-8")

    await ws.accept(subprotocol=accepted_proto)

    # 2. Verify the Clerk session. ``user_for_websocket`` returns None
    #    when CLERK_SECRET_KEY is set but the token is bad/missing, or
    #    a user_id (``DEV_USER_ID`` in open-dev mode) when valid.
    user_id = await user_for_websocket(ws)
    if not user_id:
        await ws.send_json({
            "type": "_bridge_error",
            "code": "unauthenticated",
            "message": (
                "Sign in at digi-setu.com to enable cloud chat. "
                "Or add an AI key to ~/.digi-setu/.env to use BYOK mode."
            ),
        })
        await ws.close(code=4401)
        return

    # 3. Compute the entitlement summary. The desktop renders the
    #    model picker badges off this — "you can pick CLOUD models
    #    because you're on plan=pro" or "free plan, BYOK only".
    ledger = CreditLedger.instance()
    plan = ledger.get_plan(user_id)
    plan_id = ledger.get_plan_id(user_id)
    default_model = get_model(DEFAULT_MODEL_ID)

    await ws.send_json({
        "type": "relay_hello",
        "user_id": user_id,
        "plan_id": plan_id,
        # Plan-level caps the desktop UI surfaces in Settings/Activity.
        "plan_caps": {
            "monthly_credit_usd": plan.monthly_credit_usd,
            "allowed_models": list(plan.allowed_models or []),
        },
        # Server-side defaults the desktop should fall back to when
        # the user hasn't pinned a model. Mirrors the local chat_ws
        # picker behaviour.
        "default_model_id": default_model.id if default_model else None,
        # Mirror back what the server sees of the *server's* env. The
        # desktop will re-evaluate locally, but this lets us catch
        # drift between client/server expectations during M3 testing.
        "server_byok_mode": BYOK_MODE,
        "server_deploy_mode": DEPLOY_MODE,
        # Protocol version. M3+ will branch on this.
        "protocol_version": 1,
    })

    print(
        f"[desktop_relay] connected user_id={user_id!r} plan={plan_id!r}",
        file=sys.stderr,
    )

    # 4. Heartbeat loop. Two cooperating tasks:
    #      - reader: drains client messages, resets the idle deadline,
    #        echoes pong on ping. Future M3 code will dispatch
    #        user_message / tool_result / permission_response here.
    #      - keeper: closes the socket when no message arrives within
    #        IDLE_TIMEOUT_S.
    last_seen = asyncio.get_event_loop().time()

    async def _reader() -> None:
        nonlocal last_seen
        try:
            while True:
                raw = await ws.receive_text()
                last_seen = asyncio.get_event_loop().time()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_json({
                        "type": "_bridge_error",
                        "code": "bad_json",
                        "message": "relay messages must be JSON objects",
                    })
                    continue

                mtype = (msg.get("type") or "").strip()
                if mtype == "ping":
                    await ws.send_json({"type": "pong", "ts": msg.get("ts")})
                elif mtype == "session_init":
                    # M2 stub. M3 wires this up to spawn a real
                    # PiSession server-side. For now we ack so the
                    # desktop knows the connection is healthy.
                    await ws.send_json({
                        "type": "_bridge_error",
                        "code": "relay_not_ready",
                        "message": (
                            "Desktop relay is in M2 scaffold mode. "
                            "Server-side pi spawn lands in M3. Use "
                            "BYOK locally for now."
                        ),
                    })
                else:
                    # Unknown / future message types: ack but don't
                    # process. Forward-compat for desktop clients
                    # speaking a newer protocol than we know.
                    await ws.send_json({
                        "type": "_bridge_warn",
                        "code": "ignored",
                        "echo": mtype,
                    })
        except WebSocketDisconnect:
            return

    async def _keeper() -> None:
        nonlocal last_seen
        while True:
            await asyncio.sleep(_PING_INTERVAL_S)
            now = asyncio.get_event_loop().time()
            if now - last_seen > _IDLE_TIMEOUT_S:
                # Client went silent — close cleanly so the desktop
                # dispatcher can decide whether to reconnect or surface
                # a "lost connection" toast.
                try:
                    await ws.close(code=4000)
                except Exception:
                    pass
                return

    reader_task = asyncio.create_task(_reader())
    keeper_task = asyncio.create_task(_keeper())
    done, pending = await asyncio.wait(
        {reader_task, keeper_task}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except asyncio.CancelledError:
            pass

    print(f"[desktop_relay] disconnected user_id={user_id!r}", file=sys.stderr)


@router.get("/v1/health")
async def relay_health() -> dict[str, Any]:
    """
    Smoke probe for the api.digi-setu.com Caddy block.

    Returns 200 with a tiny JSON body. Useful for monitoring
    (Pingdom / Cloudflare health checks) and for the desktop's
    pre-flight check before opening the relay WebSocket — if /v1/health
    fails, we know the api subdomain itself is down and can show a
    cleaner error than a generic WebSocket close code.
    """
    return {
        "status": "ok",
        "service": "desktop-relay",
        "deploy_mode": DEPLOY_MODE,
        "protocol_version": 1,
    }
