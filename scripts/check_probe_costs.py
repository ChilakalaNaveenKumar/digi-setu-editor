#!/usr/bin/env python3
"""
Read the JSONL emitted by scripts/live_provider_probe.ts and run each
captured usage through web/backend/services/billing.py:estimate_prompt_cost.

Prints a table the operator can eyeball before going live:

    call                          | model              | input |out|cR  |cW   | LLM cost  | charged
    anthropic_haiku_call_1        | claude-haiku-4-5   |    21 | 70|   0|10033| $0.012912 | $0.019368
    anthropic_haiku_call_2        | claude-haiku-4-5   |    21 | 70|10033|   0| $0.001372 | $0.002058
    ...

Runs nothing live — pure post-processor. Cheap. Useful for diff'ing the
output between two runs to confirm cache savings are being captured.

Usage:
    python3 scripts/check_probe_costs.py /tmp/probe.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "web" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.billing import estimate_prompt_cost  # noqa: E402
from services.models_registry import get_model  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_probe_costs.py <probe.jsonl>", file=sys.stderr)
        return 2
    lines = [
        json.loads(line)
        for line in Path(argv[1]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    header = (
        f"{'call':<32} | {'model':<28} | {'in':>5} | {'out':>4} | "
        f"{'cR':>5} | {'cW':>5} | {'LLM cost':>10} | {'charged':>10}"
    )
    print(header)
    print("-" * len(header))

    grand_llm = 0.0
    grand_total = 0.0
    for rec in lines:
        usage = rec["usage_for_billing"]
        model_id = usage.get("model", "?")
        cost = estimate_prompt_cost(usage, model_id=model_id)
        spec = get_model(model_id)
        # Fail loudly if a model used by an extension lacks a price entry —
        # this is the silent-mis-bill scenario the user is worried about.
        marker = "" if spec else " ⚠️  unknown model — billed at default rates"
        print(
            f"{rec['call']:<32} | {model_id:<28} | "
            f"{usage.get('input', 0):>5} | {usage.get('output', 0):>4} | "
            f"{usage.get('cacheRead', 0):>5} | {usage.get('cacheWrite', 0):>5} | "
            f"${cost.llm_usd:>9.6f} | ${cost.total_usd:>9.6f}{marker}"
        )
        grand_llm += cost.llm_usd
        grand_total += cost.total_usd

    print("-" * len(header))
    print(
        f"{'GRAND TOTAL':<32} | {'':<28} | {'':>5} | {'':>4} | {'':>5} | {'':>5} | "
        f"${grand_llm:>9.6f} | ${grand_total:>9.6f}"
    )

    # Sanity check: between Haiku call 1 (cold cache) and call 2 (cache
    # hit), call 2 should be at least 5x cheaper on the LLM line.
    h1 = next((r for r in lines if r["call"] == "anthropic_haiku_call_1"), None)
    h2 = next((r for r in lines if r["call"] == "anthropic_haiku_call_2"), None)
    if h1 and h2:
        c1 = estimate_prompt_cost(h1["usage_for_billing"], model_id=h1["usage_for_billing"]["model"])
        c2 = estimate_prompt_cost(h2["usage_for_billing"], model_id=h2["usage_for_billing"]["model"])
        ratio = c1.llm_usd / c2.llm_usd if c2.llm_usd > 0 else float("inf")
        print(
            f"\nPrompt-cache savings:  cold ${c1.llm_usd:.6f} → "
            f"warm ${c2.llm_usd:.6f}   ({ratio:.1f}× cheaper on cache hit)"
        )
        if ratio < 5.0:
            print(
                "⚠️  expected at least 5× savings on a cached corpus call. "
                "Either the cache_control marker isn't sticking or the cache "
                "TTL is shorter than the second call's wait time."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
