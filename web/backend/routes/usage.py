"""
Per-user usage readouts: rate-limit budget + subscription credit.

The chat pane already shows a per-message token chip (driven by the
`message_end` event). This endpoint surfaces the *cumulative* state
the SPA needs for two things:

  1. The "credits remaining" banner in the picker / chat header.
  2. The pre-send check that grays out the send button when the user
     has hit their daily token cap or monthly dollar cap.

It also exposes the public plan catalogue so the SPA can render an
"Upgrade" button without hard-coding prices.

Shape:

    GET /api/plans            (public)
        { "plans": [ {id, label, monthly_price_usd, monthly_credit_usd}, … ] }

    GET /api/usage            (auth required)
        { "rate_limits": { day, tokens_used, tokens_budget, … },
          "credit":      { month, plan, spent_usd, remaining_usd, prompts } }

    GET /api/usage/events     (auth required)
        Recent per-event activity log — the "where did my credit go?"
        view. Each event is a single LLM call (parent chat turn or a
        sub-LLM tool call) with its model, four-class token counts,
        cost breakdown, and which session it belonged to.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from config import BYOK_MODE
from services.auth import require_user
from services.billing import CreditLedger, plans
from services.byok_usage import recent_events as byok_recent_events
from services.byok_usage import summary as byok_summary
from services.rate_limit import RateLimiter

router = APIRouter(tags=["usage"])


@router.get("/api/plans")
async def get_plans() -> dict[str, Any]:
    """Public plan catalogue. Drives the upgrade flow in the SPA;
    intentionally unauthenticated so the marketing/landing surface
    can render prices without a session."""
    return {"plans": plans()}


@router.get("/api/usage")
async def get_usage(user_id: str = Depends(require_user)) -> dict[str, Any]:
    return {
        "rate_limits": RateLimiter.instance().usage(user_id),
        "credit": CreditLedger.instance().snapshot(user_id),
    }


@router.get("/api/usage/events")
async def get_usage_events(
    user_id: str = Depends(require_user),
    limit: int = Query(100, ge=1, le=500),
    since: Optional[str] = Query(
        None,
        description=(
            "ISO-8601 UTC timestamp. Returns only events strictly after "
            "this time — used by the SPA to poll incrementally without "
            "re-shipping the full window on every refresh."
        ),
    ),
    before: Optional[str] = Query(
        None,
        description=(
            "ISO-8601 UTC timestamp. Returns only events strictly BEFORE "
            "this time — cursor used by the Activity page's 'Load older' "
            "button. Pass the timestamp of the oldest currently-rendered "
            "row to fetch the next page back in history."
        ),
    ),
) -> dict[str, Any]:
    events = CreditLedger.instance().recent_events(
        user_id, limit=limit, since_iso=since, before_iso=before
    )
    # `has_more` lets the SPA know whether the "Load older" button
    # should stay rendered or collapse — `len == limit` is a strong
    # heuristic (the only false-positive is when the table happens to
    # have exactly `limit` rows older than the cursor and zero beyond,
    # which we accept; the next click would just return an empty page
    # and the button hides itself then).
    return {
        "events": events,
        "limit": limit,
        "has_more": len(events) >= limit,
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
