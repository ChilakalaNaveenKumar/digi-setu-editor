"""
Cloud-relay WebSocket bridge — desktop side.

When the user has no BYOK key but is signed in via Clerk, the desktop
chat WS dispatcher (``routes/chat_ws.py``) hands the connection off to
this module. We open a second WebSocket from the desktop's local
sidecar to ``wss://api.digi-setu.com/v1/ws/desktop-relay``, then pipe
messages **bidirectionally** so the SPA's existing chat code keeps
talking to ``ws://127.0.0.1:<sidecar-port>`` and never knows the
network hop happened.

Schema:
    Identical to the local chat WS schema in both directions. The
    relay endpoint speaks the same protocol the SPA already renders.
    Any future protocol change MUST update both sides + the
    ``protocol_version`` in ``relay_hello`` (see
    ``web/backend/routes/desktop_relay.py``).

Auth:
    Clerk session JWT carried in the WebSocket subprotocol slot:

        Sec-WebSocket-Protocol: bearer.<token>

    Standard browser WS API doesn't allow custom headers, so we
    encode the bearer as a subprotocol token. The relay endpoint
    pulls it out and verifies via ``services/auth.py``. We use the
    same convention here from the desktop side — the bearer is
    fetched from the user's local Clerk session (cached by
    ``services/desktop_auth_state.py``, see deep-link callback flow).

Failure modes:
    * Cannot resolve api subdomain → emit ``_bridge_error`` with
      ``code="relay_unreachable"`` so the SPA shows a clean toast
      ("You're offline; sign in or add a key to keep chatting").
    * Auth rejected upstream (4401) → emit
      ``code="relay_unauthenticated"`` and prompt re-sign-in.
    * Plan gate (4402) → emit ``code="upgrade_required"`` and surface
      the existing upgrade modal.

Cleanup:
    On either WS closing, the OTHER WS gets closed too. Tasks live
    inside an ``asyncio.gather(..., return_exceptions=True)`` so we
    never leave half-open sockets.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

try:
    # The relay client uses websockets (Python lib, NOT the FastAPI
    # WebSocket class) because it needs to be the CLIENT side of a
    # WS handshake to api.digi-setu.com. FastAPI only ships server-
    # side WS support.
    import websockets  # type: ignore
    from websockets.exceptions import (  # type: ignore
        ConnectionClosed,
        ConnectionClosedError,
    )

    # Status-rejection during the WS upgrade handshake is raised under
    # different class names depending on the websockets lib version:
    #   * websockets <= 12.x  → InvalidStatusCode  (`.status_code` attr)
    #   * websockets >= 13.x  → InvalidStatus      (`.response.status_code`)
    # Real-world environments mix both because pip caches resolve
    # differently per machine. Capture whichever is exported and unify
    # the type for the `except` tuple below.
    _STATUS_EXC: tuple = ()
    try:
        from websockets.exceptions import InvalidStatus as _InvStatus  # type: ignore
        _STATUS_EXC = _STATUS_EXC + (_InvStatus,)
    except ImportError:
        _InvStatus = None  # type: ignore[assignment]
    try:
        from websockets.exceptions import InvalidStatusCode as _InvStatusCode  # type: ignore
        _STATUS_EXC = _STATUS_EXC + (_InvStatusCode,)
    except ImportError:
        _InvStatusCode = None  # type: ignore[assignment]
except ImportError:
    websockets = None  # type: ignore
    ConnectionClosed = ConnectionClosedError = Exception  # type: ignore
    _STATUS_EXC = ()  # type: ignore[assignment]


def _extract_handshake_status(exc: BaseException) -> int:
    """Pull the HTTP status code out of a websockets handshake-rejection
    exception, regardless of which library version raised it. Returns
    0 if the status couldn't be extracted (treat as "unknown")."""
    # New API: exc.response.status_code
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
    # Old API: exc.status_code
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    return 0

from config import PI_RELAY_BASE, PI_RELAY_PATH


def _relay_url() -> str:
    """Compose the full relay WS URL from config bits.

    Accepts both ``https://`` and ``wss://`` (and ``http://``/``ws://``)
    forms of ``PI_RELAY_BASE``. Operators usually configure the env var
    with the same scheme they'd type in a browser (``https://...``)
    because the relay is a TLS-terminated subdomain. ``websockets``
    rejects anything other than ``ws`` / ``wss`` with ``InvalidURI``,
    which crashes the upstream connect and surfaces to the SPA as
    "Something went wrong reaching the cloud chat service" — utterly
    opaque from the user side. Normalising here keeps the
    configuration ergonomic without exposing this footgun.
    """
    base = PI_RELAY_BASE.rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    path = PI_RELAY_PATH if PI_RELAY_PATH.startswith("/") else f"/{PI_RELAY_PATH}"
    return f"{base}{path}"


async def _send_bridge_error(ws: WebSocket, code: str, message: str) -> None:
    """Best-effort error emit. Swallows exceptions because we may be
    racing the local SPA's own disconnect."""
    try:
        await ws.send_json({
            "type": "_bridge_error",
            "code": code,
            "message": message,
        })
    except Exception:
        pass


async def proxy_to_relay(
    local_ws: WebSocket,
    *,
    bearer_token: str,
    user_id: Optional[str],
) -> None:
    """
    Pipe a local desktop chat WS bidirectionally to the cloud relay.

    Flow:
        1. Fail fast if the ``websockets`` package isn't installed
           (operator forgot to redeploy the sidecar after a deps
           bump). Emit a clean error so the user sees an actionable
           toast instead of an internal stack trace.
        2. Open an upstream WS to PI_RELAY_BASE + PI_RELAY_PATH with
           ``bearer.<token>`` in ``Sec-WebSocket-Protocol``.
        3. Wait for the upstream's ``relay_hello`` so we can attach
           the user's plan info to the local SPA. (M4+ will use
           ``plan_id`` to gate model picker badges client-side.)
        4. Spawn two pumps:
              - ``local → upstream``: forwards every JSON message
                from the SPA up to the relay.
              - ``upstream → local``: forwards every relay message
                down to the SPA.
           Both run until either side closes; whichever exits first
           cancels the other and the function returns.

    The caller (``routes/chat_ws.py``) should NOT also try to spawn
    a local PiSession when it routes here — this function owns the
    full life of the WS for as long as the relay branch is active.
    """
    if websockets is None:
        await _send_bridge_error(
            local_ws,
            "relay_unavailable",
            "Cloud relay needs the 'websockets' Python library. "
            "Reinstall the desktop app to fix.",
        )
        return

    relay_url = _relay_url()
    subprotocol = f"bearer.{bearer_token}" if bearer_token else None

    # ── Step 2: connect upstream ────────────────────────────────────
    #
    # IMPORTANT: every `await _send_bridge_error(...)` below uses ONLY
    # short, user-friendly text. Never include raw HTTP codes or
    # exception strings — those land in the chat UI as toasts and
    # trigger user "wtf is this" reactions. The SPA's UiStore.toast()
    # shows the `message` field verbatim. Anything debug-y goes to
    # stderr via `print(..., file=sys.stderr)` so we (operators) can
    # still trace what happened.
    try:
        connect_kwargs: dict = {
            "max_size": 64 * 1024 * 1024,  # 64 MiB cap
            # Cap the upstream handshake so a transient cloud
            # outage / cold DNS / TLS slowness can't pin the user's
            # yellow-dot for the OS's full TCP retry window
            # (~75 s by default on Darwin). 12 s is enough headroom
            # for a healthy round-trip via Caddy + Cloudflare and
            # short enough that the user gets a clear
            # "couldn't reach cloud chat" toast instead of an
            # eternal "connecting…".
            "open_timeout": 12,
            # Keep both directions liveness-checked. websockets'
            # default ping interval is 20s with a 20s ping timeout;
            # tightening helps surface dead upstreams quickly so
            # the SPA's "Reconnect" button is the real recovery
            # path instead of a 75-second OS retry stall.
            "ping_interval": 20,
            "ping_timeout": 20,
        }
        if subprotocol:
            connect_kwargs["subprotocols"] = [subprotocol]
        upstream = await websockets.connect(relay_url, **connect_kwargs)
    except _STATUS_EXC as exc:  # type: ignore[misc]
        # 4xx on the upgrade itself. Most common cases:
        #   401 — Clerk JWT expired or rejected upstream.
        #   403 — Server-side close-before-accept (auth failure path
        #          in routes/desktop_relay.py — Starlette can only
        #          emit 403 on pre-accept rejection).
        #   402 — Plan gate (paid feature, free user).
        # For the user, 401 and 403 mean the same thing: "we couldn't
        # prove you were signed in just now, try again or re-sign in".
        code = _extract_handshake_status(exc)
        print(
            f"[relay_bridge] upstream rejected handshake "
            f"http_status={code} url={relay_url!r} user_id={user_id!r} "
            f"exc={exc!r}",
            file=sys.stderr,
        )
        if code in (401, 403):
            await _send_bridge_error(
                local_ws,
                "relay_unauthenticated",
                "Your sign-in needs to refresh. Click your account "
                "menu and sign in again, then retry your message.",
            )
        elif code == 402:
            await _send_bridge_error(
                local_ws,
                "upgrade_required",
                "This model is part of a paid plan. Upgrade your "
                "account, or add an AI provider key to "
                "~/.digi-setu/.env to chat using your own keys.",
            )
        elif code == 429:
            await _send_bridge_error(
                local_ws,
                "rate_limit",
                "You're sending messages a bit too quickly. Wait "
                "a few seconds and try again.",
            )
        else:
            await _send_bridge_error(
                local_ws,
                "relay_unreachable",
                "Couldn't connect to the cloud chat service. Check "
                "your internet connection, or add an AI provider key "
                "to ~/.digi-setu/.env to chat without the cloud.",
            )
        return
    except (OSError, asyncio.TimeoutError) as exc:
        print(
            f"[relay_bridge] upstream connect failed url={relay_url!r} "
            f"user_id={user_id!r} exc={exc!r}",
            file=sys.stderr,
        )
        await _send_bridge_error(
            local_ws,
            "relay_unreachable",
            "Couldn't reach the cloud chat service. Check your "
            "internet connection, or add an AI provider key to "
            "~/.digi-setu/.env to chat without the cloud.",
        )
        return
    except Exception as exc:  # noqa: BLE001 — defensive last resort
        print(
            f"[relay_bridge] upstream connect raised unexpected "
            f"exception url={relay_url!r} user_id={user_id!r} "
            f"exc_type={type(exc).__name__} exc={exc!r}",
            file=sys.stderr,
        )
        await _send_bridge_error(
            local_ws,
            "relay_error",
            "Something went wrong reaching the cloud chat service. "
            "Try again in a moment.",
        )
        return

    print(
        f"[relay_bridge] connected user_id={user_id!r} url={relay_url!r}",
        file=sys.stderr,
    )

    # ── Step 3 + 4: bidirectional pump ──────────────────────────────
    async def _local_to_upstream() -> None:
        try:
            while True:
                raw = await local_ws.receive_text()
                await upstream.send(raw)
        except WebSocketDisconnect:
            pass
        except (ConnectionClosed, ConnectionClosedError):  # type: ignore[misc]
            pass

    async def _upstream_to_local() -> None:
        try:
            async for raw in upstream:
                # websockets gives bytes for binary frames, str for text.
                # The relay only sends text JSON, but cope with binary
                # defensively.
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                # Validate it parses so a corrupted frame doesn't
                # crash the SPA's JSON parser. Forward unchanged.
                try:
                    json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await local_ws.send_text(raw)
        except (ConnectionClosed, ConnectionClosedError):  # type: ignore[misc]
            pass
        except WebSocketDisconnect:
            pass

    pump_local = asyncio.create_task(_local_to_upstream())
    pump_upstream = asyncio.create_task(_upstream_to_local())
    try:
        done, pending = await asyncio.wait(
            {pump_local, pump_upstream},
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        for task in (pump_local, pump_upstream):
            if not task.done():
                task.cancel()
        for task in (pump_local, pump_upstream):
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await upstream.close()
        except Exception:
            pass

    print(f"[relay_bridge] disconnected user_id={user_id!r}", file=sys.stderr)
