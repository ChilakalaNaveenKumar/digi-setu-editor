"""
Desktop → cloud HTTP client.

What this module IS
-------------------
A 100-line wrapper around ``urllib.request`` that lets the desktop
sidecar make authenticated GET calls to **our own cloud API at
``digi-setu.com``**. It runs **inside the desktop sidecar binary on
the user's machine** — there is no separate process, container, or
third-party proxy server involved. "cloud" in the name refers to the
*destination* (our cloud), not to anything running locally.

What this module IS NOT
-----------------------
* It is **not** a general-purpose HTTP proxy. It only talks to
  ``PI_CLOUD_API_BASE`` (i.e. ``https://digi-setu.com``).
* It is **not** a write proxy. The only desktop→cloud writes the
  user makes (Stripe Checkout, Customer Portal) are full-page
  browser redirects via ``openExternal()``, never HTTP from this
  module.
* It is **not** a separate piece of infrastructure the user needs
  to install or trust. It's just our desktop code calling our cloud
  API the same way the web SPA does (same domain, same JWT, same
  auth header).

End-to-end data path for a desktop "Activity" request:

    Desktop frontend (Vue, in Tauri webview)
         │  fetch('/api/usage')
         ▼
    Desktop sidecar (FastAPI, 127.0.0.1:<random port>)
         │  routes/usage.py
         ▼
    services/cloud_api.get_json('/api/usage')   ← THIS MODULE
         │  HTTPS + Authorization: Bearer <Clerk JWT>
         ▼
    https://digi-setu.com/api/usage (Caddy → cloud FastAPI)
         │
         ▼
    SQLite-on-VM (CreditLedger)

The desktop **never** opens a database connection to the cloud SQL
file. Every byte of cloud data goes through the cloud's own HTTP
API, with the same Clerk-verified JWT the web SPA presents.

Failure model
-------------
* Network errors and any non-2xx cloud response raise
  ``CloudApiError`` (with the upstream status when known). Callers
  convert this into the appropriate HTTPException — typically
  passing the cloud status through, except 401/403 which collapse
  into our own "session needs refresh" surface.
* Missing JWT (user not signed in / desktop_auth empty) raises
  ``CloudApiAuthError`` so callers can fall back to a BYOK-only
  response shape instead of bubbling a 401 to a UI that's perfectly
  capable of rendering "BYOK mode" instead.

Why ``urllib`` (not ``requests`` / ``httpx``): the sidecar is a
PyInstaller binary and we're allergic to extra deps that drag in
TLS bundles we'd then have to bless. ``urllib`` + the OS trust
store works on macOS and Linux without a single extra wheel. We
already use the same pattern in ``services/dotenv_watcher.py``.

This module was previously named ``cloud_proxy`` — renamed in May
2026 because "proxy" suggested a separate piece of infrastructure
the user had to trust, when in fact it's just our own desktop code
making HTTPS calls to our own cloud API.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from config import PI_CLOUD_API_BASE


# Generous on the read path — these calls are user-facing polls
# (credit chip, activity table) so a long timeout on a hung TLS
# handshake would freeze the whole UI. Aggressive enough that an
# offline laptop returns a clean error within a few seconds.
_DEFAULT_TIMEOUT_SECS = 6.0


class CloudApiError(Exception):
    """Generic upstream failure. ``status`` is the HTTP code if the
    cloud answered (None on connection-level errors)."""

    def __init__(self, message: str, *, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


class CloudApiAuthError(CloudApiError):
    """Raised when we don't have a desktop JWT to forward at all.
    Callers should branch into a BYOK-only / signed-out response
    rather than turning this into a 401 — a signed-out desktop
    user is a normal state, not an error."""


def _bearer_token() -> str:
    """Return the Clerk JWT the desktop has cached for this user.

    Implemented as a function (not import-time read) so a sign-in
    that lands AFTER the sidecar booted still works on the very next
    proxied request. Importing inside avoids the circular
    desktop_auth → routes/usage → cloud_api → desktop_auth chain.

    NOTE on the return shape: ``get_cached_desktop_session()`` returns
    a ``tuple[str, Optional[str]]`` of ``(jwt, user_id)`` — NOT a
    dict. An earlier version of this module assumed a dict shape and
    crashed with ``AttributeError: 'tuple' object has no attribute
    'get'`` on every signed-in chat connect, which the WS bridge
    surfaced to the UI as a generic "websocket error". Don't reshape
    the return value here without updating both callers.
    """
    from routes.desktop_auth import get_cached_desktop_session

    sess = get_cached_desktop_session()
    if sess is None:
        raise CloudApiAuthError("no cached desktop session")
    bearer, _user_id = sess
    if not bearer:
        raise CloudApiAuthError("cached desktop session has no bearer")
    return bearer


_WARNED_BAD_BASE = False


def _normalised_base() -> str:
    """Return PI_CLOUD_API_BASE, auto-correcting the common
    `api.digi-setu.com` misconfig.

    The /api/* surface is only mounted on the apex digi-setu.com.
    The api subdomain serves /v1/* (the WebSocket relay) and 404s
    everything else. A build that misroutes us to the api host
    therefore turns every billing/usage/workspace request into a
    404, which surfaces in the SPA as "Something went wrong
    reaching the cloud chat service" + an offline-looking credit
    chip — extremely unobvious from the user side. Catching it
    here means even an old / stale binary keeps working after the
    server-side route layout is locked in.

    We log the rewrite ONCE (per-process) so an operator can spot
    that the binary was built with a wrong env value and fix the
    pipeline, without spamming stderr on every poll.
    """
    global _WARNED_BAD_BASE
    base = (PI_CLOUD_API_BASE or "").rstrip("/")
    if not base:
        return base
    parsed = urllib.parse.urlparse(base)
    host = (parsed.hostname or "").lower()
    if host.startswith("api."):
        apex = host[len("api."):]
        new_netloc = apex
        if parsed.port:
            new_netloc = f"{apex}:{parsed.port}"
        rewritten = parsed._replace(netloc=new_netloc).geturl().rstrip("/")
        if not _WARNED_BAD_BASE:
            print(
                f"[cloud_api] WARN: PI_CLOUD_API_BASE was {base!r} but "
                f"/api/* is only on the apex; rewriting to {rewritten!r}. "
                f"Fix the build pipeline so this auto-correct isn't needed.",
                file=sys.stderr,
            )
            _WARNED_BAD_BASE = True
        return rewritten
    return base


def _build_url(path: str, params: Optional[dict[str, Any]] = None) -> str:
    if not path.startswith("/"):
        path = "/" + path
    base = _normalised_base()
    if not params:
        return base + path
    # Drop None values so callers can pass `since=since_iso` without
    # branching when `since_iso` is None.
    pairs = [(k, str(v)) for k, v in params.items() if v is not None]
    if not pairs:
        return base + path
    return base + path + "?" + urllib.parse.urlencode(pairs, doseq=True)


def get_json(
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    timeout: float = _DEFAULT_TIMEOUT_SECS,
) -> Any:
    """GET ``{PI_CLOUD_API_BASE}{path}`` with the cached desktop JWT
    and parse the response as JSON. Returns the decoded body on 2xx,
    raises ``CloudApiError`` (or its ``CloudApiAuthError``
    subclass) otherwise.

    The function is sync on purpose — we call it from FastAPI
    handlers via ``run_in_threadpool`` (or just await wrapping),
    NOT from inside the chat WS hot loop. Keeping it sync keeps
    PyInstaller from needing aiohttp/httpx and matches the
    existing dotenv_watcher pattern in this codebase.
    """
    bearer = _bearer_token()
    url = _build_url(path, params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
            # Identifies sidecar-originated calls in cloud access
            # logs, so we can tell "desktop sidecar polled /api/usage"
            # from "browser SPA polled /api/usage". Useful for
            # diagnosing "why is desktop seeing stale credits?" later.
            "User-Agent": "digi-setu-desktop-sidecar/1.0 (cloud-api)",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return json.loads(body) if body else None
            except json.JSONDecodeError as exc:
                raise CloudApiError(
                    f"cloud returned non-JSON for {path}: {exc}",
                    status=resp.status,
                ) from exc
    except urllib.error.HTTPError as exc:
        # 401 from cloud almost always means the cached JWT expired
        # AFTER our local re-mint check (slow refresh, clock skew).
        # Surface it loudly so desktop_auth can re-mint on the next
        # call, but DON'T silently downgrade to "signed out" — that
        # would mask a real auth bug.
        body_excerpt = ""
        try:
            body_excerpt = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        print(
            f"[cloud_api] {path} → HTTP {exc.code}: {body_excerpt!r}",
            file=sys.stderr,
        )
        raise CloudApiError(
            f"cloud returned HTTP {exc.code}",
            status=exc.code,
        ) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        # Network-level failure (offline, DNS, TLS, …). Logged so the
        # operator (us) can correlate with VM uptime; the caller
        # converts this into a friendly "couldn't reach the cloud"
        # toast rather than dumping the raw exception.
        print(f"[cloud_api] {path} network error: {exc}", file=sys.stderr)
        raise CloudApiError(f"cloud unreachable: {exc}") from exc
