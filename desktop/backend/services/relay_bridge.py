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
        InvalidStatus,
    )
except ImportError:
    websockets = None  # type: ignore
    ConnectionClosed = ConnectionClosedError = InvalidStatus = Exception  # type: ignore

from config import PI_RELAY_BASE, PI_RELAY_PATH


def _relay_url() -> str:
    """Compose the full relay WS URL from config bits."""
    base = PI_RELAY_BASE.rstrip("/")
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
    try:
        connect_kwargs: dict = {"max_size": 64 * 1024 * 1024}  # 64 MiB cap
        if subprotocol:
            connect_kwargs["subprotocols"] = [subprotocol]
        upstream = await websockets.connect(relay_url, **connect_kwargs)
    except InvalidStatus as exc:  # type: ignore[misc]
        # 4xx on the upgrade itself — usually 401 (bad token) or 403
        # (relay disabled). Surface a code the SPA already knows how
        # to render.
        status = getattr(exc, "response", None)
        code = getattr(status, "status_code", 0) if status else 0
        if code == 401:
            await _send_bridge_error(
                local_ws,
                "relay_unauthenticated",
                "Your sign-in expired. Click 'Sign in' to refresh.",
            )
        elif code == 402:
            await _send_bridge_error(
                local_ws,
                "upgrade_required",
                "Cloud chat requires a paid plan. Upgrade or add an "
                "AI key to ~/.digi-setu/.env to keep using BYOK.",
            )
        else:
            await _send_bridge_error(
                local_ws,
                "relay_unreachable",
                f"Cloud relay rejected the connection (HTTP {code}). "
                "Try again, or add an AI key to ~/.digi-setu/.env.",
            )
        return
    except (OSError, asyncio.TimeoutError) as exc:
        await _send_bridge_error(
            local_ws,
            "relay_unreachable",
            f"Couldn't reach {relay_url}: {exc}. Check your internet, "
            "or add an AI key to ~/.digi-setu/.env to use BYOK.",
        )
        return
    except Exception as exc:  # noqa: BLE001 — defensive last resort
        await _send_bridge_error(
            local_ws,
            "relay_error",
            f"Unexpected relay error: {exc}",
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
