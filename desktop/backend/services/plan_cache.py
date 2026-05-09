"""
Plan-id cache for the desktop sidecar.

Replaces ``services.billing.CreditLedger.get_plan_id`` for everything
that just needs "what plan is this user on?" — the model picker
filter, session feature gates, BYOK-vs-cloud routing hint, etc.

Why a thin cache instead of asking the cloud on every call:
    * The plan-id is read by *every* route handler that needs to
      decide whether to hide a paid model or unlock a feature. A
      naive proxy would round-trip api.digi-setu.com on every
      ``GET /api/models`` and stall the UI.
    * Plan changes are rare (Stripe webhook → cloud DB). A 60s TTL
      means the worst-case staleness is one minute — a paid user
      who just upgraded waits at most one tab refresh before the
      paid models light up.
    * If the cloud is unreachable we keep returning the LAST KNOWN
      plan instead of downgrading to ``free``. That stops a flaky
      home Wi-Fi from kicking a Pro user back to "no Opus for you"
      every time the cloud blip drops a packet.

Security model:
    * The cloud is the *only* authority. This cache is purely for
      UX hints. The cloud relay re-checks ``can_spend`` at every
      chat-WS message, so a user whose cache lies (e.g., we said
      "pro" but they got cancelled mid-session) will still hit a
      ``quota_exceeded`` envelope when their cloud row says "free".
      Lying to the desktop's *display* of plan never grants extra
      compute; the gate is enforced server-side.

Public surface:

    get_plan_id(user_id) → str   "free" | "starter" | "pro" |
                                  "enterprise" | "byok"
    invalidate(user_id)  → None  drop cache; force next call to
                                  re-fetch from cloud.

Returns ``"byok"`` whenever the desktop is running with at least one
local AI key configured AND the user is NOT signed in to the cloud,
so the SPA can render "BYOK · Anthropic" instead of "Free" in the
credit chip without us lying about a Stripe plan we can't verify.
"""

from __future__ import annotations

import sys
import threading
import time
from typing import Optional

from config import BYOK_MODE
from services.cloud_api import (
    CloudApiAuthError,
    CloudApiError,
    get_json,
)


# How long a plan-id stays trusted before we ask the cloud again.
# Picked at the boundary of "feels live to a user who just upgraded"
# vs. "doesn't hammer the cloud with a request per route handler".
_TTL_SECS = 60.0

# How long we keep returning the last-known plan after the cloud has
# started rejecting / timing out. Capped at 10 minutes so a forever-
# offline laptop can't keep claiming Enterprise indefinitely.
_STALE_GRACE_SECS = 600.0


class _Entry:
    __slots__ = ("plan_id", "fetched_at", "stale_since")

    def __init__(self, plan_id: str, fetched_at: float) -> None:
        self.plan_id = plan_id
        self.fetched_at = fetched_at
        self.stale_since: Optional[float] = None


_cache: dict[str, _Entry] = {}
_lock = threading.Lock()


def _fetch_from_cloud(user_id: str) -> Optional[str]:
    """Hit the cloud's /api/usage and return ``credit.plan.id``.

    Returns:
        - ``str`` plan id on success
        - ``None`` if the user is NOT signed in (no cached JWT) — the
          caller will fall back to BYOK / free as appropriate. This
          is intentionally separate from a real failure so we can
          distinguish "user is offline" from "user is signed out".

    Raises:
        ``CloudApiError`` on HTTP / network failures so the caller
        can decide whether to serve a stale cached value.
    """
    try:
        body = get_json("/api/usage")
    except CloudApiAuthError:
        return None
    if not isinstance(body, dict):
        return None
    credit = body.get("credit") or {}
    plan = credit.get("plan") or {}
    plan_id = plan.get("id")
    if isinstance(plan_id, str) and plan_id:
        return plan_id
    return None


def get_plan_id(user_id: str) -> str:
    """Return the cached plan id for ``user_id``, refreshing from
    the cloud if the entry is older than ``_TTL_SECS``.

    Falls back to:
        ``"byok"`` if the desktop has BYOK keys configured AND the
        user is signed out (no JWT to ask the cloud about).
        ``"free"`` if neither cloud nor BYOK can answer.

    Never raises — display surfaces should always have a string to
    render. The cloud relay enforces the actual ``can_spend`` gate
    at chat-WS time, so a wrong-direction guess here cannot
    materially affect billing.
    """
    now = time.monotonic()
    with _lock:
        entry = _cache.get(user_id)

    if entry is not None and (now - entry.fetched_at) < _TTL_SECS:
        return entry.plan_id

    # Need a refresh. Outside the lock so two concurrent route
    # handlers don't serialise behind each other waiting on the
    # cloud round-trip.
    plan_id: Optional[str] = None
    refresh_failed = False
    try:
        plan_id = _fetch_from_cloud(user_id)
    except CloudApiError as exc:
        refresh_failed = True
        print(
            f"[plan_cache] refresh failed for {user_id!r}: {exc}",
            file=sys.stderr,
        )

    if plan_id is None and refresh_failed and entry is not None:
        # Cloud blip — keep serving the last known value as long as
        # we're inside the grace window. After that we collapse to
        # "free" so a permanently offline machine can't keep
        # masquerading as Enterprise forever.
        if (now - entry.fetched_at) < _STALE_GRACE_SECS:
            entry.stale_since = entry.stale_since or now
            return entry.plan_id

    if plan_id is None:
        # Either the user is signed out, or the cloud told us "no
        # plan on file" (hasn't checked out yet). Use BYOK if the
        # local sidecar has provider keys, else "free".
        plan_id = "byok" if BYOK_MODE else "free"

    with _lock:
        _cache[user_id] = _Entry(plan_id=plan_id, fetched_at=now)
    return plan_id


def invalidate(user_id: Optional[str] = None) -> None:
    """Drop the cache so the next ``get_plan_id`` re-fetches.

    ``user_id=None`` clears every entry — useful for tests and after
    a global event like sign-out. Per-user invalidate is for the
    rare ``billing/return`` deep-link that fires after a successful
    Stripe Checkout: we know the cloud just updated, no point
    waiting up to 60s for the TTL.
    """
    with _lock:
        if user_id is None:
            _cache.clear()
        else:
            _cache.pop(user_id, None)
