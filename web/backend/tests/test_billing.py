"""Cost-math regression tests.

Run with:
    cd web/backend && source .venv/bin/activate && pytest tests/

Covers the two paths chat_ws.py walks every prompt:

  1. estimate_prompt_cost — computes total USD from a usage payload + model
     id (used for both parent assistant turns AND sub-LLM tool calls).
  2. extract_sub_llm_usage / usage_token_total — pull a sub-LLM usage
     payload out of a tool_execution_end event and sum its token classes.

These tests exist because the billing path is not exercised by any
integration test today and the recent Gemini cache-double-count fix
showed how easy it is to drift here. If your edit affects either of
these helpers and a test below stops passing, that's the test's job —
don't update the assertion to match the new behaviour without thinking.
"""

from __future__ import annotations

import pytest

from services.billing import (
    SUB_LLM_TOOLS,
    estimate_prompt_cost,
    extract_sub_llm_usage,
    usage_token_total,
)
from services.models_registry import get_model


# ── estimate_prompt_cost ────────────────────────────────────────────────────

def test_zero_usage_returns_zero_total():
    """Empty usage shouldn't bill the user — defensive against tools that
    fail before invoking their LLM and still emit a tool_execution_end."""
    cost = estimate_prompt_cost({"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0})
    assert cost.total_usd == 0
    assert cost.llm_usd == 0


def test_haiku_pricing_matches_per_class_rates():
    """Per-class rates from models_registry should be applied independently.
    Using Haiku 4.5 because it's the search_docs default and has all four
    rates non-zero, so this catches drift in any single rate.

    Expected (per Mtok): input=$1, output=$5, cache_read=$0.10, cache_write=$1.25
    """
    haiku = get_model("claude-haiku-4-5")
    assert haiku is not None, "claude-haiku-4-5 missing from models_registry"
    usage = {"input": 10_000, "output": 1_000, "cacheRead": 50_000, "cacheWrite": 0}
    expected_llm = (
        10_000 * 1.0 / 1_000_000        # input
        + 1_000 * 5.0 / 1_000_000        # output
        + 50_000 * 0.10 / 1_000_000      # cache_read
        + 0 * 1.25 / 1_000_000           # cache_write
    )
    cost = estimate_prompt_cost(usage, model_id="claude-haiku-4-5")
    assert cost.llm_usd == pytest.approx(expected_llm, rel=1e-9)
    # total = (llm + vm) * markup; vm=0 here because wall_seconds=0
    # markup is configured via BILLING_INFRA_MARKUP env (default 1.5)
    assert cost.total_usd >= cost.llm_usd  # markup is always ≥ 1


def test_pi_provided_total_short_circuits_recompute():
    """When pi-ai already populated usage.cost.total (which it does for
    every assistant message), we trust that as the LLM cost — saves us a
    source of drift if pi's price table moves before ours does."""
    usage = {
        "input": 999_999,  # absurd, would dominate cost if recomputed
        "output": 999_999,
        "cacheRead": 0,
        "cacheWrite": 0,
        "cost": {"total": 0.42},
    }
    cost = estimate_prompt_cost(usage, model_id="claude-haiku-4-5")
    # llm portion is exactly the pi-provided value, regardless of token counts
    assert cost.llm_usd == pytest.approx(0.42, rel=1e-9)


def test_unknown_model_falls_back_to_default():
    """If a sub-LLM tool reports a model id we don't have in the registry
    (e.g. Gemini bumped a preview suffix overnight), don't crash — fall
    back to the default model's rates so we still bill SOMETHING."""
    cost = estimate_prompt_cost(
        {"input": 1_000, "output": 1_000, "cacheRead": 0, "cacheWrite": 0},
        model_id="gemini-99.9-mythical-vapour-edition",
    )
    assert cost.llm_usd > 0


def test_vm_amortisation_kicks_in_with_wall_seconds():
    """Long wall-clock turns should bill VM time on top of LLM cost."""
    short = estimate_prompt_cost(
        {"input": 100, "output": 100, "cacheRead": 0, "cacheWrite": 0},
        model_id="claude-haiku-4-5",
        wall_seconds=0.0,
    )
    long_ = estimate_prompt_cost(
        {"input": 100, "output": 100, "cacheRead": 0, "cacheWrite": 0},
        model_id="claude-haiku-4-5",
        wall_seconds=3600.0,
    )
    assert long_.vm_usd > short.vm_usd
    assert long_.total_usd > short.total_usd


# ── usage_token_total ──────────────────────────────────────────────────────

def test_usage_token_total_sums_all_four_classes():
    assert usage_token_total({"input": 100, "output": 50, "cacheRead": 30, "cacheWrite": 20}) == 200


def test_usage_token_total_handles_missing_fields_and_strings():
    assert usage_token_total({}) == 0
    # Defensive: pi sometimes ships strings for tokens (rare; older models)
    assert usage_token_total({"input": "100", "output": 50}) == 150


# ── extract_sub_llm_usage ──────────────────────────────────────────────────

def _evt(tool: str = "search_docs", usage: dict | None = None, **overrides) -> dict:
    """Build a synthetic tool_execution_end event the way pi RPC ships it."""
    base = {
        "type": "tool_execution_end",
        "toolCallId": "call_test",
        "toolName": tool,
        "isError": False,
        "result": {
            "content": [{"type": "text", "text": "stub"}],
            "details": {"ok": True, "usage": usage} if usage else {"ok": True},
        },
    }
    base.update(overrides)
    return base


def test_extract_returns_usage_for_known_tool():
    usage = {"input": 200, "output": 800, "cacheRead": 0, "cacheWrite": 0, "model": "claude-haiku-4-5"}
    out = extract_sub_llm_usage(_evt(tool="search_docs", usage=usage))
    assert out == usage


def test_extract_works_for_all_known_sub_llm_tools():
    """Catches regressions where someone edits SUB_LLM_TOOLS but forgets a tool."""
    for tool in ("search_docs", "web_search"):
        usage = {"input": 1, "output": 1, "cacheRead": 0, "cacheWrite": 0, "model": "x"}
        out = extract_sub_llm_usage(_evt(tool=tool, usage=usage))
        assert out is not None, f"failed for {tool}"
        assert out["model"] == "x"


def test_extract_ignores_unknown_tool():
    """A future tool that nests `usage` in details for some other reason
    (telemetry, logging) shouldn't accidentally bill the user."""
    usage = {"input": 999, "output": 999, "cacheRead": 0, "cacheWrite": 0, "model": "x"}
    assert extract_sub_llm_usage(_evt(tool="bash", usage=usage)) is None
    assert extract_sub_llm_usage(_evt(tool="read", usage=usage)) is None


def test_extract_returns_none_when_usage_missing():
    """Tools may legitimately fail before invoking their LLM (eg. invalid
    package param). Those shouldn't trigger a charge."""
    assert extract_sub_llm_usage(_evt(tool="search_docs")) is None


def test_extract_returns_none_for_non_terminal_events():
    """Only tool_execution_end / tool_result count — never *_start, message_*, etc."""
    e = _evt(tool="search_docs", usage={"input": 100, "model": "x"})
    e["type"] = "tool_execution_start"
    assert extract_sub_llm_usage(e) is None


def test_extract_returns_none_for_malformed_result():
    """Defensive against pi shipping an unexpected shape."""
    bad_result = _evt(tool="search_docs")
    bad_result["result"] = "string-not-dict"
    assert extract_sub_llm_usage(bad_result) is None

    bad_details = _evt(tool="search_docs")
    bad_details["result"]["details"] = "string-not-dict"
    assert extract_sub_llm_usage(bad_details) is None


def test_sub_llm_tools_set_is_the_canonical_allow_list():
    """Documents the contract — if you add a sub-LLM tool to extensions/typst-tools.ts
    you must add it here too. This test exists to make that requirement explicit."""
    assert "search_docs" in SUB_LLM_TOOLS
    assert "web_search" in SUB_LLM_TOOLS


# ── End-to-end: extract → token total → cost ───────────────────────────────

def test_full_search_docs_charge_path():
    """Walks the same path chat_ws.py:_maybe_charge_tool_sub_llm walks.

    Scenario: search_docs against the cetz corpus, second call so the
    50k-token corpus is cached. We expect a tiny ~$0.0025 LLM bill,
    NOT the $0.05 we'd get if we forgot the cache_read price.
    """
    evt = _evt(
        tool="search_docs",
        usage={
            "input": 250,           # the brief
            "output": 800,          # the answer
            "cacheRead": 50_000,    # the cetz corpus
            "cacheWrite": 0,
            "model": "claude-haiku-4-5",
        },
    )
    usage = extract_sub_llm_usage(evt)
    assert usage is not None
    total = usage_token_total(usage)
    assert total == 51_050
    cost = estimate_prompt_cost(usage, model_id=usage["model"])
    expected_llm = (
        250 * 1.0 / 1_000_000        # input
        + 800 * 5.0 / 1_000_000      # output
        + 50_000 * 0.10 / 1_000_000  # cache_read — the cheap path
    )
    assert cost.llm_usd == pytest.approx(expected_llm, rel=1e-9)
    # The without-cache cost would be ~10× higher; sanity-check that explicitly:
    no_cache_cost = (250 + 50_000) * 1.0 / 1_000_000 + 800 * 5.0 / 1_000_000
    assert cost.llm_usd < no_cache_cost / 5, (
        f"expected a meaningful cache discount but got llm={cost.llm_usd} vs no_cache={no_cache_cost}"
    )
