"""
Stripe-backed billing routes.

Three endpoints:
  POST /api/billing/checkout      — create a Stripe Checkout session
                                    for the requested plan, return its
                                    hosted URL. SPA does
                                    `window.location.href = url`.
  POST /api/billing/portal        — create a Customer Portal session so
                                    the user can change/cancel their
                                    plan or update their card. Same
                                    redirect pattern as checkout.
  POST /api/billing/webhook       — Stripe → here on subscription /
                                    invoice events. Updates
                                    CreditLedger.set_plan so the next
                                    prompt sees the new tier.

When STRIPE_SECRET_KEY is unset (dev mode without a Stripe account),
all three return 503 with a clear message. The SPA then renders an
"Upgrade unavailable in this build" affordance instead of a broken
button.

USD-only for v1 — Stripe Subscriptions don't ship to India yet. Plan
to add Razorpay (or move everything to Paddle/Lemon Squeezy as MoR)
once the first non-US paying user asks for it.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from config import (
    BILLING_ENABLED,
    BILLING_RETURN_URL,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from services.auth import require_user
from services.billing import (
    CreditLedger,
    known_plan_id,
    plan_for,
    plan_for_stripe_price,
    plans,
)

router = APIRouter(tags=["billing"])


# ── lazy stripe import ────────────────────────────────────────────
# We import inside the handlers (not at module load) so a missing
# STRIPE_SECRET_KEY doesn't break unrelated routes — billing endpoints
# return 503, everything else stays up. The import is cheap once cached.
def _stripe():
    if not BILLING_ENABLED:
        raise HTTPException(status_code=503, detail="billing not configured")
    import stripe  # type: ignore

    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


class CheckoutRequest(BaseModel):
    plan_id: str          # "starter" | "pro" | "enterprise"
    return_url: Optional[str] = None     # override (e.g. for desktop deep links)


@router.post("/api/billing/checkout")
async def create_checkout(
    payload: CheckoutRequest,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Create a hosted Stripe Checkout session for the requested plan.

    Idempotency-key is the (user_id, plan_id) pair so a double-clicked
    Upgrade button doesn't create two open sessions.
    """
    plan = plan_for(payload.plan_id)
    if not plan.stripe_price_id:
        raise HTTPException(
            status_code=400,
            detail=f"plan '{plan.id}' has no Stripe price id configured",
        )

    stripe = _stripe()
    return_base = (payload.return_url or BILLING_RETURN_URL).rstrip("/")

    # If we already know this user's Stripe customer id, reuse it so
    # their billing history stays in one customer record across plan
    # switches. Otherwise let Checkout create one and we'll capture it
    # via the customer.created webhook below.
    ledger = CreditLedger.instance()
    customer_id = ledger.get_stripe_customer(user_id)

    try:
        # In subscription mode Stripe always creates a Customer
        # automatically — `customer_creation` is only valid in payment
        # mode. The customer id surfaces on `checkout.session.completed`
        # and we capture it in the webhook handler below.
        kwargs: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
            "success_url": f"{return_base}/?billing=success",
            "cancel_url": f"{return_base}/?billing=cancel",
            "client_reference_id": user_id,
            # Mirror the plan id into both the session AND the resulting
            # subscription. The webhook reads `metadata.plan_id` to know
            # which tier to flip the ledger to.
            "metadata": {"user_id": user_id, "plan_id": plan.id},
            "subscription_data": {
                "metadata": {"user_id": user_id, "plan_id": plan.id},
            },
            "allow_promotion_codes": True,
            "idempotency_key": f"checkout:{user_id}:{plan.id}",
        }
        if customer_id:
            kwargs["customer"] = customer_id
        session = stripe.checkout.Session.create(**kwargs)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"url": session.url, "session_id": session.id}


class PortalRequest(BaseModel):
    return_url: Optional[str] = None


@router.post("/api/billing/portal")
async def create_portal_session(
    payload: PortalRequest,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Send the user to Stripe's hosted Customer Portal for self-serve
    plan changes / cancellations / card updates. We don't reimplement
    that UI; Stripe's is already excellent and stays in sync with their
    billing rules in every region we sell."""
    stripe = _stripe()
    customer_id = CreditLedger.instance().get_stripe_customer(user_id)
    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="no Stripe customer on file — purchase a plan first",
        )
    return_base = (payload.return_url or BILLING_RETURN_URL).rstrip("/")
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{return_base}/?billing=portal",
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"url": session.url}


@router.post("/api/billing/webhook")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    """Stripe → us. Three event types we care about for v1:

      checkout.session.completed   — initial purchase. Capture the
                                     stripe_customer_id, set the plan.
      customer.subscription.updated — plan change (upgrade / downgrade
                                     mid-cycle). Re-derive plan from
                                     the active price id.
      customer.subscription.deleted — cancellation. Drop to "free".

    Everything else is ack-only (Stripe expects 2xx within 30 s, or
    it'll retry; an unknown event type isn't an error, just noise).
    """
    if not BILLING_ENABLED:
        raise HTTPException(status_code=503, detail="billing not configured")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="STRIPE_WEBHOOK_SECRET not set — refusing to process events",
        )

    stripe = _stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=401, detail="invalid stripe signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid payload")

    # `construct_event` returns a Stripe `Event` object, not a dict —
    # it supports attribute access (event.type, event.data.object) and
    # plain `event["..."]` indexing, but NOT `event.get(...)`. We use
    # bracket access with a tiny `_g` helper for nested optional fields.
    def _g(obj: Any, key: str, default: Any = None) -> Any:
        try:
            return obj[key] if obj is not None else default
        except (KeyError, TypeError):
            return default

    etype = event["type"]
    obj = _g(event["data"], "object", {}) or {}
    ledger = CreditLedger.instance()

    if etype == "checkout.session.completed":
        meta = _g(obj, "metadata", {}) or {}
        user_id = (
            _g(meta, "user_id", "")
            or _g(obj, "client_reference_id", "")
            or ""
        )
        plan_id = _g(meta, "plan_id", "") or ""
        customer_id = _g(obj, "customer", "") or ""
        if user_id:
            if customer_id:
                ledger.set_stripe_customer(user_id, customer_id)
            # Reject unknown plan_ids — defence against a confused or
            # malicious metadata field that could leave the ledger in
            # a "this user is on plan 'godmode'" state. The downstream
            # plan_for() falls back to Free for unknown ids so there's
            # no financial exploit, but we still don't want the
            # registry writing garbage we'll see in logs forever.
            if plan_id and not known_plan_id(plan_id):
                print(
                    f"[stripe] WARN unknown plan_id {plan_id!r} for "
                    f"{user_id} — ignoring (event {_g(event, 'id', '?')})",
                    file=sys.stderr,
                )
                plan_id = ""
            if plan_id:
                ledger.set_plan(user_id, plan_id)
                print(f"[stripe] {user_id} → plan {plan_id}", file=sys.stderr)

    elif etype == "customer.subscription.updated":
        # Extract the active price id from the subscription's items and
        # map it back to a local plan. This handles upgrades and
        # downgrades that happen mid-cycle (Stripe's "proration"
        # already adjusted the invoice; we just mirror the tier).
        items_obj = _g(obj, "items", {}) or {}
        items = _g(items_obj, "data", []) or []
        price_id = ""
        if items:
            first_price = _g(items[0], "price", {}) or {}
            price_id = _g(first_price, "id", "") or ""
        plan = plan_for_stripe_price(price_id)
        meta = _g(obj, "metadata", {}) or {}
        user_id = _g(meta, "user_id", "") or ""
        if not user_id:
            customer_id = _g(obj, "customer", "") or ""
            if customer_id:
                user_id = ledger.find_user_by_stripe_customer(customer_id) or ""
        if user_id and plan:
            ledger.set_plan(user_id, plan.id)
            print(f"[stripe] {user_id} → plan {plan.id} (sub.updated)", file=sys.stderr)

    elif etype == "customer.subscription.deleted":
        meta = _g(obj, "metadata", {}) or {}
        user_id = _g(meta, "user_id", "") or ""
        if not user_id:
            customer_id = _g(obj, "customer", "") or ""
            if customer_id:
                user_id = ledger.find_user_by_stripe_customer(customer_id) or ""
        if user_id:
            ledger.set_plan(user_id, "free")
            print(f"[stripe] {user_id} → plan free (sub.deleted)", file=sys.stderr)

    return {"received": True, "type": etype}


@router.get("/api/billing/status")
async def billing_status() -> dict[str, Any]:
    """Public health check the SPA polls before showing Upgrade
    buttons. When `enabled=false` the upgrade flow is hidden and the
    pricing page renders a "coming soon" notice instead."""
    return {
        "enabled": BILLING_ENABLED,
        "currency": "usd",
        "plans": plans(),
    }
