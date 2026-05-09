"""
Billing redirector (desktop).

The desktop sidecar **does not handle billing**. It has no Stripe
keys, no checkout sessions, no webhook secret, no local credit
ledger. The cloud at api.digi-setu.com owns all of that — see
web/backend/routes/billing.py for the real implementation.

Why this file still exists:

    Older desktop builds and any third-party integrators that
    hard-coded ``http://127.0.0.1:<port>/api/billing/*`` will keep
    hitting these endpoints. Rather than 404 silently we return a
    stable 410 Gone with the cloud URL the SPA / curl caller should
    use instead. This makes "what happened to billing on desktop?"
    self-documenting in network logs.

    The SPA itself NEVER calls these — the new desktop frontend
    redirects to https://digi-setu.com/pricing and
    https://digi-setu.com/account/billing via openExternal()
    instead. See desktop/frontend/src/api/billing.ts.

Security:

    No secrets imported, no Stripe SDK loaded, no DB writes. This
    file is intentionally inert — if a malicious local process
    POSTs to /api/billing/checkout it gets a 410 and nothing
    moves. The cloud is the only place anything can be charged
    or refunded.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from config import PI_CLOUD_WEB_BASE

router = APIRouter(tags=["billing"])


# Where the SPA / a curious curl user should go instead. Read at
# import time because PI_CLOUD_WEB_BASE never changes after boot.
_PRICING_URL = f"{PI_CLOUD_WEB_BASE}/pricing"
_PORTAL_URL = f"{PI_CLOUD_WEB_BASE}/account/billing"


def _gone(action: str, redirect: str) -> JSONResponse:
    """Standard 410 envelope. ``action`` is what the caller wanted
    to do (``"checkout"`` / ``"portal"`` / ``"webhook"``); the SPA
    never reads it but it's useful in server logs and for human
    debuggers reading curl output."""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "error": "billing_moved_to_cloud",
            "message": (
                "The desktop sidecar no longer handles billing. "
                "Open the URL in `redirect` in your system browser; "
                "Stripe Checkout / Customer Portal run there."
            ),
            "action": action,
            "redirect": redirect,
        },
    )


@router.post("/api/billing/checkout")
async def billing_checkout_gone(_payload: dict[str, Any] | None = None) -> JSONResponse:
    """Old: created a Stripe Checkout Session locally.
    New: SPA opens ``{PI_CLOUD_WEB_BASE}/pricing`` in the system
    browser; the cloud's /api/billing/checkout creates the session
    inside the user's authenticated browser context."""
    return _gone(action="checkout", redirect=_PRICING_URL)


@router.post("/api/billing/portal")
async def billing_portal_gone(_payload: dict[str, Any] | None = None) -> JSONResponse:
    """Old: created a Stripe Customer Portal session locally.
    New: SPA opens ``{PI_CLOUD_WEB_BASE}/account/billing`` in the
    system browser; the cloud creates the portal session there."""
    return _gone(action="portal", redirect=_PORTAL_URL)


@router.post("/api/billing/webhook")
async def billing_webhook_gone() -> JSONResponse:
    """Old: ingested Stripe webhooks locally. There is **no reason**
    a Stripe webhook should ever land on a user's desktop — they
    can't even reach a customer's localhost. Returning 410 here
    just makes the dead route honest; Stripe's only configured
    webhook endpoint is the cloud's."""
    return _gone(action="webhook", redirect=f"{PI_CLOUD_WEB_BASE}/api/billing/webhook")
