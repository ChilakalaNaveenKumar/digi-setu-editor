"""
Per-user usage readouts: rate-limit budget + subscription credit.

Architectural note (read me before editing):

    Subscription credit is OWNED BY THE CLOUD. The desktop sidecar
    is a thin client. ``GET /api/usage`` and ``GET /api/usage/events``
    forward to ``digi-setu.com/api/usage`` over HTTPS — see
    services/cloud_api.py — and never consult any local SQLite ledger
    for cloud-billed activity. A user who deletes their local data
    dir gains ZERO free usage; the cloud relay re-checks
    ``can_spend`` on every chat-WS message regardless of what the
    desktop says.

    Local SQLite at ``~/.digi-setu/usage.sqlite`` (services/byok_usage)
    DOES still record BYOK token tallies — but those are *not money*,
    just a "how much have I used my own provider?" counter. The user
    pays the provider directly; deleting that file just blanks the
    Activity page's BYOK tab and harms only themselves.

Shape:

    GET /api/plans            (public)
        { "plans": [ {id, label, monthly_price_usd, monthly_credit_usd}, … ] }

    GET /api/usage            (auth required)
        { "rate_limits":   { day, tokens_used, tokens_budget, … },
          "credit":        { month, plan, spent_usd, remaining_usd, prompts },
          "source":        "cloud" | "offline_byok" | "offline_signed_out",
          "cloud_error":   <string|null> }

    GET /api/usage/events     (auth required)
        Recent per-event activity log proxied from the cloud. When
        the cloud is unreachable returns ``events: []`` plus a
        ``cloud_error`` field so the SPA can render a "couldn't
        reach the cloud — your local activity is unaffected" banner.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from config import BYOK_MODE
from services.auth import require_user
from services.billing import plan_for, plans
from services.byok_usage import recent_events as byok_recent_events
from services.byok_usage import summary as byok_summary
from services.cloud_api import (
    CloudApiAuthError,
    CloudApiError,
    get_json as cloud_get_json,
)
from services.rate_limit import RateLimiter

router = APIRouter(tags=["usage"])


def _free_credit_snapshot() -> dict[str, Any]:
    """Synthetic credit shape returned when we can't reach the cloud
    AND the user isn't BYOK (signed out + offline).

    Matches the cloud's response schema so the SPA doesn't need to
    branch. We hand it the *real* Free plan cap (e.g. $10) and a
    matching ``remaining_usd`` so the credit chip doesn't render the
    misleading red "$0 / $0" exhausted state when the cloud is just
    temporarily unreachable. The SPA additionally inspects the
    ``source`` discriminator on the parent response to know this is
    a fallback, not authoritative spend, and suppresses the
    "you've used all your credit" banner accordingly.
    """
    free = plan_for("free")
    cap = float(getattr(free, "monthly_credit_usd", 0.0) or 0.0)
    return {
        "month": "",
        "plan": {
            "id": "free",
            "label": "Free",
            "monthly_price_usd": float(getattr(free, "monthly_price_usd", 0.0) or 0.0),
            "monthly_credit_usd": cap,
            "stripe_price_id": "",
            "description": getattr(free, "description", ""),
        },
        "spent_usd": 0.0,
        "remaining_usd": cap,
        "remaining_pct": 100.0 if cap > 0 else 0.0,
        "prompts": 0,
        "monthly_cap_usd": cap,
    }


def _byok_credit_snapshot() -> dict[str, Any]:
    """Snapshot rendered when the user is offline / signed out but
    has BYOK keys configured. The credit chip needs *something*
    to display; we hand it a synthetic plan id of ``byok`` so the
    SPA can render "BYOK · You pay your provider" instead of a
    misleading "$0 / $0 left"."""
    return {
        "month": "",
        "plan": {
            "id": "byok",
            "label": "BYOK",
            "monthly_price_usd": 0.0,
            "monthly_credit_usd": 0.0,
            "stripe_price_id": "",
            "description": "Using your own AI provider keys — billed by them, not us.",
        },
        "spent_usd": 0.0,
        "remaining_usd": 0.0,
        # 100% so the chip doesn't paint itself red — BYOK has no
        # operator-side budget to exhaust. The SPA short-circuits the
        # "$X of $Y" label to "Using your own key" when plan.id=byok.
        "remaining_pct": 100.0,
        "prompts": 0,
        "monthly_cap_usd": 0.0,
    }


@router.get("/api/plans")
async def get_plans() -> dict[str, Any]:
    """Public plan catalogue. The desktop SPA uses this only for
    layout (label + monthly_price + monthly_credit); the actual
    Upgrade button opens https://digi-setu.com/pricing in the
    system browser, where Stripe does the real checkout. Kept
    public (no auth) so the Welcome screen can render prices for
    a not-signed-in user."""
    return {"plans": plans()}


@router.get("/api/usage")
async def get_usage(user_id: str = Depends(require_user)) -> dict[str, Any]:
    """Cloud-credit proxy + local rate-limit usage.

    The rate-limit budget is per-machine (a localhost throttle on
    the LOCAL chat WS, distinct from the cloud's rate limit) and
    stays computed in-process. The credit half is fetched from the
    cloud — never trusted from any local file — and cached on the
    cloud side per the user's plan TTL."""
    rate_payload = RateLimiter.instance().usage(user_id)

    try:
        cloud = cloud_get_json("/api/usage")
    except CloudApiAuthError:
        return {
            "rate_limits": rate_payload,
            "credit": _byok_credit_snapshot() if BYOK_MODE else _free_credit_snapshot(),
            "source": "offline_byok" if BYOK_MODE else "offline_signed_out",
            "cloud_error": None,
        }
    except CloudApiError as exc:
        return {
            "rate_limits": rate_payload,
            "credit": _byok_credit_snapshot() if BYOK_MODE else _free_credit_snapshot(),
            "source": "offline_byok" if BYOK_MODE else "offline_signed_out",
            "cloud_error": str(exc),
        }

    cloud_credit = (cloud or {}).get("credit") or _free_credit_snapshot()
    return {
        "rate_limits": rate_payload,
        "credit": cloud_credit,
        "source": "cloud",
        "cloud_error": None,
    }


@router.get("/api/usage/events")
async def get_usage_events(
    user_id: str = Depends(require_user),  # noqa: ARG001 — cloud uses the bearer
    limit: int = Query(100, ge=1, le=500),
    since: Optional[str] = Query(
        None,
        description=(
            "ISO-8601 UTC timestamp. Forwarded to the cloud, which "
            "returns only events strictly after this time so the "
            "Activity table can poll incrementally."
        ),
    ),
    before: Optional[str] = Query(
        None,
        description=(
            "ISO-8601 UTC timestamp. Forwarded to the cloud, which "
            "returns only events strictly BEFORE this time. Cursor "
            "for the Activity page's 'Load older' button."
        ),
    ),
) -> dict[str, Any]:
    """Cloud activity log proxy. Empty list + ``cloud_error`` when
    we can't reach the cloud; the SPA renders a quiet banner rather
    than treating that as a real "no events" state.

    `has_more` is propagated from the cloud response so the SPA's
    "Load older" button hides itself once we hit the back of the log.
    When the cloud is unreachable we conservatively report
    ``has_more=false`` — there's no point offering to fetch more pages
    we can't actually fetch."""
    params: dict[str, Any] = {"limit": limit}
    if since:
        params["since"] = since
    if before:
        params["before"] = before
    try:
        cloud = cloud_get_json("/api/usage/events", params=params)
    except CloudApiAuthError:
        return {
            "events": [],
            "limit": limit,
            "has_more": False,
            "cloud_error": None,
            "source": "offline_signed_out",
        }
    except CloudApiError as exc:
        return {
            "events": [],
            "limit": limit,
            "has_more": False,
            "cloud_error": str(exc),
            "source": "offline",
        }

    cloud = cloud or {}
    events = cloud.get("events") or []
    return {
        "events": events,
        "limit": limit,
        # Trust the cloud's signal; fall back to "len ≥ limit" if the
        # cloud is on an older build that hasn't been deployed yet.
        "has_more": bool(cloud.get("has_more", len(events) >= limit)),
        "cloud_error": None,
        "source": "cloud",
    }


@router.get("/api/usage/byok")
async def get_byok_usage(
    user_id: str = Depends(require_user),  # noqa: ARG001 — desktop is single-user; require_user gates dev-mode access only
    limit: int = Query(100, ge=1, le=500),
    since: Optional[str] = Query(None),
    before: Optional[str] = Query(
        None,
        description=(
            "ISO-8601 UTC timestamp. Returns rows strictly older than "
            "this — used by the Activity page's 'Load older' button on "
            "the BYOK table."
        ),
    ),
) -> dict[str, Any]:
    """Per-turn rows + rollup summary from the local BYOK ledger
    (SQLite at ~/.digi-setu/usage.sqlite). When called in web mode
    or in desktop without any BYOK keys, returns empty arrays so the
    Activity page can render a quiet "no local usage" state without
    branching on the deployment shape.

    No USD figures are returned — the user pays their AI provider
    directly and we don't know their actual rate.

    The `summary` block always reflects the *full* BYOK history (or
    the `since` slice if provided) — pagination only narrows the
    `events` list, not the totals, so the rollup numbers don't jump
    around as the user pages through history."""
    if not BYOK_MODE:
        return {
            "byok_active": False,
            "events": [],
            "summary": {"total": {}, "per_model": []},
            "limit": limit,
            "has_more": False,
        }
    events = byok_recent_events(limit=limit, since_iso=since, before_iso=before)
    return {
        "byok_active": True,
        "events": events,
        "summary": byok_summary(since_iso=since),
        "limit": limit,
        "has_more": len(events) >= limit,
    }
