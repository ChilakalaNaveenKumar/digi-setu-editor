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

from services.auth import require_user
from services.billing import CreditLedger, plans
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
    limit: int = Query(200, ge=1, le=500),
    since: Optional[str] = Query(
        None,
        description=(
            "ISO-8601 UTC timestamp. Returns only events strictly after "
            "this time — used by the SPA to poll incrementally without "
            "re-shipping the full ring buffer on every refresh."
        ),
    ),
) -> dict[str, Any]:
    events = CreditLedger.instance().recent_events(
        user_id, limit=limit, since_iso=since
    )
    return {"events": events, "limit": limit}
