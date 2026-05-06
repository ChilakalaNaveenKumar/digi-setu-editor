#!/usr/bin/env python3
"""
scripts/compare_models.py

Runs the four smoke prompts against TWO providers (Gemini 3.1 Pro on Vertex
and Claude Opus 4.7 on Vertex), captures wall time / turns / tool calls /
cost / pass-fail per case from rpc_driver.py output, and prints a
side-by-side table.

Usage:
  python3 scripts/compare_models.py
  python3 scripts/compare_models.py --cases 1,3,4   # skip the slow compile case
  python3 scripts/compare_models.py --timeout 300

Requires:
  - scripts/env.sh sourced (or GOOGLE_CLOUD_PROJECT / LOCATION exported)
  - Both providers configured (anthropic-vertex patch applied — see
    patches/PATCH.md)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── The four smoke cases (mirror scripts/smoke.sh) ────────────────────────
CASES = [
    {
        "id": "01_tools_loaded",
        "title": "List custom tools (instruction following, no tool calls)",
        "prompt": (
            "List the four custom Typst tools you have available, just by "
            "name, comma-separated, on one line. Do not call any of them."
        ),
        # Actual tools exposed by extensions/typst-tools.ts:
        "expect_match": r"style_guide.*search_docs.*list_fonts.*list_packages|"
                        r"search_docs.*list_fonts.*list_packages.*style_guide",
        "expect_max_tool_calls": 0,
    },
    {
        "id": "02_compile_loop",
        "title": "Compile + fix-on-error loop (tool use + iteration)",
        "prompt": (
            "Compile workspace/main.typ. Use compile_typ. If it errors, fix "
            "the source and retry. Report the result in one line."
        ),
        # Either the success word OR a sign the agent ended up writing the PDF
        "expect_match": r"compiled|succeed|success|wrote .*main\.pdf|main\.pdf.*produc",
        "expect_min_tool_calls": 1,
    },
    {
        "id": "03_search_docs",
        "title": "search_docs RAG (touying / metropolis)",
        "prompt": (
            "Use search_docs with package=touying to find the minimal "
            "boilerplate to make a 3-slide deck using the metropolis theme. "
            "Just paste the boilerplate, no commentary."
        ),
        "expect_match": r"metropolis|touying-theme|show:\s*metropolis-theme",
        "expect_min_tool_calls": 1,
    },
    {
        "id": "04_anti_halluc_fonts",
        "title": "Anti-hallucination: must call list_fonts before recommending",
        "prompt": (
            "Suggest a serif font for a thesis. Before recommending one, "
            "you MUST call list_fonts to confirm it is installed. Then say "
            "which font you picked and why."
        ),
        # Any real serif font name OR an explicit confirmation it called list_fonts
        "expect_match": r"New Computer Modern|Libertinus|Linux Libertine|EB Garamond|"
                        r"Source Serif|Crimson|Cormorant|did not find|installed",
        "expect_min_tool_calls": 1,
    },
]

# ── The two configurations under comparison ───────────────────────────────
PROVIDERS = [
    {
        "label": "Gemini 3.1 Pro",
        "env": {
            "PI_PROVIDER": "google-vertex",
            "PI_MODEL": "gemini-3.1-pro-preview-customtools",
        },
    },
    {
        "label": "Claude Opus 4.7",
        "env": {
            "PI_PROVIDER": "anthropic-vertex",
            "PI_MODEL": "claude-opus-4-7",
            "PI_VERTEX_ANTHROPIC_LOCATION": "global",
        },
    },
]


@dataclass
class Result:
    label: str
    case_id: str
    wall_s: float
    turns: int
    tool_calls: int
    cost_usd: float
    rc: int
    matched: bool
    body_excerpt: str
    log_path: str


# Patterns we extract from rpc_driver.py's pretty output
RE_COST = re.compile(r"cost=\$([0-9.]+)")
RE_MESSAGE_END = re.compile(r"← message")          # one per assistant turn
RE_TOOL_EXEC = re.compile(r"tool_execution_start|⚙ tool ")
RE_TEXT_DELTA = re.compile(r"…text:\s+(.*)")


def run_case(case: dict, provider: dict, timeout_s: float, log_dir: Path) -> Result:
    log_path = log_dir / f"{provider['env']['PI_PROVIDER']}__{case['id']}.log"

    env = os.environ.copy()
    env.update(provider["env"])
    # belt-and-suspenders: clear stray Anthropic API keys so anthropic-vertex
    # doesn't accidentally fall back to api.anthropic.com.
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_OAUTH_TOKEN"):
        env.pop(k, None)

    print(f"  · {case['id']:<22} ", end="", flush=True)
    t0 = time.monotonic()

    proc = subprocess.run(
        [sys.executable, "scripts/rpc_driver.py", "--timeout", str(int(timeout_s)), case["prompt"]],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s + 30,
    )
    wall = time.monotonic() - t0

    body = proc.stdout + "\n" + proc.stderr
    log_path.write_text(body)

    cost = sum(float(m) for m in RE_COST.findall(proc.stdout))
    turns = len(RE_MESSAGE_END.findall(proc.stdout))
    tools = len(RE_TOOL_EXEC.findall(proc.stdout))

    # Reassemble the assistant text deltas for the pass/fail regex check
    text_assembled = "".join(RE_TEXT_DELTA.findall(proc.stdout))
    matched = bool(re.search(case["expect_match"], text_assembled, re.IGNORECASE | re.DOTALL))

    excerpt = re.sub(r"\s+", " ", text_assembled)[:160]

    print(f"{wall:6.1f}s  turns={turns:<2}  tools={tools:<2}  ${cost:.4f}  "
          f"{'PASS' if matched else 'fail'}  {excerpt[:60]}")

    return Result(
        label=provider["label"],
        case_id=case["id"],
        wall_s=wall,
        turns=turns,
        tool_calls=tools,
        cost_usd=cost,
        rc=proc.returncode,
        matched=matched,
        body_excerpt=excerpt,
        log_path=str(log_path.relative_to(ROOT)),
    )


def fmt_table(results_by_case: dict[str, list[Result]]) -> str:
    """Side-by-side comparison table."""
    cases = [c for c in CASES if c["id"] in results_by_case]
    labels = [p["label"] for p in PROVIDERS]
    if not cases:
        return "(no results)"

    rows = []
    header = f"{'case':<24} | " + " | ".join(f"{lab:^36}" for lab in labels)
    sep = "-" * len(header)
    rows.append(header)
    rows.append(sep)

    for case in cases:
        sub_header = f"{case['id']:<24} | " + " | ".join(
            f"{'wall':>6} {'turns':>5} {'tools':>5} {'cost':>9} {'pass':>5}"
            for _ in labels
        )
        rows.append(sub_header)

        cells = [f"{case['title'][:24]:<24} |"]
        for lab in labels:
            r = next((x for x in results_by_case[case["id"]] if x.label == lab), None)
            if r is None:
                cells.append(" " * 36)
            else:
                cells.append(
                    f" {r.wall_s:5.1f}s "
                    f"{r.turns:5d} "
                    f"{r.tool_calls:5d} "
                    f"   ${r.cost_usd:6.4f} "
                    f"{'Y' if r.matched else 'N':>5} |"
                )
        rows.append("".join(cells))
        rows.append("")

    rows.append(sep)
    rows.append("totals")
    rows.append(sep)
    for lab in labels:
        all_for_lab = [r for c in cases for r in results_by_case[c["id"]] if r.label == lab]
        if not all_for_lab:
            continue
        wall = sum(r.wall_s for r in all_for_lab)
        turns = sum(r.turns for r in all_for_lab)
        tools = sum(r.tool_calls for r in all_for_lab)
        cost = sum(r.cost_usd for r in all_for_lab)
        passed = sum(1 for r in all_for_lab if r.matched)
        rows.append(
            f"  {lab:<22}  wall={wall:6.1f}s  turns={turns:3d}  tools={tools:3d}  "
            f"cost=${cost:.4f}  passed={passed}/{len(all_for_lab)}"
        )

    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="1,2,3,4",
                        help="comma-separated case numbers to run (default 1,2,3,4)")
    parser.add_argument("--timeout", type=float, default=300.0,
                        help="per-case timeout in seconds (default 300)")
    args = parser.parse_args()

    selected_ids = set()
    for tok in args.cases.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            idx = int(tok) - 1
            selected_ids.add(CASES[idx]["id"])
        except (ValueError, IndexError):
            print(f"warning: ignoring invalid case '{tok}'", file=sys.stderr)
    cases_to_run = [c for c in CASES if c["id"] in selected_ids]
    if not cases_to_run:
        print("no valid cases selected", file=sys.stderr)
        return 2

    log_dir = ROOT / "logs" / f"compare-{time.strftime('%Y%m%d-%H%M%S')}"
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"log dir: {log_dir.relative_to(ROOT)}")
    print(f"cases  : {[c['id'] for c in cases_to_run]}")
    print(f"timeout: {args.timeout}s per case")
    print()

    results: dict[str, list[Result]] = {c["id"]: [] for c in cases_to_run}

    for provider in PROVIDERS:
        print(f"── {provider['label']} ({provider['env']['PI_PROVIDER']}/"
              f"{provider['env']['PI_MODEL']}) ──")
        for case in cases_to_run:
            try:
                r = run_case(case, provider, args.timeout, log_dir)
            except subprocess.TimeoutExpired:
                print(f"    !! timeout after {args.timeout}s")
                r = Result(provider["label"], case["id"], args.timeout,
                           0, 0, 0.0, 124, False, "(timeout)",
                           str((log_dir / f"{provider['env']['PI_PROVIDER']}__{case['id']}.log").relative_to(ROOT)))
            results[case["id"]].append(r)
        print()

    print()
    print("════════════════════════════════════════════════════════════════════════════════")
    print(fmt_table(results))
    print()
    print(f"full logs: {log_dir.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
