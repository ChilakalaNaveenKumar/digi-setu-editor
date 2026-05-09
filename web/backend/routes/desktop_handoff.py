"""
Desktop sign-in handoff (web → desktop).

The Tauri desktop app cannot host Clerk's <SignIn /> component inside
its embedded webview (passkeys, anti-phishing, autofill all break).
Instead it pops the user's default browser at the production web app's
`/desktop/sign-in` page. After Clerk authenticates the user there, the
page hits THIS endpoint to grab the handoff session id that the
desktop sidecar can consume via /api/auth/desktop-refresh.

Lifecycle:

  desktop                       browser (web frontend)              this endpoint
  ────────                      ──────────────────────              ──────────────
  openExternal(...)  ───────►  /desktop/sign-in?state&return
                               (Clerk SignIn renders here)
                               user authenticates with Clerk
                               page calls ───────────────────────►  POST /api/auth/desktop-mint-handoff
                                                                    {auth: bearer JWT from Clerk}
                                                                    │
                                                                    ▼
                                                                    read sid claim from JWT
                                                                    returns: { session_id }
                               redirects to ◄──────────────────────  { session_id }
                               <return URL> (loopback callback on
                               the desktop sidecar)
                               ?session_id=...&state=...
  ◄── localhost callback
  desktop sidecar
  /api/auth/desktop-refresh
  with {session_id}
  → clerk.sessions.create_token
  → fresh JWT cached
  → frontend stores session_id
    in OS keychain

The session_id is the "stay signed in" handle: it survives sidecar
restarts because the desktop frontend keeps it in the OS keychain.
The sidecar mints a fresh JWT from it on demand via the /refresh
endpoint, no browser bounce required.

Why we read the JWT's `sid` claim instead of calling Clerk's admin
`POST /v1/sessions` to mint a fresh session:

    Clerk's "create session on behalf of a user" admin API is
    PERMANENTLY locked to development tenants (production tenants
    reject it with `request_invalid_for_environment`).

    But by the time the bounce page calls this endpoint the user
    has ALREADY signed in via Clerk's frontend SDK in the browser —
    Clerk has issued them a real, revocable, dashboard-visible
    session. The session id is right there in the JWT they're
    sending us as the bearer token, in the standard `sid` claim.
    So we just read it and hand it back. No admin call, no
    second session burned against the user's active-session limit,
    works identically in test and prod tenants.

Auth on this endpoint: standard Clerk-authenticated user via the web
backend's existing `optional_session` helper, which validates the JWT
the same way `require_user` does and additionally extracts `sid`.
If a hostile actor hits this with a stolen JWT they can read its sid
— but they could also just *use* the stolen JWT directly, so this
doesn't expand the attack surface.

CSRF protection lives on the BROWSER side (the bounce page validates
the `state` parameter on its way back into the localhost callback),
not here — this endpoint is a plain authenticated POST.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from config import AUTH_REQUIRED, CLERK_SECRET_KEY
from services.auth import optional_session

router = APIRouter(prefix="/api/auth", tags=["desktop-handoff"])


@router.post("/desktop-mint-handoff")
async def desktop_mint_handoff(request: Request) -> dict[str, Any]:
    """
    Return the handoff session id for the currently-signed-in user.

    Reads the `sid` claim from the verified Clerk JWT the bounce page
    sends as the bearer token. The desktop sidecar exchanges this id
    for a fresh JWT via /api/auth/desktop-refresh on every launch,
    using `clerk.sessions.create_token` which IS allowed on production
    tenants (and is the same call we already use for silent SSO refresh
    on subsequent app launches).

    Dev mode (no Clerk configured) returns a synthetic id so the
    end-to-end flow is testable without a real Clerk dashboard.
    """
    if not AUTH_REQUIRED or not CLERK_SECRET_KEY:
        return {"ok": True, "session_id": "sess_dev_local", "mode": "dev"}

    pair = optional_session(request)
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not signed in",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _user_id, session_id = pair
    return {"ok": True, "session_id": session_id, "mode": "prod"}
