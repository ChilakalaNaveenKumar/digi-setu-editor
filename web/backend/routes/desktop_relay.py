"""
Desktop chat-relay WebSocket endpoint.

Endpoint:
    /v1/ws/desktop-relay

Purpose:
    The desktop sidecar opens this WS when it needs to route a chat
    through the cloud (no BYOK key configured but the user is signed
    in to a paid plan). The pi subprocess that backs the chat runs
    HERE on the cloud VM — not on the user's laptop — so the user
    never has to install pi/node/Python locally.

Auth:
    The desktop side ships its Clerk JWT in
    ``Sec-WebSocket-Protocol: bearer.<token>`` because browser-style
    WebSockets can't set custom headers. ``services/auth._WsRequestish``
    already knows how to extract that and feed it to Clerk's verifier.

    Relay-only restriction: we additionally require the request to
    look like it's coming from the desktop (subprotocol-bearer is
    present). Browser SPAs use ``?clerk_token=`` instead, so that path
    can't accidentally end up here.

Lifecycle:
    Per WS connection we create:
      * a fresh transient workspace under web/data/workspaces/ws_XYZ/
        owned by the signed-in user
      * a fresh session inside that workspace
    Both are torn down when the connection closes (the registry's
    background prune sweep is a fallback).

    The user's existing chat history (if any) lives in their other
    sessions and isn't touched. This endpoint is for ephemeral relay
    sessions only — the desktop SPA renders the conversation in its
    own UI and decides whether to persist anything locally.

Protocol surface:
    Identical to /ws/sessions/{sid} — see chat_ws.run_session_loop().
    The desktop side (services/relay_bridge.py) just pipes everything
    through, so any envelope the SPA understands works here too.

    Special: we send one ``relay_hello`` envelope right after accept()
    so the desktop bridge can attach plan info to the local SPA before
    the chat starts.
"""

from __future__ import annotations

import sys
import traceback
from typing import Optional

from fastapi import APIRouter, WebSocket

from config import AUTH_REQUIRED, DEV_USER_ID
from routes.chat_ws import run_session_loop
from services.auth import (
    _WsRequestish,
    _bearer_from_subprotocol,
    negotiated_subprotocol,
    user_for_websocket,
)
from services.billing import CreditLedger
from services.error_codes import bridge_error, log_error
from services.rate_limit import RateLimiter
from services.registry import Registry

router = APIRouter()

# Bumped whenever the relay protocol changes in a way the desktop
# side has to detect. Today there's only v1 — the existing chat
# envelope. v2 will land when we add cloud-side BYOK proxying.
_RELAY_PROTOCOL_VERSION = 1


def _has_bearer_subprotocol(ws: WebSocket) -> bool:
    """True iff the upgrade request carries a `bearer.<jwt>` token in
    the Sec-WebSocket-Protocol list. Used to gate the endpoint to
    desktop callers (browsers can't set this header themselves)."""
    raw = ws.headers.get("sec-websocket-protocol", "")
    return _bearer_from_subprotocol(raw) is not None


@router.websocket("/v1/ws/desktop-relay")
async def desktop_relay(ws: WebSocket) -> None:
    """Cloud chat relay for the Digi Setu desktop app.

    See the module docstring for the contract. In short:
        1. Verify the bearer subprotocol → user_id.
        2. Rate-limit the WS upgrade.
        3. Accept (echoing the bearer subprotocol — required by the
           browser-WS spec even though our client is python-websockets).
        4. Create a transient workspace + session for this connection.
        5. Send `relay_hello` so the desktop bridge can hydrate plan
           info into the local SPA.
        6. Hand off to chat_ws.run_session_loop — the same machinery
           that powers /ws/sessions/{sid}.
        7. Best-effort delete of the transient state on teardown.
    """
    # ── Step 1: auth ───────────────────────────────────────────────
    # In production we require a real Clerk JWT in the subprotocol.
    # In dev mode (AUTH_REQUIRED=False) we allow connections without
    # any token so a developer can poke the endpoint with `wscat`
    # without standing up Clerk locally — the resolved user_id is
    # the synthetic DEV_USER_ID.
    #
    # IMPORTANT: every rejection branch logs WHY. Without these the
    # only signal a 403 was caused by `auth failed` vs `bearer
    # missing` vs `bearer expired` is the tail of the Clerk SDK's
    # own debug output, which `clerk-backend-api` only emits on
    # uncaught exceptions. The desktop side only sees "HTTP 403" so
    # the operator (us) is the only one with enough context to
    # diagnose — these stderr lines are how we get that context.
    client_addr = "?"
    try:
        if ws.client is not None:
            client_addr = f"{ws.client.host}:{ws.client.port}"
    except Exception:
        pass

    if AUTH_REQUIRED and not _has_bearer_subprotocol(ws):
        print(
            f"[desktop_relay] reject reason=missing_bearer_subprotocol "
            f"client={client_addr} sec_ws_proto="
            f"{ws.headers.get('sec-websocket-protocol', '')!r}",
            file=sys.stderr,
        )
        # Closing BEFORE accept yields an HTTP 403 on the upgrade
        # (Starlette hardcodes 403 for pre-accept close). The desktop
        # bridge maps both 401 and 403 to the same "sign-in needs
        # refresh" toast — see services/relay_bridge.py.
        await ws.close(code=4401)
        return

    user_id = await user_for_websocket(ws)
    if user_id is None:
        print(
            f"[desktop_relay] reject reason=clerk_verify_failed "
            f"client={client_addr} "
            f"sec_ws_proto_len={len(ws.headers.get('sec-websocket-protocol', ''))}",
            file=sys.stderr,
        )
        await ws.close(code=4401)
        return

    # ── Step 2: rate-limit the upgrade ─────────────────────────────
    rl = RateLimiter.instance()
    if not rl.try_take(user_id, "ws.connect"):
        await ws.close(code=4429)
        return

    # Concurrent-chat cap: same budget the browser /ws/sessions/* path
    # uses (services/rate_limit.py:_MAX_CONCURRENT_CHATS, default 5).
    # A user with 5 desktop windows already at the cap will get a
    # clean rejection here instead of starving a 6th window forever
    # waiting for backend-ready. The custom 4409 close code lets the
    # desktop relay bridge surface "you have N chats open — close one"
    # rather than a generic disconnect toast.
    granted, current, cap = rl.acquire_chat_slot(user_id)
    if not granted:
        print(
            f"[desktop_relay] reject reason=too_many_chats "
            f"user={user_id} current={current} cap={cap}",
            file=sys.stderr,
        )
        await ws.close(
            code=4409,
            reason=f"too_many_chats:{current}/{cap}",
        )
        return

    # ── Step 3: accept (echo the subprotocol if the client offered) ─
    # RFC 6455 §4.2.2: if the client offered subprotocols the server
    # MUST echo one of them or close the handshake. python-websockets
    # is strict about this on the client side.
    sub_echo = negotiated_subprotocol(ws)
    try:
        if sub_echo:
            await ws.accept(subprotocol=sub_echo)
        else:
            await ws.accept()
    except Exception as exc:
        log_error(
            "internal",
            user_id=user_id,
            exc=exc,
            where="desktop_relay_accept",
        )
        return

    # ── Step 4: create the transient workspace + session ───────────
    reg = Registry.instance()
    transient_workspace_id: Optional[str] = None
    transient_session_id: Optional[str] = None
    try:
        ws_rec = reg.create_web_workspace(
            name=f"relay {user_id[:6]}",
            owner_user_id=user_id,
        )
        transient_workspace_id = ws_rec["id"]
        sess_rec = reg.create_session(workspace_id=transient_workspace_id)
        transient_session_id = sess_rec["id"]
    except Exception as exc:
        log_error(
            "internal",
            user_id=user_id,
            exc=exc,
            where="desktop_relay_provision",
        )
        try:
            await ws.send_json(bridge_error("internal"))
        except Exception:
            pass
        await ws.close(code=1011)
        # Best-effort cleanup if we got partway through.
        if transient_workspace_id is not None:
            try:
                reg.delete_workspace(transient_workspace_id)
            except Exception:
                pass
        # Release the chat slot we reserved in step 2 — the connection
        # never reached the run_session_loop teardown that would
        # normally do this for us.
        rl.release_chat_slot(user_id)
        return

    # ── Step 5: send relay_hello so the bridge can hydrate plan info ─
    plan_id = "free"
    try:
        if user_id != DEV_USER_ID:
            plan_id = CreditLedger.instance().get_plan_id(user_id)
    except Exception as exc:
        # Plan lookup is best-effort — a transient billing-store error
        # shouldn't kill the chat. Default to "free" and let the SPA
        # gate models accordingly.
        print(
            f"[desktop_relay] get_plan_id({user_id}) failed: {exc}",
            file=sys.stderr,
        )
    try:
        await ws.send_json({
            "type": "relay_hello",
            "protocol_version": _RELAY_PROTOCOL_VERSION,
            "plan_id": plan_id,
            "session_id": transient_session_id,
            "workspace_id": transient_workspace_id,
        })
    except Exception as exc:
        log_error(
            "internal",
            user_id=user_id,
            exc=exc,
            where="desktop_relay_hello",
        )
        # Bail before we spawn pi — if we can't even send the hello
        # the connection is already broken at the transport layer.
        try:
            reg.delete_workspace(transient_workspace_id)
        except Exception:
            pass
        rl.release_chat_slot(user_id)
        return

    # ── Step 6: hand off to the shared chat loop ───────────────────
    print(
        f"[desktop_relay] connected user_id={user_id!r} "
        f"session_id={transient_session_id!r} plan={plan_id!r}",
        file=sys.stderr,
    )
    try:
        await run_session_loop(ws, user_id, transient_session_id)
    except Exception as exc:
        # run_session_loop has its own internal error reporting; this
        # catch is the last-resort net so a buggy pump can't poison
        # the relay endpoint's lifecycle.
        log_error(
            "internal",
            user_id=user_id,
            exc=exc,
            where="desktop_relay_loop",
        )
        traceback.print_exc(file=sys.stderr)
    finally:
        # ── Step 7: cleanup transient state ────────────────────────
        # delete_workspace cascades to its sessions + the on-disk
        # sandbox. Idempotent; safe to call even if pieces are gone.
        try:
            reg.delete_workspace(transient_workspace_id)
        except KeyError:
            pass
        except Exception as exc:
            print(
                f"[desktop_relay] cleanup failed for {transient_workspace_id}: {exc}",
                file=sys.stderr,
            )
        # Always release the chat slot we reserved in step 2, even if
        # provisioning + the loop succeeded but a teardown step failed.
        rl.release_chat_slot(user_id)
        print(
            f"[desktop_relay] disconnected user_id={user_id!r} "
            f"session_id={transient_session_id!r}",
            file=sys.stderr,
        )
