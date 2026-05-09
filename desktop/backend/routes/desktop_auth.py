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
     digi-setu://auth/callback?token=<ticket>&state=<csrf>`. The
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

import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import AUTH_REQUIRED, CLERK_SECRET_KEY, DEPLOY_MODE


# ── Persistent SSO storage ─────────────────────────────────────────
# The Rust shell ALSO writes / reads this file via secure_storage.rs
# (shared layout). Path stays in sync with secure_storage.rs's
# `data_root() / SESSION_FILE`. Both use the same DIGI_SETU_HOME
# env var when set so a developer can override the data root in
# tests without touching the canonical ~/.digi-setu copy.
_SESSION_FILE_NAME = ".session_id"


def _session_file_path() -> Path:
    custom = os.environ.get("DIGI_SETU_HOME", "").strip()
    if custom:
        root = Path(custom)
    else:
        root = Path.home() / ".digi-setu"
    return root / _SESSION_FILE_NAME


def _persist_session_id(session_id: str) -> None:
    """Write the session id to ~/.digi-setu/.session_id (mode 0600).

    Best-effort: a failure here means the user has to sign in again
    next launch, which is an annoyance, not a security issue. We log
    to stderr so an operator can see why and move on. We do NOT raise
    because the caller (desktop-callback / desktop-refresh) is on the
    user-visible sign-in path and we'd rather succeed-with-warning
    than turn a Clerk-side success into a UI failure.

    Why duplicate the Rust write: the localhost-callback flow never
    reaches the SPA's storeSessionId path (the SPA only fires that on
    digi-setu:// deep-links, which prod uses for OAuth flows but not
    for the loopback sign-in pattern). Without this, the cached
    session lives in Python RAM only and dies with the sidecar at
    quit-time → user is signed-out on next launch.
    """
    try:
        path = _session_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".new")
        tmp.write_text(session_id, encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)
    except OSError as exc:
        print(
            f"[desktop_auth] persist session-id failed: {exc!r}",
            file=sys.stderr,
        )


def _load_persisted_session_id() -> Optional[str]:
    """Read the session id from disk on cold start. Symmetric with
    _persist_session_id; returns None on any IO error so the boot
    flow falls through to the not-signed-in path cleanly."""
    try:
        path = _session_file_path()
        if not path.exists():
            return None
        sid = path.read_text(encoding="utf-8").strip()
        return sid or None
    except OSError:
        return None


def _clear_persisted_session_id() -> None:
    """Wipe the on-disk session id on explicit sign-out / refresh
    failure. Safe to call when the file doesn't exist."""
    try:
        path = _session_file_path()
        if path.exists():
            path.unlink()
    except OSError as exc:
        print(
            f"[desktop_auth] clear session-id failed: {exc!r}",
            file=sys.stderr,
        )

router = APIRouter(prefix="/api/auth", tags=["desktop-auth"])

# In-memory CSRF state cache for the localhost callback flow. The
# desktop frontend POSTs the state token to `/desktop-prepare-state`
# at sign-in start; the browser's bounce-page redirect then arrives
# at `/desktop-callback?state=…&session_id=…`. We only accept states
# we recently issued AND haven't already consumed. Entries older
# than 10 minutes are evicted on every read so the dict can't grow
# unbounded if the user opens 100 browsers and never finishes any.
_PENDING_STATES: dict[str, float] = {}
_STATE_TTL_S = 600  # 10 minutes


def _evict_stale_states(now: float) -> None:
    expired = [s for s, t in _PENDING_STATES.items() if now - t > _STATE_TTL_S]
    for s in expired:
        _PENDING_STATES.pop(s, None)


class _ExchangeBody(BaseModel):
    token: str
    """One-time Clerk auth ticket from the deep-link callback."""


class _RefreshBody(BaseModel):
    session_id: str
    """
    Clerk session id (`sess_…`) the SPA pulled from OS keychain at
    boot. We use it to mint a fresh JWT via the Clerk SDK; the JWT
    is never stored client-side, only re-cached on this sidecar
    instance for the lifetime of the process.
    """


# Process-local desktop session cache. Survives sidecar restart? No —
# but the SPA holds the long-lived `session_id` in the OS keychain
# (via Tauri's `secure_store_session` IPC), so a fresh launch can
# silently re-mint the JWT via /api/auth/desktop-refresh and the
# user stays signed in for as long as Clerk keeps the session alive
# (default 30 days, configurable in the Clerk dashboard).
_desktop_session_jwt: Optional[str] = None
_desktop_session_user: Optional[str] = None
_desktop_session_id: Optional[str] = None

# How much life a cached JWT must have left before we treat it as
# "still good". Clerk JWTs default to 60s, so 10s of leeway leaves
# enough headroom for a slow round-trip through the cloud relay
# without forcing a re-mint on every single chat message.
_BEARER_REFRESH_LEEWAY_SECS = 10


# ── Cold-start rehydration ─────────────────────────────────────────
# Pull the persisted session id off disk on import so the FIRST
# /api/auth/desktop-refresh-or-equivalent call has something to
# mint a JWT from. Without this, the user has to bounce through
# the browser again every time the .app is relaunched — the
# yellow-dot symptom from the user's screenshot.
#
# We DON'T mint the JWT eagerly here (no network call on import,
# keep startup fast). The first call to _mint_fresh_bearer() will
# do that lazily. Module-level "load from disk" is the cheap part.
if DEPLOY_MODE == "desktop":
    _persisted = _load_persisted_session_id()
    if _persisted:
        _desktop_session_id = _persisted
        print(
            f"[desktop_auth] rehydrated session id from "
            f"{_session_file_path()}",
            file=sys.stderr,
        )


@router.post("/desktop-exchange")
async def desktop_exchange(payload: _ExchangeBody, request: Request) -> dict[str, Any]:
    """
    Exchange a Clerk auth ticket from the deep-link callback for a
    full session token. Stamps the result on the desktop-session
    cache so the SPA's subsequent api/client calls authenticate
    automatically.

    In dev mode we accept any token and stamp user_id="dev" so the
    dev loop works without Clerk credentials at all.

    Returns:
        ok          bool   — exchange succeeded
        user_id     str    — Clerk user id (or "dev")
        session_id  str    — Clerk session id; the SPA stores this in
                             the OS keychain so subsequent app launches
                             can call /api/auth/desktop-refresh and
                             stay signed in without bouncing through
                             the browser again.
        mode        str    — "dev" | "prod"
    """
    global _desktop_session_jwt, _desktop_session_user, _desktop_session_id

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
        _desktop_session_id = "sess_dev"
        return {
            "ok": True,
            "user_id": "dev",
            "session_id": "sess_dev",
            "mode": "dev",
        }

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
        _desktop_session_id = None    # populated by Clerk verify (sid claim)

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
            if hasattr(state, "payload"):
                if getattr(state.payload, "sub", None):
                    _desktop_session_user = state.payload.sub
                # Clerk's session JWT carries the session id in the
                # `sid` claim. We pluck it out and return it so the
                # SPA can stash it in OS keychain — that's the long-
                # lived handle for /desktop-refresh on the next launch.
                if getattr(state.payload, "sid", None):
                    _desktop_session_id = state.payload.sid
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
        "session_id": _desktop_session_id or "",
        "mode": "prod",
    }


@router.post("/desktop-refresh")
async def desktop_refresh(payload: _RefreshBody) -> dict[str, Any]:
    """
    Mint a fresh JWT from a previously-cached Clerk session id.

    The SPA calls this on every cold start: it loads the session id
    from the OS keychain (Tauri `secure_load_session` IPC) and POSTs
    it here. If the session is still alive, we cache the new JWT
    on this sidecar instance and the user is signed in without any
    browser bounce.

    If the session has been revoked (user signed out from another
    device, password changed, dashboard force-logout, 30-day idle
    expiry, …) Clerk's SDK errors out and we 401. The SPA's boot
    flow treats a 401 here as "clear keychain, route to /login" —
    same UX as a first-launch user.

    Returns:
        ok          bool
        user_id     str   — Clerk user id (or "dev" in dev mode)
        mode        str   — "dev" | "prod"
    """
    global _desktop_session_jwt, _desktop_session_user, _desktop_session_id

    if DEPLOY_MODE != "desktop":
        raise HTTPException(
            status_code=400,
            detail="desktop-refresh is only valid when PI_MODE=desktop",
        )

    session_id = (payload.session_id or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    if not AUTH_REQUIRED or not CLERK_SECRET_KEY:
        # Dev mode — accept any cached id and stamp user="dev".
        _desktop_session_jwt = "dev-token"
        _desktop_session_user = "dev"
        _desktop_session_id = session_id
        _persist_session_id(session_id)
        return {"ok": True, "user_id": "dev", "mode": "dev"}

    try:
        from clerk_backend_api import Clerk  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"clerk-backend-api not available: {exc}",
        )

    clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)
    try:
        sessions_api = getattr(clerk, "sessions", None)
        if sessions_api is None:
            raise RuntimeError("clerk.sessions API not available")

        # Step 1 — mint a short-lived JWT from the long-lived session id.
        # In SDK 5.x the canonical method is `create_token`. The previous
        # implementation tried `create_session_token` first via getattr,
        # which doesn't exist in 5.x and silently fell through.
        mint = getattr(sessions_api, "create_token", None)
        if mint is None:
            raise RuntimeError("clerk.sessions.create_token not available")
        result = mint(session_id=session_id)  # type: ignore[misc]
        token_str: Optional[str] = None
        for attr in ("jwt", "token"):
            v = getattr(result, attr, None)
            if isinstance(v, str) and v:
                token_str = v
                break
        if not token_str:
            raise RuntimeError("Clerk did not return a session token")

        # Step 2 — fetch the Session object to get the user_id.
        # The Session model from clerk-backend-api 5.x has user_id as a
        # guaranteed string field; this is the reliable source of truth.
        # The previous implementation tried `authenticate_request()` with
        # a duck-typed Request that only had `.headers`. The SDK actually
        # needs method+url+headers, so it raised silently in the bare
        # `except Exception: pass` block — leaving _desktop_session_user
        # = None. That's the root cause of the 'no sign-in / sign-out
        # button' symptom: whoami sees user=None and reports
        # signed_in=false even though sign-in succeeded.
        user_id_resolved: Optional[str] = None
        try:
            sess = sessions_api.get(session_id=session_id)
            uid = getattr(sess, "user_id", None)
            if isinstance(uid, str) and uid:
                user_id_resolved = uid
        except Exception as exc:
            # User lookup failure shouldn't fail the whole refresh — we
            # still have a valid JWT. whoami degrades gracefully.
            print(
                f"[desktop_auth] sessions.get({session_id}) failed: {exc}",
                file=sys.stderr,
            )

        _desktop_session_jwt = token_str
        _desktop_session_id = session_id
        if user_id_resolved:
            _desktop_session_user = user_id_resolved
        # Persist to disk so the NEXT cold launch can rehydrate
        # without bouncing the user through the browser again. This
        # is the localhost-callback-equivalent of the SPA's
        # storeSessionId() call (which only fires for digi-setu://
        # deep-links and so doesn't run for our loopback flow).
        _persist_session_id(session_id)
    except HTTPException:
        raise
    except Exception as exc:
        # Session revoked / expired / network blip — clear local cache
        # so the next request 401s and the SPA routes to /login. Wipe
        # the disk copy too so we don't keep retrying the dead session
        # on every relaunch.
        _desktop_session_jwt = None
        _desktop_session_user = None
        _desktop_session_id = None
        _clear_persisted_session_id()
        raise HTTPException(
            status_code=401,
            detail=f"Clerk refresh failed: {exc}",
        )
    finally:
        clerk_close = getattr(clerk, "close", None)
        if callable(clerk_close):
            clerk_close()

    return {
        "ok": True,
        "user_id": _desktop_session_user or "unknown",
        "mode": "prod",
    }


@router.post("/desktop-sign-out")
async def desktop_sign_out() -> dict[str, Any]:
    """Drop the cached desktop session so the next request 401s. The
    SPA pairs this with a `secure_delete_session` IPC call so the
    OS keychain entry is cleared too — otherwise the next cold
    start would silently re-authenticate."""
    global _desktop_session_jwt, _desktop_session_user, _desktop_session_id
    _desktop_session_jwt = None
    _desktop_session_user = None
    _desktop_session_id = None
    # Wipe the disk copy too — sign-out is the user explicitly asking
    # us to forget them on this machine.
    _clear_persisted_session_id()
    return {"ok": True}


class _PrepareStateBody(BaseModel):
    state: str
    """CSRF state token the desktop frontend just generated. We cache
    it so the matching `/desktop-callback?state=…` from the browser
    redirect can be authenticated against a value we know we
    issued."""


@router.post("/desktop-prepare-state")
async def desktop_prepare_state(payload: _PrepareStateBody) -> dict[str, Any]:
    """
    Whitelist a CSRF state token before the user starts sign-in.

    Why this exists: the desktop sign-in flow uses a localhost HTTP
    callback (`http://127.0.0.1:<sidecar_port>/api/auth/desktop-callback`)
    instead of a `digi-setu://` deep-link, because deep-links don't
    deliver to a `tauri dev` binary on macOS (no .app bundle, so
    LaunchServices has no handler to route to). Localhost works
    everywhere — the same pattern gh CLI / gcloud CLI use.

    Without state validation, any web page the user visits could
    `<a href="http://127.0.0.1:<port>/api/auth/desktop-callback?session_id=evil">`
    and sign them into the attacker's account. Pre-registering the
    state token closes that hole: only states we just issued count.

    Best-effort: a sidecar restart between sign-in start and
    callback drops pending states. The user retries; same UX as
    Clerk session expiry.
    """
    state = (payload.state or "").strip()
    if not state or len(state) < 16:
        raise HTTPException(status_code=400, detail="state is required (>= 16 chars)")
    now = time.time()
    _evict_stale_states(now)
    _PENDING_STATES[state] = now
    return {"ok": True}


@router.get("/desktop-callback", response_class=HTMLResponse)
async def desktop_callback(
    state: str = Query(...),
    session_id: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    """
    Browser redirect target after Clerk sign-in completes.

    The web bounce page (`/desktop/sign-in`) mints a Clerk session
    via `desktop-mint-handoff`, then top-level navigates here with
    `?session_id=…&state=<csrf>`. We:

      1. Verify the state matches one the desktop pre-registered
         (CSRF defence — see `/desktop-prepare-state`).
      2. Reuse the existing `desktop-refresh` logic to mint a fresh
         JWT from the session id and stamp it on this sidecar's
         in-memory cache.
      3. Return a small "you can close this tab" HTML page.

    The desktop frontend's `App.vue` window-focus listener will then
    re-fetch `/api/auth/whoami` when the user clicks back to the
    app, picking up the new session immediately. No deep-link
    plumbing involved.
    """
    state = (state or "").strip()
    session_id = (session_id or "").strip()
    err = (error or "").strip()
    now = time.time()
    _evict_stale_states(now)

    issued_at = _PENDING_STATES.pop(state, None)  # one-shot consume
    if issued_at is None:
        return HTMLResponse(
            content=_callback_html(
                title="Sign-in link expired",
                body="This sign-in link is invalid or has already been "
                "used. Please return to Digi Setu and click "
                "<em>Sign in</em> again.",
                ok=False,
            ),
            status_code=400,
        )

    if err:
        return HTMLResponse(
            content=_callback_html(
                title="Sign-in cancelled",
                body=f"The browser reported: <code>{err}</code>. Please "
                "return to Digi Setu and try again.",
                ok=False,
            ),
            status_code=400,
        )

    if not session_id:
        return HTMLResponse(
            content=_callback_html(
                title="Sign-in incomplete",
                body="The browser didn't return a session id. Please "
                "return to Digi Setu and try again.",
                ok=False,
            ),
            status_code=400,
        )

    # Reuse the existing refresh path so the JWT-mint + cache is
    # identical to what `desktop-refresh` would do via deep-link.
    try:
        await desktop_refresh(_RefreshBody(session_id=session_id))
    except HTTPException as exc:
        # Surface Clerk's reason (revoked / expired) on the in-browser
        # success page so the user knows what to retry.
        return HTMLResponse(
            content=_callback_html(
                title="Sign-in failed",
                body=f"Clerk rejected the session: {exc.detail}. Please "
                "return to Digi Setu and try again.",
                ok=False,
            ),
            status_code=exc.status_code or 400,
        )
    except Exception as exc:  # pragma: no cover — defensive
        return HTMLResponse(
            content=_callback_html(
                title="Sign-in failed",
                body=f"Unexpected error: {exc}. Please return to Digi "
                "Setu and try again.",
                ok=False,
            ),
            status_code=500,
        )

    return HTMLResponse(
        content=_callback_html(
            title="You're signed in!",
            body="You can close this tab and return to Digi Setu.",
            ok=True,
        ),
        status_code=200,
    )


def _callback_html(*, title: str, body: str, ok: bool) -> str:
    """Tiny standalone HTML page rendered after the localhost
    callback. Inlines all CSS so it works without any asset server
    and renders identically whether the desktop is dark- or
    light-mode (the page is on its own; the desktop window theme
    doesn't apply)."""
    accent = "#10b981" if ok else "#ef4444"  # emerald-500 / red-500
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Digi Setu — {title}</title>
<style>
  :root {{ color-scheme: dark light; }}
  html, body {{ height: 100%; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    background: #0a0a0a;
    color: #e5e5e5;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .card {{
    max-width: 28rem;
    width: 100%;
    background: #171717;
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 28px;
    text-align: center;
  }}
  .dot {{
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: {accent};
    margin-bottom: 14px;
  }}
  h1 {{
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 10px;
    color: #fafafa;
  }}
  p {{
    margin: 0;
    line-height: 1.5;
    color: #a3a3a3;
    font-size: 14px;
  }}
  code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    background: #262626;
    padding: 2px 6px;
    border-radius: 4px;
  }}
</style>
</head>
<body>
  <div class="card">
    <span class="dot"></span>
    <h1>{title}</h1>
    <p>{body}</p>
  </div>
</body>
</html>
"""


@router.get("/whoami")
async def whoami() -> dict[str, Any]:
    """
    Resolve the currently signed-in desktop user for the SPA's
    BrandHeader avatar / sign-out menu.

    Why this endpoint exists: the desktop frontend is intentionally
    Clerk-free (no @clerk/vue). All Clerk SDK calls live here in the
    sidecar. The SPA polls this on boot + after every sign-in /
    sign-out to refresh the avatar without ever touching Clerk's
    JS bundle.

    Response schema (always the same shape; null fields when not
    signed in):

        signed_in   bool
        user_id     str | null
        email       str | null   — primary verified email
        name        str | null   — first + last, or username, or null
        image_url   str | null   — Clerk's profile_image_url

    Dev mode (CLERK_SECRET_KEY unset): returns signed_in=True with
    user_id="dev" and the rest null. Matches the rest of the
    sidecar's "always one synthetic dev user" convention so the UI
    can render an avatar shape during local development.

    Failure modes:
      * No cached session   → signed_in=False, all fields null. NOT
                              an error — the SPA renders the "Sign in"
                              CTA.
      * Clerk API blip      → signed_in=True with whatever fields
                              we already had cached, plus the
                              user_id from the JWT. Never raises —
                              BrandHeader must render even if Clerk
                              is briefly unreachable.
    """
    if DEPLOY_MODE != "desktop":
        raise HTTPException(
            status_code=400,
            detail="whoami is only valid when PI_MODE=desktop",
        )

    if not AUTH_REQUIRED or not CLERK_SECRET_KEY:
        return {
            "signed_in": True,
            "user_id": "dev",
            "email": None,
            "name": None,
            "image_url": None,
            "mode": "dev",
        }

    if not _desktop_session_jwt:
        # No JWT cached at all → user is not signed in. Fast path.
        return {
            "signed_in": False,
            "user_id": None,
            "email": None,
            "name": None,
            "image_url": None,
            "mode": "prod",
        }

    # JWT is cached but user_id is unknown (e.g. a Clerk hiccup during
    # the post-mint sessions.get call). The SPA still needs to know the
    # user is signed in so the BrandHeader can paint the avatar — we
    # degrade gracefully and try one more sessions.get with the cached
    # session id. If that also fails we report signed_in=True with a
    # placeholder user_id so the UI doesn't bounce them back to login.
    global _desktop_session_user
    if not _desktop_session_user and _desktop_session_id:
        try:
            from clerk_backend_api import Clerk  # type: ignore
            _c = Clerk(bearer_auth=CLERK_SECRET_KEY)
            try:
                _s = _c.sessions.get(session_id=_desktop_session_id)
                _u = getattr(_s, "user_id", None)
                if isinstance(_u, str) and _u:
                    _desktop_session_user = _u
            finally:
                _close = getattr(_c, "close", None)
                if callable(_close):
                    _close()
        except Exception as _exc:
            print(
                f"[desktop_auth] whoami fallback sessions.get failed: {_exc}",
                file=sys.stderr,
            )

    user_id = _desktop_session_user or "unknown"
    email: Optional[str] = None
    name: Optional[str] = None
    image_url: Optional[str] = None

    try:
        from clerk_backend_api import Clerk  # type: ignore

        clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)
        try:
            user = clerk.users.get(user_id=user_id)
            primary_id = getattr(user, "primary_email_address_id", None)
            for e in (getattr(user, "email_addresses", None) or []):
                if getattr(e, "id", None) == primary_id:
                    addr = getattr(e, "email_address", None)
                    if isinstance(addr, str):
                        email = addr
                    break
            first = getattr(user, "first_name", None) or ""
            last = getattr(user, "last_name", None) or ""
            full = (f"{first} {last}".strip()) or None
            uname = getattr(user, "username", None)
            name = full or (uname if isinstance(uname, str) and uname else None)
            img = getattr(user, "image_url", None) or getattr(user, "profile_image_url", None)
            if isinstance(img, str) and img:
                image_url = img
        finally:
            close = getattr(clerk, "close", None)
            if callable(close):
                close()
    except Exception as exc:  # pragma: no cover — defensive
        # Clerk API blip: still signaled signed_in=True so the SPA
        # doesn't bounce the user back to /login mid-session, but
        # email/name/image stay null until the next refresh.
        print(f"[desktop_auth] whoami Clerk users.get failed: {exc}", file=sys.stderr)

    return {
        "signed_in": True,
        "user_id": user_id,
        "email": email,
        "name": name,
        "image_url": image_url,
        "mode": "prod",
    }


def _decode_jwt_exp(token: str) -> Optional[int]:
    """Pull the `exp` (unix epoch seconds) claim out of a JWT WITHOUT
    verifying the signature. We only ever use this to decide whether
    to re-mint the bearer; signature verification happens server-side
    on every actual request. Reading the payload locally is the
    standard "is this expired" check used by every OAuth client.

    Returns None if the token is malformed or has no exp claim.
    """
    if not token or token.count(".") != 2:
        return None
    try:
        import base64 as _b64
        import json as _json
        payload_b64 = token.split(".", 2)[1]
        # Pad to a multiple of 4 — JWT base64 strips trailing '='.
        padding = "=" * (-len(payload_b64) % 4)
        raw = _b64.urlsafe_b64decode(payload_b64 + padding)
        claims = _json.loads(raw)
        exp = claims.get("exp")
        return int(exp) if isinstance(exp, (int, float)) else None
    except Exception:
        return None


def _mint_fresh_bearer() -> Optional[tuple[str, Optional[str]]]:
    """Return a (jwt, user_id) tuple where the JWT has at least
    ``_BEARER_REFRESH_LEEWAY_SECS`` of life left. Re-mints from the
    cached ``_desktop_session_id`` (Clerk session) when needed.

    SSO model:
      * The Clerk SESSION lives for weeks (default 30 days). It is
        the credential we promise to keep "signed in" — we cache its
        id in the OS Keychain and re-load on every cold start.
      * The JWT is a *short-lived* (~60s) bearer derived from the
        session. Every authenticated request uses one. Re-minting
        is fast (cached HMAC at Clerk's edge, no user action).
      * If Clerk says the session is gone (revoked from another
        device, user clicked sign-out elsewhere, 30-day idle
        timeout) we clear the in-memory cache and return None.
        The caller surfaces a clean "sign in again" toast — exactly
        the UX a user expects from an idle laptop.

    This helper is deliberately blocking + synchronous: Clerk's
    create_token call typically completes in 30-80ms, much faster
    than the WebSocket handshake we're about to perform anyway,
    and keeping it sync means we don't have to thread async
    plumbing through every existing call site.
    """
    global _desktop_session_jwt, _desktop_session_user, _desktop_session_id

    if not _desktop_session_id:
        return None

    # ── Fast path: cached JWT is still fresh enough to use ─────────
    if _desktop_session_jwt:
        exp = _decode_jwt_exp(_desktop_session_jwt)
        if exp is not None:
            now = int(time.time())
            if exp - now > _BEARER_REFRESH_LEEWAY_SECS:
                return _desktop_session_jwt, _desktop_session_user

    # ── Dev-mode short circuit — no Clerk SDK round-trip ───────────
    if not AUTH_REQUIRED or not CLERK_SECRET_KEY:
        _desktop_session_jwt = "dev-token"
        _desktop_session_user = _desktop_session_user or "dev"
        return _desktop_session_jwt, _desktop_session_user

    # ── Slow path: re-mint from the long-lived session id ──────────
    try:
        from clerk_backend_api import Clerk  # type: ignore
    except ImportError as exc:
        print(
            f"[desktop_auth] mint_fresh_bearer: clerk-backend-api missing: {exc}",
            file=sys.stderr,
        )
        return None

    clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)
    try:
        sessions_api = getattr(clerk, "sessions", None)
        if sessions_api is None:
            return None
        mint = getattr(sessions_api, "create_token", None)
        if mint is None:
            return None
        result = mint(session_id=_desktop_session_id)  # type: ignore[misc]
        token_str: Optional[str] = None
        for attr in ("jwt", "token"):
            v = getattr(result, attr, None)
            if isinstance(v, str) and v:
                token_str = v
                break
        if not token_str:
            return None
        _desktop_session_jwt = token_str

        # Best-effort: ensure user_id is still cached. If it's not, look
        # it up; failure here doesn't invalidate the bearer.
        if not _desktop_session_user:
            try:
                sess = sessions_api.get(session_id=_desktop_session_id)
                uid = getattr(sess, "user_id", None)
                if isinstance(uid, str) and uid:
                    _desktop_session_user = uid
            except Exception:
                pass

        return _desktop_session_jwt, _desktop_session_user
    except Exception as exc:
        # Clerk rejected the re-mint — the session is dead. Clear the
        # cache so the next call cleanly reports "not signed in" and
        # the SPA can route to /login.
        print(
            f"[desktop_auth] mint_fresh_bearer: Clerk re-mint failed "
            f"(session likely revoked): {exc}",
            file=sys.stderr,
        )
        _desktop_session_jwt = None
        _desktop_session_user = None
        # Keep _desktop_session_id so a manual refresh attempt can
        # surface the exact Clerk error to the SPA.
        return None
    finally:
        clerk_close = getattr(clerk, "close", None)
        if callable(clerk_close):
            clerk_close()


def get_cached_desktop_session() -> Optional[tuple[str, Optional[str]]]:
    """
    Internal helper — returns (jwt, user_id) if a desktop exchange
    has been completed, else None. Used by services/auth.py's
    request-time fallback so an unauthenticated SPA request can be
    "promoted" using the cached desktop session token AND by
    routes/chat_ws.py before opening the cloud relay.

    The returned JWT is guaranteed to have at least
    ``_BEARER_REFRESH_LEEWAY_SECS`` of life left — re-minted from the
    Clerk session if the cached one is stale. This is the SSO
    contract: the user signed in once weeks ago; we silently keep
    their bearer fresh for as long as Clerk says the session is
    alive.

    Returns None when:
      * No desktop sign-in has ever completed (cold launch, no
        keychain entry).
      * Clerk says the session is gone (revoked, expired, signed
        out from another device). Caller should surface "sign in
        again".
    """
    fresh = _mint_fresh_bearer()
    if fresh is not None:
        return fresh
    # Last-resort fallback for the legacy code path: if a JWT is
    # cached but we somehow couldn't re-mint (e.g. cached id is None
    # but a JWT lingered from /desktop-exchange that never recorded
    # the sid), still return what we have so the caller's auth code
    # at least gets a chance to verify it server-side.
    if _desktop_session_jwt:
        return _desktop_session_jwt, _desktop_session_user
    return None
