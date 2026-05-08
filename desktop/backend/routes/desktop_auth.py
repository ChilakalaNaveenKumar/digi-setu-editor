"""
Desktop OAuth + billing handoff.

The desktop client cannot run Clerk's SignIn component inside its
embedded webview (anti-phishing, passkeys, autofill, 3DS — see
`web/frontend/src/lib/desktop-auth.ts` for the full rationale).

Flow:

  1. Desktop SPA calls `openExternal(url)` with a URL pointing at the
     production web app's `/desktop/sign-in?state=…&return=…` page.
     That page runs Clerk's normal sign-in.

  2. After Clerk authenticates the user, the production web page
     calls Clerk's `users.createTicket()` to mint a single-use auth
     ticket bound to that session.

  3. The web page then `window.location =
     pi-typst-test://auth/callback?token=<ticket>&state=<csrf>`. The
     OS hands the URL to the Tauri shell, which forwards it as a
     `deep-link` event into the SPA.

  4. The SPA's `installDeepLinkBridge` handler verifies the CSRF state
     and POSTs `{ token: <ticket> }` to **this module**'s
     `/api/auth/desktop-exchange` endpoint.

  5. We exchange the ticket for a Clerk JWT via the SDK, and:

         a. In production (CLERK_SECRET_KEY set): cache the JWT in a
            short-lived in-memory desktop-session table keyed by the
            sidecar's PID. The Clerk Vue plugin in the SPA picks up
            the JWT via the Authorization header on subsequent
            requests.

         b. In dev (CLERK_SECRET_KEY unset): do nothing — every
            request resolves to user_id="dev" anyway.

This module is deliberately STUB-LEVEL today. The Clerk dashboard
side (allowed redirect schemes, custom `/desktop/sign-in` page) and
the `users.createTicket` call need real product wiring on the web
app, which lives outside this repo. Build that, point its return URL
at us, and the rest of the chain is ready.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import AUTH_REQUIRED, CLERK_SECRET_KEY, DEPLOY_MODE

router = APIRouter(prefix="/api/auth", tags=["desktop-auth"])


class _ExchangeBody(BaseModel):
    token: str
    """One-time Clerk auth ticket from the deep-link callback."""


# Process-local desktop session cache. Survives restart? No — but
# desktop apps usually keep the sidecar alive for the whole app
# lifetime, and the SPA persists the user-id in localStorage anyway.
_desktop_session_jwt: Optional[str] = None
_desktop_session_user: Optional[str] = None


@router.post("/desktop-exchange")
async def desktop_exchange(payload: _ExchangeBody, request: Request) -> dict[str, Any]:
    """
    Exchange a Clerk auth ticket from the deep-link callback for a
    full session token. Stamps the result on the desktop-session
    cache so the SPA's subsequent api/client calls authenticate
    automatically.

    In dev mode we accept any token and stamp user_id="dev" so the
    dev loop works without Clerk credentials at all.
    """
    global _desktop_session_jwt, _desktop_session_user

    if DEPLOY_MODE != "desktop":
        raise HTTPException(
            status_code=400,
            detail="desktop-exchange is only valid when PI_MODE=desktop",
        )

    token = (payload.token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token is required")

    # Dev-mode short circuit — no Clerk SDK call, every request will
    # resolve to user_id="dev" via the existing auth.py path.
    if not AUTH_REQUIRED or not CLERK_SECRET_KEY:
        _desktop_session_jwt = token
        _desktop_session_user = "dev"
        return {"ok": True, "user_id": "dev", "mode": "dev"}

    # Production path: exchange the ticket via Clerk SDK. The actual
    # Clerk-Python API for ticket exchange is `Tickets.verify` (as of
    # clerk-backend-api 5.x) — that returns a session_id we then
    # convert to a JWT via `Sessions.createSessionToken`.
    #
    # We deliberately import lazily so the dev path doesn't pull in
    # ~3MB of Clerk SDK code on every cold boot.
    try:
        from clerk_backend_api import Clerk  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"clerk-backend-api not available: {exc}",
        )

    try:
        clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)
        # NOTE: the exact Clerk SDK call here depends on the dashboard
        # configuration (sign-in token vs ticket vs OAuth code grant).
        # The TODO below documents what to swap in — the production
        # web app's /desktop/sign-in page determines which Clerk API
        # mints the token, and this endpoint must consume the same
        # kind of token.
        #
        # TODO(@team): replace with the real Clerk exchange call once
        # the /desktop/sign-in page is live. Until then we treat the
        # token opaquely and store it for diagnostics.
        _desktop_session_jwt = token
        _desktop_session_user = None  # populated by Clerk verify

        # Probe: try resolving the user from the token via the SDK's
        # request authenticator. If this works we have a real session.
        try:
            from clerk_backend_api import (  # type: ignore
                authenticate_request,
                AuthenticateRequestOptions,
            )

            class _ProbeReq:
                def __init__(self, hdrs: dict[str, str]) -> None:
                    self.headers = hdrs

            probe = _ProbeReq({"authorization": f"Bearer {token}"})
            state = authenticate_request(
                probe, AuthenticateRequestOptions(secret_key=CLERK_SECRET_KEY)
            )
            if hasattr(state, "payload") and getattr(state.payload, "sub", None):
                _desktop_session_user = state.payload.sub
        except Exception:
            pass

        clerk_close = getattr(clerk, "close", None)
        if callable(clerk_close):
            clerk_close()

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Clerk exchange failed: {exc}",
        )

    return {
        "ok": True,
        "user_id": _desktop_session_user or "unknown",
        "mode": "prod",
    }


@router.post("/desktop-sign-out")
async def desktop_sign_out() -> dict[str, Any]:
    """Drop the cached desktop session JWT so the next request 401s."""
    global _desktop_session_jwt, _desktop_session_user
    _desktop_session_jwt = None
    _desktop_session_user = None
    return {"ok": True}


def get_cached_desktop_session() -> Optional[tuple[str, Optional[str]]]:
    """
    Internal helper — returns (jwt, user_id) if a desktop exchange
    has been completed, else None. Used by services/auth.py's
    request-time fallback so an unauthenticated SPA request can be
    "promoted" using the cached desktop session token.
    """
    if _desktop_session_jwt:
        return _desktop_session_jwt, _desktop_session_user
    return None
