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
from dataclasses import dataclass
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
                # Clerk's RequestState exposes `reason` (machine-readable
                # enum) and `message` (human-readable) that explain why
                # the JWT was rejected: token-expired, signature-invalid,
                # session-revoked, missing-claim, etc. Without this log
                # a 403 from /v1/ws/desktop-relay is opaque on the
                # operator side too — we can only see "auth failed"
                # which is useless for debugging stale-JWT vs revoked-
                # session vs misconfigured-Clerk-instance.
                reason = getattr(state, "reason", None) or "unknown"
                message = getattr(state, "message", None) or ""
                print(
                    f"[auth] clerk verify rejected: reason={reason!r} "
                    f"message={message!r}",
                    file=sys.stderr,
                )
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


def optional_session(request: Request) -> Optional[tuple[str, str]]:
    """
    Best-effort `(user_id, session_id)` resolver from the request's
    Clerk JWT. Returns None if the request is not authenticated.

    Used by the desktop sign-in handoff to pluck the session id (`sid`
    claim) out of the JWT the bounce page already holds. We do this
    rather than calling Clerk's admin "create session for user" API
    because that admin API is permanently locked to development
    instances — production tenants reject it with
    "request_invalid_for_environment".

    The `sid` claim is the same opaque session handle Clerk returns
    from `clerk.sessions.create()` in dev, so the desktop sidecar's
    /api/auth/desktop-refresh exchange is identical in both modes.
    """
    if not AUTH_REQUIRED:
        return (DEV_USER_ID, f"sess_dev_{DEV_USER_ID}")

    # Re-run the Clerk verifier so we get the full claims payload, not
    # just the user id. We don't cache the result — desktop-mint-handoff
    # is called once per sign-in, never on a hot path.
    try:
        from clerk_backend_api import (  # type: ignore
            authenticate_request,
            AuthenticateRequestOptions,
        )
    except ImportError:
        return None

    opts = AuthenticateRequestOptions(secret_key=CLERK_SECRET_KEY)
    try:
        state = authenticate_request(request, opts)
    except Exception:
        return None
    if not state.is_signed_in:
        return None
    payload = state.payload or {}
    uid = payload.get("sub")
    sid = payload.get("sid")
    if not (isinstance(uid, str) and uid):
        return None
    if not (isinstance(sid, str) and sid):
        return None
    return (uid, sid)


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


def _bearer_from_subprotocol(raw: str) -> Optional[str]:
    """Pull a `bearer.<jwt>` token out of a Sec-WebSocket-Protocol header
    value. Returns None if no bearer entry is present.

    The browser's `new WebSocket(url, protocols)` API can't set
    custom headers, so the desktop sidecar (which DOES open WS
    connections itself) ships its Clerk JWT here. Pattern adopted from
    the Kubernetes / Hasura desktop tooling — RFC 6455 says the value
    is a comma-separated list of tokens, each `[A-Za-z0-9._\\-+/]+`,
    which fits a JWT cleanly when prefixed.
    """
    if not raw:
        return None
    for part in raw.split(","):
        token = part.strip()
        if token.startswith("bearer."):
            jwt = token[len("bearer."):]
            if jwt:
                return jwt
    return None


class _WsRequestish:
    """
    Adapter that exposes a WebSocket as the SDK's `Requestish` protocol
    (just `.headers`), with one twist: if the upgrade carries a
    `?clerk_token=...` query param OR a `Sec-WebSocket-Protocol:
    bearer.<jwt>` entry we synthesise an `Authorization` header so the
    SDK's session-token extractor finds it.

    This sidesteps the browser limitation that custom headers can't be
    set on the `new WebSocket(...)` constructor — the only other
    cross-environment path would be cookies, which require same-origin
    + correct cookie domain in every dev/staging/prod permutation.

    The subprotocol-bearer path is what the desktop relay bridge
    (services/relay_bridge.py on the desktop side) uses to authenticate
    to /v1/ws/desktop-relay. The browser SPA still uses ?clerk_token=.
    """

    __slots__ = ("_headers",)

    def __init__(self, ws: WebSocket) -> None:
        merged = dict(ws.headers)
        # Header keys are case-insensitive but starlette preserves
        # whatever the client sent. Normalise once.
        existing = {k.lower() for k in merged.keys()}
        if "authorization" not in existing:
            token = ws.query_params.get("clerk_token", "")
            if not token:
                # Sec-WebSocket-Protocol carries comma-separated tokens.
                # Fall through if nothing usable is in there.
                proto = merged.get("sec-websocket-protocol") or merged.get(
                    "Sec-WebSocket-Protocol", ""
                )
                token = _bearer_from_subprotocol(proto) or ""
            if token:
                merged["Authorization"] = f"Bearer {token}"
        self._headers = merged

    @property
    def headers(self):
        return self._headers


def negotiated_subprotocol(ws: WebSocket) -> Optional[str]:
    """Return the subprotocol value to echo back in `ws.accept()`.

    Per RFC 6455, if the client offers any subprotocols the server MUST
    echo one (or close the handshake). Browsers will reject the upgrade
    otherwise. We pick the first `bearer.<jwt>` entry verbatim so the
    handshake completes — the server doesn't actually use this for
    application logic (we already extracted the JWT in `_WsRequestish`).
    """
    raw = ws.headers.get("sec-websocket-protocol", "")
    if not raw:
        return None
    for part in raw.split(","):
        token = part.strip()
        if token.startswith("bearer."):
            return token
    # Some clients send a plain protocol token; echo the first one so
    # we don't break the handshake.
    first = raw.split(",", 1)[0].strip()
    return first or None


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


# ── relay-principal (LLM relay only) ──────────────────────────────────
#
# The LLM relay (routes/llm_relay.py) is the cloud-facing edge of the
# desktop "local pi, cloud auth" path: a desktop laptop spawns
# pi-coding-agent in-process so file ops happen on the user's disk, but
# every Anthropic / Vertex call gets re-routed through api.digi-setu.com
# so we never ship Application Default Credentials to the laptop.
#
# That edge needs a leaner auth contract than the SPA's `require_user`:
#   - bearer-only (no cookies — the desktop pi-proxy talks pure HTTP)
#   - returns plan + admin in one shot so the relay can fan out to
#     plan-gating and budget checks without re-querying Clerk
#   - returns the JWT's `jti` so we can later add a replay cache without
#     rewriting the dependency
#
# We keep the old verifier untouched — `require_user` is still the
# right tool for cookie-bearing SPA traffic, and `optional_user` for
# the rate-limit hook on /api/usage. This is just a sibling.

@dataclass(frozen=True)
class RelayPrincipal:
    """Resolved identity for one /v1/relay/* call.

    `plan` is materialised here (not lazy-looked-up later) so a
    constant-time `principal.plan` access in the relay's hot loop never
    touches the SQLite billing DB more than once. `admin` short-circuits
    plan-gating + budget checks for operators.
    """

    user_id: str
    plan: str
    admin: bool
    jti: Optional[str]
    exp: Optional[int]


def _bearer_from_request(request: Request) -> Optional[str]:
    """Extract the JWT from `Authorization: Bearer <token>`.

    The relay deliberately ignores cookies — it's called from the
    desktop pi-proxy (services/relay_bridge.py on the desktop side),
    which is just an HTTP forwarder and has no browser context.
    Cookie-only requests must go through the SPA path (`require_user`).
    """
    raw = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if not raw:
        return None
    # Tolerate `Bearer  <jwt>` (extra space) and `bearer <jwt>` (lowercase).
    parts = raw.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def _verify_clerk_payload(request: Request) -> Optional[dict]:
    """Run Clerk's `authenticate_request` and return the full claims
    payload, or None if the JWT is missing / invalid / expired.

    Lifted from `_get_verifier` and `optional_session` — this returns
    the WHOLE payload (not just `sub`) because the relay needs `jti`
    + `exp` for future replay caching.
    """
    try:
        from clerk_backend_api import (  # type: ignore
            authenticate_request,
            AuthenticateRequestOptions,
        )
    except ImportError:
        return None

    opts = AuthenticateRequestOptions(secret_key=CLERK_SECRET_KEY)
    try:
        state = authenticate_request(request, opts)
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[auth.relay] clerk verify raised: {exc}", file=sys.stderr)
        return None
    if not state.is_signed_in:
        reason = getattr(state, "reason", None) or "unknown"
        print(
            f"[auth.relay] clerk verify rejected: reason={reason!r}",
            file=sys.stderr,
        )
        return None
    payload = state.payload or {}
    return dict(payload) if isinstance(payload, dict) else None


def verify_relay_jwt(request: Request) -> RelayPrincipal:
    """FastAPI dependency for /v1/relay/* endpoints.

    Verifies the bearer JWT, materialises the user's plan + admin flag,
    and returns the structured `RelayPrincipal`. Raises 401 on missing
    / invalid / expired tokens.

    Use as:
        @router.post("/v1/relay/anthropic/...")
        async def fwd(principal: RelayPrincipal = Depends(verify_relay_jwt)):
            ...

    Notes:
      * `_bearer_from_request` is only used in dev mode for the empty-
        bearer fast-fail. In prod we still let `_verify_clerk_payload`
        do the full extraction (Clerk's SDK accepts both bearer and
        cookie shapes; we want bearer-only here, so we pre-check).
      * In dev (`AUTH_REQUIRED=False`) we synthesise a permissive
        principal with the dev plan default — exactly mirrors the
        existing dev-loop short-circuit in `optional_user`.
    """
    if not AUTH_REQUIRED:
        from services.billing import CreditLedger  # local import (cycle)

        plan = CreditLedger.instance().get_plan_id(DEV_USER_ID)
        return RelayPrincipal(
            user_id=DEV_USER_ID,
            plan=plan,
            admin=True,
            jti=None,
            exp=None,
        )

    if _bearer_from_request(request) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": 'Bearer realm="relay"'},
        )

    payload = _verify_clerk_payload(request)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired session",
            headers={"WWW-Authenticate": 'Bearer realm="relay"'},
        )

    sub = payload.get("sub")
    if not (isinstance(sub, str) and sub):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing subject claim",
        )

    jti = payload.get("jti") if isinstance(payload.get("jti"), str) else None
    exp = payload.get("exp") if isinstance(payload.get("exp"), (int, float)) else None

    # Resolve plan via the billing ledger (Stripe webhook is its source
    # of truth). Admins are forced to enterprise here so the relay's
    # plan-gating + budget checks treat them identically to a paying
    # power user — same code path, just unconstrained.
    admin = is_admin_user(sub)
    if admin:
        plan = "enterprise"
    else:
        from services.billing import CreditLedger  # local import (cycle)

        plan = CreditLedger.instance().get_plan_id(sub)

    return RelayPrincipal(
        user_id=sub,
        plan=plan,
        admin=admin,
        jti=jti,
        exp=int(exp) if exp is not None else None,
    )
