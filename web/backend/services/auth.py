"""
Clerk-backed authentication.

Two modes:

  - **Dev mode** (CLERK_SECRET_KEY unset). Every request resolves to
    the synthetic user `DEV_USER_ID = "dev"`. The dev-loop never has
    to log in; per-user filtering still works because all dev rows
    share the same owner.

  - **Prod mode** (CLERK_SECRET_KEY set). Every protected request must
    carry a Clerk session cookie or `Authorization: Bearer <token>`.
    We hand the raw HTTP request to clerk-backend-api's
    `authenticate_request`, which verifies signature + expiry locally
    using JWKS (no network round-trip per request after warmup).

Public surface:

    require_user(request)  → str   FastAPI dependency; user_id, or 401
    optional_user(request) → str|None   never raises; for rate-limit hooks
    is_open()              → bool  True iff dev mode
    user_for_websocket(ws) → str|None   parses cookies + bearer; caller
                                     must `await ws.close(code=4401)`
                                     when None.

Why a thin wrapper over the SDK and not the SDK directly:
  - Centralises the dev-mode short-circuit in one file (every route
    handler stays a one-liner).
  - clerk-backend-api's `Requestish` protocol is just `.headers`, so
    we can hand it either a starlette `Request` or `WebSocket` — but
    only this module should know that detail.
"""

from __future__ import annotations

import sys
from typing import Optional

from fastapi import HTTPException, Request, WebSocket, status

from config import (
    ADMIN_EMAILS,
    ADMIN_USER_IDS,
    AUTH_REQUIRED,
    CLERK_SECRET_KEY,
    DEV_USER_ID,
)


_clerk_verifier = None
_clerk_users_client = None

# Cache user_id → primary email forever within the process. Clerk emails
# are stable (Clerk re-issues the user record on email change with a new
# `email_addresses[0].id`, but `user_id` follows the user). Worst case
# of a stale entry: an admin is still treated as admin after they remove
# their admin email — acceptable for a dev convenience knob.
_email_by_user: dict[str, Optional[str]] = {}
_admin_by_user: dict[str, bool] = {}


def _get_verifier():
    """
    Return a callable `(requestish) -> Optional[str]` that returns the
    signed-in user's id, or None.

    Lazy-imported because clerk-backend-api is ~3 MB of generated SDK
    code we don't want to pay for in dev mode.
    """
    global _clerk_verifier
    if _clerk_verifier is None:
        from clerk_backend_api import (  # type: ignore
            authenticate_request,
            AuthenticateRequestOptions,
        )

        opts = AuthenticateRequestOptions(secret_key=CLERK_SECRET_KEY)

        def _verify(req) -> Optional[str]:
            try:
                state = authenticate_request(req, opts)
            except Exception as exc:  # pragma: no cover — defensive
                print(f"[auth] clerk verify raised: {exc}", file=sys.stderr)
                return None
            if not state.is_signed_in:
                return None
            payload = state.payload or {}
            sub = payload.get("sub")
            return sub if isinstance(sub, str) and sub else None

        _clerk_verifier = _verify
    return _clerk_verifier


def is_open() -> bool:
    """True iff auth is disabled (dev / staging-cutover mode)."""
    return not AUTH_REQUIRED


def optional_user(request: Request) -> Optional[str]:
    """
    Best-effort user_id resolver. Never raises. Returns:
      - DEV_USER_ID in dev mode
      - the verified Clerk sub in prod mode if signed in
      - None if no valid session
    """
    if not AUTH_REQUIRED:
        return DEV_USER_ID
    return _get_verifier()(request)


def require_user(request: Request) -> str:
    """
    FastAPI dependency: returns the caller's user_id or raises 401.

    Use as:
        @router.get("/api/whatever")
        async def handler(user_id: str = Depends(require_user)):
            ...
    """
    uid = optional_user(request)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not signed in",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return uid


class _WsRequestish:
    """
    Adapter that exposes a WebSocket as the SDK's `Requestish` protocol
    (just `.headers`), with one twist: if the upgrade carries a
    `?clerk_token=...` query param we synthesise an `Authorization`
    header so the SDK's session-token extractor finds it.

    This sidesteps the browser limitation that custom headers can't be
    set on the `new WebSocket(...)` constructor — the only other
    cross-environment path would be cookies, which require same-origin
    + correct cookie domain in every dev/staging/prod permutation.
    """

    __slots__ = ("_headers",)

    def __init__(self, ws: WebSocket) -> None:
        merged = dict(ws.headers)
        # `Authorization` already wins over the query param (the
        # frontend never sends both, but be explicit).
        if "authorization" not in {k.lower() for k in merged.keys()}:
            token = ws.query_params.get("clerk_token", "")
            if token:
                merged["Authorization"] = f"Bearer {token}"
        self._headers = merged

    @property
    def headers(self):
        return self._headers


async def user_for_websocket(ws: WebSocket) -> Optional[str]:
    """
    Verify a WebSocket upgrade against Clerk.

    Returns the user_id if signed in (or DEV_USER_ID in dev mode), or
    None if the handshake should be rejected. Caller is responsible
    for closing with code 4401 on None.
    """
    if not AUTH_REQUIRED:
        return DEV_USER_ID
    return _get_verifier()(_WsRequestish(ws))


def _get_users_client():
    """Lazy Clerk Users API client, used only for the admin-email
    lookup. Cached at module level so we instantiate once per process."""
    global _clerk_users_client
    if _clerk_users_client is None:
        try:
            from clerk_backend_api import Clerk  # type: ignore

            _clerk_users_client = Clerk(bearer_auth=CLERK_SECRET_KEY)
        except Exception as exc:  # pragma: no cover — defensive
            print(f"[auth] could not init Clerk Users client: {exc}", file=sys.stderr)
            _clerk_users_client = False  # sentinel: don't keep retrying
    return _clerk_users_client


def email_for_user(user_id: str) -> Optional[str]:
    """Resolve a user's primary email via Clerk, cached forever.

    Returns None when:
      - we're in open-dev mode (no Clerk SDK initialised)
      - the user has no verified email
      - the SDK call failed (logged once, not retried this process run)
    """
    if not user_id:
        return None
    if user_id in _email_by_user:
        return _email_by_user[user_id]
    if not AUTH_REQUIRED or not CLERK_SECRET_KEY:
        _email_by_user[user_id] = None
        return None
    client = _get_users_client()
    if not client:
        _email_by_user[user_id] = None
        return None
    try:
        user = client.users.get(user_id=user_id)
        primary_id = getattr(user, "primary_email_address_id", None)
        emails = getattr(user, "email_addresses", None) or []
        chosen: Optional[str] = None
        for e in emails:
            eid = getattr(e, "id", None)
            addr = getattr(e, "email_address", None)
            if eid == primary_id and isinstance(addr, str):
                chosen = addr
                break
        if chosen is None and emails:
            addr = getattr(emails[0], "email_address", None)
            if isinstance(addr, str):
                chosen = addr
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[auth] users.get({user_id}) failed: {exc}", file=sys.stderr)
        chosen = None
    _email_by_user[user_id] = chosen
    return chosen


def is_admin_user(user_id: str) -> bool:
    """True iff the user is on the admin allow-list (by id or email).

    Admin = treated as enterprise tier across the app (every model
    unlocked, no plan-based gating). Configured via ADMIN_USER_IDS and
    ADMIN_EMAILS env vars. Result is cached per-user.
    """
    if not user_id:
        return False
    cached = _admin_by_user.get(user_id)
    if cached is not None:
        return cached
    is_admin = False
    if user_id in ADMIN_USER_IDS:
        is_admin = True
    elif ADMIN_EMAILS:
        em = (email_for_user(user_id) or "").lower()
        if em and em in ADMIN_EMAILS:
            is_admin = True
    _admin_by_user[user_id] = is_admin
    if is_admin:
        print(
            f"[auth] {user_id} flagged as admin — enterprise plan unlocked",
            file=sys.stderr,
        )
    return is_admin
