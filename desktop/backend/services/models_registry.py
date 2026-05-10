"""
Available models the user can pick + their published per-MTok prices.

Mirrors `pi-mono/packages/ai/src/models.generated.ts:MODELS` so anyone
already familiar with pi's model table can read this file unchanged.
We only carry the six models the SPA exposes (no need for the full
catalogue's 40+ entries) and we strip the fields pi cares about
internally (`api`, `baseUrl`, `compat`) — what matters here is:

  - the `id` we pass to `pi --model …`
  - the human-readable label for the picker
  - the `provider` (so we can also pass `pi --provider …`)
  - the per-MTok cost dict (so the cost calculator can recompute
    when pi's `usage.cost.total` is missing)
  - the plan tiers that include this model (so Free can't pick Opus)

Sources for prices (pulled May 2026, bump when providers change):
  - Anthropic:  https://docs.anthropic.com/en/docs/about-claude/pricing
  - Google API: https://ai.google.dev/gemini-api/docs/pricing
  - pi-mono package: packages/ai/src/models.generated.ts (cross-check)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelCost:
    """Per-MTok prices in USD. cacheRead/Write may be 0 for providers
    that don't expose explicit cache pricing (Gemini Flash variants)."""
    input: float
    output: float
    cache_read: float
    cache_write: float


@dataclass(frozen=True)
class ModelSpec:
    id: str                 # value passed to `pi --model`
    name: str               # label shown in the picker
    provider: str           # value passed to `pi --provider`
    pi_provider: str        # value passed to `pi --provider` (may differ if we proxy via Vertex)
    family: str             # "anthropic" | "google" — used for grouping in the UI
    cost: ModelCost
    context_window: int
    reasoning: bool         # supports extended thinking (UI hint)
    min_plan: str           # cheapest plan that may select this model
    blurb: str              # one-liner under the name in the picker
    hidden: bool = False    # True = internal sub-LLM model; cost-only, never in picker


# Plan tier ordering (cheapest → priciest). When `min_plan` of a model
# is "starter", every plan AT or ABOVE starter (i.e. starter, pro,
# enterprise) can pick that model. "free" can pick anything tagged
# "free".
_PLAN_RANK: dict[str, int] = {"free": 0, "starter": 1, "pro": 2, "enterprise": 3}


# We bill against Anthropic's published rates regardless of whether
# the request actually transits anthropic-vertex (Vertex marks up
# Anthropic models by 0% on top of Anthropic's price; GCP eats the
# margin). Same model id works for both — pi handles the routing.
_MODELS: list[ModelSpec] = [
    # ── Anthropic ────────────────────────────────────────────────
    ModelSpec(
        id="claude-haiku-4-5",
        name="Claude Haiku 4.5",
        provider="anthropic-vertex",
        pi_provider="anthropic-vertex",
        family="anthropic",
        cost=ModelCost(input=1.0, output=5.0, cache_read=0.10, cache_write=1.25),
        context_window=200_000,
        reasoning=True,
        min_plan="free",
        blurb="Fast and cheap. Good for quick edits and short tasks.",
    ),
    ModelSpec(
        id="claude-sonnet-4-6",
        name="Claude Sonnet 4.6",
        provider="anthropic-vertex",
        pi_provider="anthropic-vertex",
        family="anthropic",
        cost=ModelCost(input=3.0, output=15.0, cache_read=0.30, cache_write=3.75),
        context_window=1_000_000,
        reasoning=True,
        # Open to every plan including Free — Sonnet is the default
        # everywhere; we'd rather a Free user have a great first
        # experience than push them onto Haiku to cut a few cents
        # of compute on the trial. Free has a hard daily $-cap that
        # protects us from runaway use.
        min_plan="free",
        blurb="Default. Balanced quality + speed across most tasks.",
    ),
    ModelSpec(
        id="claude-opus-4-7",
        name="Claude Opus 4.7",
        provider="anthropic-vertex",
        pi_provider="anthropic-vertex",
        family="anthropic",
        cost=ModelCost(input=5.0, output=25.0, cache_read=0.50, cache_write=6.25),
        context_window=200_000,
        reasoning=True,
        # Free can pick Opus too; the daily-$-cap on Free is the
        # actual guardrail, not an artificial picker filter.
        min_plan="free",
        blurb="Strongest reasoning. ~5× the cost of Sonnet — pick it when you mean it.",
    ),
    # ── Google ───────────────────────────────────────────────────
    # We route Gemini through `google-vertex` (same Vertex AI project,
    # same auth) so users on Anthropic-vertex already have ADC
    # configured. Pi accepts the same model id either way.
    ModelSpec(
        id="gemini-3.1-flash-lite-preview",
        name="Gemini 3.1 Flash Lite",
        provider="google-vertex",
        pi_provider="google-vertex",
        family="google",
        cost=ModelCost(input=0.25, output=1.50, cache_read=0.025, cache_write=1.0),
        context_window=1_000_000,
        reasoning=True,
        min_plan="free",
        blurb="Cheapest option. ~12× more prompts per dollar than Sonnet.",
    ),
    ModelSpec(
        id="gemini-3-flash-preview",
        name="Gemini 3 Flash",
        provider="google-vertex",
        pi_provider="google-vertex",
        family="google",
        cost=ModelCost(input=0.50, output=3.00, cache_read=0.05, cache_write=0.0),
        context_window=1_000_000,
        reasoning=True,
        min_plan="free",
        blurb="Fast Google model. Good when you want speed over depth.",
    ),
    ModelSpec(
        id="gemini-3.1-pro-preview",
        name="Gemini 3.1 Pro",
        provider="google-vertex",
        pi_provider="google-vertex",
        family="google",
        cost=ModelCost(input=2.00, output=12.0, cache_read=0.20, cache_write=0.0),
        context_window=2_000_000,
        reasoning=True,
        min_plan="free",
        blurb="Google's strongest. 2M context window for whole-codebase tasks.",
    ),
    # ── Hidden / internal models ─────────────────────────────────
    # Used by extension tools (web_search, future sub-LLM helpers).
    # Never selectable from the SPA picker — `hidden=True` filters
    # them out — but still need a price entry so chat_ws.py can bill
    # the sub-LLM call accurately. If you wire a new internal model
    # into an extension, add its id here BEFORE going live, otherwise
    # the cost falls back to claude-sonnet-4-6's rates and you'll
    # silently mis-bill the user.
    ModelSpec(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash (web_search)",
        provider="google-vertex",
        pi_provider="google-vertex",
        family="google",
        # Vertex AI pricing as of May 2026: input $0.30, output $2.50,
        # cache_read $0.075. Source: cloud.google.com/vertex-ai/generative-ai/pricing
        cost=ModelCost(input=0.30, output=2.50, cache_read=0.075, cache_write=0.0),
        context_window=1_000_000,
        reasoning=False,
        min_plan="enterprise",  # not user-selectable; tagged for safety
        blurb="(internal) Used by web_search to drive grounded Google Search.",
        hidden=True,
    ),
]


_BY_ID: dict[str, ModelSpec] = {m.id: m for m in _MODELS}

# What we use when nothing's stored on the session yet. Sonnet is the
# right balance of quality and cost; if the user is on Free we'll
# auto-downgrade to Haiku at spawn time (see `pick_default_for_plan`).
DEFAULT_MODEL_ID = "claude-sonnet-4-6"


def list_models(plan_id: str = "enterprise") -> list[dict]:
    """Catalogue for the model picker. `plan_id` filters out models
    above the user's tier so the dropdown doesn't tease unavailable
    options. Pass "enterprise" to get everything (admin / picker preview).

    Hidden models (used internally by extensions for sub-LLM calls)
    are excluded — the picker is for parent-assistant choice only."""
    plan_rank = _PLAN_RANK.get(plan_id, 0)
    out = []
    for m in _MODELS:
        if m.hidden:
            continue
        out.append({
            "id": m.id,
            "name": m.name,
            "family": m.family,
            "context_window": m.context_window,
            "reasoning": m.reasoning,
            "min_plan": m.min_plan,
            "available": _PLAN_RANK.get(m.min_plan, 99) <= plan_rank,
            "blurb": m.blurb,
            "cost_per_mtok_input": m.cost.input,
            "cost_per_mtok_output": m.cost.output,
        })
    return out


def get_model(model_id: str) -> Optional[ModelSpec]:
    return _BY_ID.get(model_id)


def is_allowed(model_id: str, plan_id: str) -> bool:
    """True if `plan_id` is at or above the model's `min_plan`. Used to
    reject API attempts to set a model the user can't afford yet."""
    spec = _BY_ID.get(model_id)
    if not spec:
        return False
    return _PLAN_RANK.get(plan_id, 0) >= _PLAN_RANK.get(spec.min_plan, 99)


def pick_default_for_plan(plan_id: str) -> str:
    """Return the cheapest model id allowed on `plan_id`. Used at
    session-spawn time when the session record predates model selection
    or the stored model is no longer allowed (e.g. user downgraded)."""
    rank = _PLAN_RANK.get(plan_id, 0)
    if is_allowed(DEFAULT_MODEL_ID, plan_id):
        return DEFAULT_MODEL_ID
    for m in _MODELS:
        if _PLAN_RANK.get(m.min_plan, 99) <= rank:
            return m.id
    # Plan unknown / no models tagged free — fall back to Haiku, the
    # cheapest. Should never hit this in practice.
    return "claude-haiku-4-5"
