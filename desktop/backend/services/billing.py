"""
Cost calculator + plan catalogue (DESKTOP).

This is the **desktop** flavour of services/billing — a *thin client*.
The cloud's web/backend/services/billing.py owns:

    * the canonical CreditLedger (SQLite at api.digi-setu.com)
    * Stripe Checkout / Customer Portal sessions
    * Stripe webhook → plan upgrades
    * the ``can_spend`` gate enforced at chat-WS time

The desktop sidecar deliberately keeps NONE of those. Reasons:

    1. Stripe credentials must never live on a user's machine.
    2. A SQLite ledger on the user's disk is *trivially editable*;
       gating on it would let any user grant themselves Enterprise
       by deleting one file. The cloud relay enforces the only
       gate that matters — see web/backend/routes/desktop_relay.py
       and web/backend/routes/chat_ws.py:run_session_loop.
    3. Two ledgers ⇒ two sources of truth ⇒ inevitable drift.

What stays here, and why:

    * **Plan catalogue** (``_PLANS``, ``plan_for``, ``plans()``).
      Read-only metadata. Used by the model picker filter + a few
      display surfaces. Eventually we may have the cloud serve
      this so tiers can change without a desktop redeploy, but
      for now duplicating four dicts is cheaper than one more
      cloud round-trip on every fresh tab.
    * **Cost calculator** (``estimate_prompt_cost``,
      ``extract_sub_llm_usage``, ``usage_token_total``,
      ``SUB_LLM_TOOLS``). Used by chat_ws to *display* per-turn
      cost in the assistant bubble (the BYOK path tells the user
      what they spent against their own provider quota). No money
      moves; nothing here gates anything.

What was deleted vs. the cloud copy:

    * The entire ``CreditLedger`` class + SQLite schema.
    * Stripe customer / monthly-spend helpers.
    * ``can_spend`` / ``note_cost`` — replaced by:
        - cloud-relay enforcement for cloud chats
        - services/byok_usage.py for BYOK token tally (no $)
    * ``_BILLING_DB_OVERRIDE`` / ``_DB_PATH`` / ``_connect_db``.

For "what plan is the user on right now?" use
``services/plan_cache.get_plan_id`` — it proxies the cloud and
caches for 60s.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from services.models_registry import (
    DEFAULT_MODEL_ID,
    ModelSpec,
    get_model,
)


def _f_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


# ── infra cost constants (overridable via env) ────────────────────
# Used by estimate_prompt_cost so the per-turn $ shown in the BYOK
# assistant bubble at least *resembles* what the cloud would
# charge. Pure display — none of it gates anything on the desktop.
# e2-small in us-central1, on-demand: $0.0168/h.
_VM_HOURLY_USD = _f_env("BILLING_VM_HOURLY_USD", 0.0168)
_VM_USERS_AT_ONCE = max(1.0, _f_env("BILLING_VM_USERS_AT_ONCE", 10.0))
_INFRA_MARKUP = max(1.0, _f_env("BILLING_INFRA_MARKUP", 1.5))


# ── plans ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PlanSpec:
    """One subscription tier, mirrored from the cloud catalogue.

    ``stripe_price_id`` is intentionally *empty on desktop* — the
    desktop never creates Stripe sessions, so it never needs the
    id. We keep the field in the dataclass so the SPA's
    ``PlanInfo`` type stays identical between web and desktop and
    no per-platform branching is needed in the typed API client.
    """

    id: str
    label: str
    monthly_price_usd: float
    monthly_credit_usd: float
    stripe_price_id: str  # always "" on desktop
    description: str


_PLANS: dict[str, PlanSpec] = {
    "free": PlanSpec(
        id="free",
        label="Free",
        monthly_price_usd=0.0,
        # $10 of credit/month so signed-up users can actually try the
        # cloud models end-to-end (a typical Sonnet chat costs ~$0.05;
        # $10 covers ~150–200 prompts before they hit the gate). The
        # previous $2 was effectively "two short Haiku threads", which
        # didn't show off what the product can do — and forced the
        # Upgrade modal to pop after the very first conversation.
        monthly_credit_usd=_f_env("BILLING_FREE_CREDIT_USD", 10.0),
        stripe_price_id="",
        description="Try it out. Haiku + Gemini Flash models, with $10 of free monthly credit.",
    ),
    "starter": PlanSpec(
        id="starter",
        label="Starter",
        monthly_price_usd=20.0,
        monthly_credit_usd=_f_env("BILLING_STARTER_CREDIT_USD", 20.0),
        stripe_price_id="",
        description="Sonnet + Gemini Pro. $20 of usage included.",
    ),
    "pro": PlanSpec(
        id="pro",
        label="Pro",
        monthly_price_usd=100.0,
        monthly_credit_usd=_f_env("BILLING_PRO_CREDIT_USD", 200.0),
        stripe_price_id="",
        description="Adds Opus 4.7. Pay $100, spend up to $200. Best value for daily users.",
    ),
    "enterprise": PlanSpec(
        id="enterprise",
        label="Enterprise",
        monthly_price_usd=200.0,
        monthly_credit_usd=_f_env("BILLING_MAX_CREDIT_USD", 350.0),
        stripe_price_id="",
        description="Pay $200, spend up to $350. For full-time Opus / multi-hour Gemini Pro sessions.",
    ),
}


def plans() -> list[dict[str, Any]]:
    """Public catalogue used by the SPA's pricing chip + upgrade
    redirect. ``stripe_price_id`` is empty on desktop because the
    SPA never POSTs to ``/api/billing/checkout`` on this side — it
    just opens https://digi-setu.com/pricing in the system browser
    and Stripe is configured on the cloud."""
    return [
        {
            "id": p.id,
            "label": p.label,
            "monthly_price_usd": p.monthly_price_usd,
            "monthly_credit_usd": p.monthly_credit_usd,
            "stripe_price_id": p.stripe_price_id,
            "description": p.description,
        }
        for p in _PLANS.values()
    ]


def plan_for(plan_id: str) -> PlanSpec:
    """Look up by id with a hard fallback to ``free`` so display
    surfaces always have a valid spec to render. The string
    ``"byok"`` (returned by plan_cache when running on local AI
    keys with no sign-in) intentionally falls through to ``free``
    here — chargeable plan tiers don't apply, and the SPA already
    knows to render BYOK-specific copy."""
    return _PLANS.get(plan_id) or _PLANS["free"]


def known_plan_id(plan_id: str) -> bool:
    """True if ``plan_id`` is a tier we ship. Kept on desktop for
    parity with the cloud helper so SPA code that imports plan-id
    constants from a shared place still type-checks."""
    return plan_id in _PLANS


# ── per-prompt cost calculator ────────────────────────────────────
@dataclass(frozen=True)
class CostBreakdown:
    model_id: str
    llm_usd: float
    vm_usd: float
    margin_usd: float
    total_usd: float


def _llm_cost_from_tokens(model: ModelSpec, usage: dict[str, Any]) -> float:
    """Per-class token count × per-MTok price, summed. Same formula
    as pi-mono's ``calculateCost`` — keep identical so the figure
    we render in the assistant bubble matches what pi reports."""
    return (
        (int(usage.get("input") or 0) * model.cost.input / 1_000_000)
        + (int(usage.get("output") or 0) * model.cost.output / 1_000_000)
        + (int(usage.get("cacheRead") or 0) * model.cost.cache_read / 1_000_000)
        + (int(usage.get("cacheWrite") or 0) * model.cost.cache_write / 1_000_000)
    )


# Tools whose execute() bodies make their own provider call and report
# usage in result.details.usage. Without this allow-list those calls
# are free for the user and we eat the bill (on cloud) / under-display
# the spend (on desktop). Adding a new sub-LLM tool? Just surface
# ``details.usage = { input, output, cacheRead, cacheWrite, model }``
# from the tool and add its name here. See chat_ws.py /
# extensions/usage.ts for the orchestration side.
SUB_LLM_TOOLS: set[str] = {"search_docs", "web_search"}


def extract_sub_llm_usage(evt: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Pull a sub-LLM ``usage`` payload out of a
    ``tool_execution_end`` event. Returns the inner usage dict
    (with ``model`` set) if the event is from a known sub-LLM
    tool AND the tool surfaced its usage payload as designed,
    else None. Pure function; easy to unit test."""
    if evt.get("type") not in ("tool_execution_end", "tool_result"):
        return None
    tool_name = str(evt.get("toolName") or "")
    if tool_name not in SUB_LLM_TOOLS:
        return None
    result = evt.get("result")
    if not isinstance(result, dict):
        return None
    details = result.get("details")
    if not isinstance(details, dict):
        return None
    usage = details.get("usage")
    if not isinstance(usage, dict):
        return None
    return usage


def usage_token_total(usage: dict[str, Any]) -> int:
    """Sum of the four token classes — matches what
    ``estimate_prompt_cost`` multiplies by per-class rates. Used by
    the rate-limiter's ``charge_tokens()``."""
    return (
        int(usage.get("input") or 0)
        + int(usage.get("output") or 0)
        + int(usage.get("cacheRead") or 0)
        + int(usage.get("cacheWrite") or 0)
    )


def estimate_prompt_cost(
    usage: dict[str, Any],
    *,
    model_id: str = DEFAULT_MODEL_ID,
    wall_seconds: float = 0.0,
) -> CostBreakdown:
    """Compute the all-in dollar cost of a single assistant turn.

    ``usage`` mirrors pi's ``message_end.usage`` payload:
        ``{input, output, cacheRead, cacheWrite, [cost: {total, …}]}``

    If pi already produced ``cost.total`` (pi-mono populates it for
    every assistant message via models.ts:calculateCost), trust
    that as the LLM cost — no double-counting if pi's model table
    moves before ours does. Otherwise recompute from token counts.

    Returns a value-only struct; callers decide whether to
    persist, display, or ignore it. On the desktop today every
    caller just displays it in the assistant bubble.
    """
    model = get_model(model_id) or get_model(DEFAULT_MODEL_ID)

    cost_subtree = usage.get("cost") if isinstance(usage.get("cost"), dict) else {}
    pi_total = float((cost_subtree or {}).get("total") or 0)

    if pi_total > 0:
        llm = pi_total
    elif model is not None:
        llm = _llm_cost_from_tokens(model, usage)
    else:
        llm = 0.0

    vm = (_VM_HOURLY_USD * max(0.0, wall_seconds) / 3600.0) / _VM_USERS_AT_ONCE
    base = llm + vm
    total = base * _INFRA_MARKUP

    return CostBreakdown(
        model_id=model.id if model else model_id,
        llm_usd=round(llm, 6),
        vm_usd=round(vm, 6),
        margin_usd=round(total - base, 6),
        total_usd=round(total, 6),
    )
