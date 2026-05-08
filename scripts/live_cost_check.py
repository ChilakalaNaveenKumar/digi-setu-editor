#!/usr/bin/env python3
"""
Live cost-verification test.

Drives `pi --mode rpc` exactly the way web/backend/services/pi_session.py
does (same provider, same model, same extension), sends one prompt that
forces a `search_docs` call, then prints a side-by-side of:

  - REAL tokens reported by Vertex (Anthropic / Gemini)
  - COMPUTED cost via web/backend/services/billing.py:estimate_prompt_cost

If the two columns drift the cost calculator is wrong; we want to find
that out here, not in production after a customer complaint.

This script does NOT touch the running backend — it spawns a fresh pi
subprocess, captures its stdout, and runs the same Python helpers that
the WS bridge uses. That means a green run here proves the math AND
the integration points (extraction from event, model id lookup, etc.)
without depending on Clerk auth / a logged-in browser.

Usage
-----
    cd pi-typst-test
    source scripts/env.sh            # sets PI_PROVIDER / PI_MODEL / GOOGLE_CLOUD_*
    python3 scripts/live_cost_check.py [--prompt "..."] [--model claude-haiku-4-5]

Output
------
    [search_docs]    real: in=…  out=…  cacheR=…  cacheW=…   model=…
                     calc: $LLM   |   sub-LLM cost charged to ledger
    [message_end]    real: in=…  out=…  cacheR=…  cacheW=…   model=…
                     calc: $LLM   |   parent-turn cost charged to ledger
    [TOTAL]          $… (LLM)   $… (LLM + VM + 1.5× markup)

Exit 0 on a successful tool call; non-zero if pi crashes, search_docs
errors, or the parent turn never emits message_end.

Why a script and not a pytest test? Because it costs real money to
run (one Vertex call ≈ a few cents) and we don't want CI hitting
provider APIs on every commit. Run it manually before going live.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "web" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Imported AFTER sys.path manipulation. These are the EXACT same helpers
# chat_ws.py uses to bill in production — we're not reimplementing the math.
from services.billing import (  # noqa: E402
    SUB_LLM_TOOLS,
    estimate_prompt_cost,
    extract_sub_llm_usage,
    usage_token_total,
)
from services.models_registry import get_model  # noqa: E402


# ── ANSI colour helpers (ignored if NO_COLOR is set) ────────────────────────

def _supports_colour() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


C_BOLD = "\033[1m" if _supports_colour() else ""
C_GREEN = "\033[32m" if _supports_colour() else ""
C_YELLOW = "\033[33m" if _supports_colour() else ""
C_CYAN = "\033[36m" if _supports_colour() else ""
C_DIM = "\033[2m" if _supports_colour() else ""
C_RST = "\033[0m" if _supports_colour() else ""


def banner(line: str) -> None:
    print(f"\n{C_BOLD}{C_CYAN}── {line} ──{C_RST}")


# ── pi subprocess driver ────────────────────────────────────────────────────

DEFAULT_PROMPT = (
    "Use the search_docs tool to find how `set-rule` works in the typst "
    "language for the `typst` package. Just call the tool once with a "
    "concrete query, summarise the answer in two sentences, and stop."
)

# Multi-turn forcing prompts. Engineered to look as much like a real
# user chat as possible while still reliably exercising every billable
# code path the WS bridge sees:
#
#   Turn 1 — agent must call all THREE sub-LLM tools in one assistant
#            turn (search_docs + style_guide + web_search) plus a
#            side-effect tool (write). Stress-tests the per-event
#            billing path: chat_ws.py has to debit once per
#            tool_execution_end and once for the parent message_end.
#   Turn 2 — follow-up that re-uses the same workspace (proves session
#            continuity bills correctly across pi's history compaction
#            window).
#   Turn 3 — pure text reply (no tool calls). Proves that turns where
#            *only* the parent talks still produce a usage block.
MULTI_TURN_PROMPTS: list[str] = [
    # Turn 1: cram three sub-LLM calls + write into one assistant turn.
    # The phrasing is the strongest "you must use the tool" wording I've
    # found that still reads like a real user instruction.
    "I need a one-page intro to fletcher diagrams. Do these steps in "
    "order, calling the listed tool each time — do not answer from "
    "memory:\n"
    "1. Call `search_docs` with query=\"how to draw a node\" and "
    "package=\"fletcher\". This returns documentation snippets you "
    "must base the intro on.\n"
    "2. Call `style_guide` with query=\"minimalist monochrome palette "
    "for a maths textbook\". This returns the colours you must use.\n"
    "3. Call `web_search` with query=\"fletcher typst package github "
    "url\". Use the result to add a one-line citation.\n"
    "4. Call `write` to save the combined output to ./intro.md.\n"
    "Do not skip any of those four tool calls.",
    # Turn 2: continuation that exercises read + edit (no sub-LLM, just
    # parent-turn billing across a non-trivial context).
    "Read ./intro.md and replace the heading with `# Fletcher: a quick "
    "tour`. Use the edit tool.",
    # Turn 3: pure text reply, proves message_end bills correctly even
    # when no tools fire.
    "In one sentence, what's the difference between fletcher and cetz?",
]


async def _spawn_pi(
    *, workspace: Path, session_dir: Path, provider: str, model: str
) -> tuple[asyncio.subprocess.Process, asyncio.Task[None]]:
    """Spawn `pi --mode rpc` the same way services/pi_session.py does
    (sans permission extension — we want unattended runs). Returns the
    subprocess and a stderr-drain task the caller is responsible for
    cancelling."""
    cmd = [
        "pi",
        "--mode", "rpc",
        "--provider", provider,
        "--model", model,
        "--session-dir", str(session_dir),
        "--extension", str(REPO_ROOT / "extensions" / "typst-tools.ts"),
    ]
    print(f"{C_DIM}spawn:{C_RST} {' '.join(cmd)}")
    print(f"{C_DIM}cwd:  {workspace}{C_RST}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(workspace),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=16 * 1024 * 1024,
    )

    async def _drain_stderr() -> None:
        assert proc.stderr is not None
        while True:
            line = await proc.stderr.readline()
            if not line:
                return
            txt = line.decode("utf-8", errors="replace").rstrip()
            if "[permission]" in txt or "ERROR" in txt or "warning" in txt.lower():
                print(f"{C_DIM}pi-stderr: {txt}{C_RST}")

    stderr_task = asyncio.create_task(_drain_stderr())
    return proc, stderr_task


async def _send_prompt_and_collect(
    proc: asyncio.subprocess.Process, *, prompt_id: str, prompt: str, timeout_s: float = 300.0
) -> dict[str, Any]:
    """Send one `prompt` RPC, drain events until message_end (or
    error / timeout). Returns the per-turn breakdown — everything the
    caller needs to bill that turn."""
    assert proc.stdin is not None
    assert proc.stdout is not None
    cmd_payload = json.dumps({"id": prompt_id, "type": "prompt", "message": prompt}) + "\n"
    proc.stdin.write(cmd_payload.encode("utf-8"))
    await proc.stdin.drain()

    events: list[dict[str, Any]] = []
    sub_llm_events: list[dict[str, Any]] = []
    side_effect_tools: list[str] = []
    parent_message_end: Optional[dict[str, Any]] = None

    started = time.monotonic()
    while True:
        if time.monotonic() - started > timeout_s:
            raise TimeoutError(
                f"prompt {prompt_id} did not produce message_end within {timeout_s}s"
            )
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - started
            print(
                f"{C_DIM}…still waiting (elapsed={elapsed:.1f}s, events={len(events)}){C_RST}",
                file=sys.stderr,
            )
            continue
        if not line:
            break
        txt = line.decode("utf-8", errors="replace").strip()
        if not txt:
            continue
        try:
            evt = json.loads(txt)
        except json.JSONDecodeError:
            print(f"{C_DIM}non-json stdout: {txt[:200]}{C_RST}", file=sys.stderr)
            continue
        events.append(evt)

        kind = evt.get("type")
        tool = evt.get("toolName")
        if kind == "tool_execution_start" and tool:
            print(f"    {C_DIM}→ tool start: {tool}{C_RST}")
        if kind in ("tool_execution_end", "tool_result"):
            if tool in SUB_LLM_TOOLS:
                sub_llm_events.append(evt)
                marker = " (error)" if evt.get("isError") else ""
                print(
                    f"    {C_GREEN}✓{C_RST} sub-LLM tool finished: "
                    f"{C_BOLD}{tool}{C_RST}{marker}"
                )
            elif tool:
                side_effect_tools.append(tool)
                print(
                    f"    {C_DIM}✓ side-effect tool finished: {tool}{C_RST}"
                )
        elif kind == "message_end":
            msg = evt.get("message") or {}
            if msg.get("role") in (None, "assistant"):
                parent_message_end = evt
                print(f"  {C_GREEN}✓{C_RST} parent assistant turn ended")
                break
        elif kind in ("error", "abort"):
            print(f"{C_YELLOW}pi event {kind}:{C_RST} {evt}", file=sys.stderr)
            break

    return {
        "prompt": prompt,
        "events": events,
        "sub_llm_events": sub_llm_events,
        "side_effect_tools": side_effect_tools,
        "parent_message_end": parent_message_end,
        "elapsed_s": time.monotonic() - started,
    }


async def run_pi_and_capture(
    *,
    workspace: Path,
    session_dir: Path,
    provider: str,
    model: str,
    prompts: list[str],
) -> dict[str, Any]:
    """Spawn pi once, drive `prompts` through it sequentially, capture
    per-turn events. Same pi instance across all turns, exactly the
    way the WS bridge keeps a long-lived pi per session."""
    proc, stderr_task = await _spawn_pi(
        workspace=workspace, session_dir=session_dir, provider=provider, model=model
    )

    turns: list[dict[str, Any]] = []
    try:
        for i, prompt in enumerate(prompts, 1):
            print(f"\n{C_CYAN}── Turn {i}/{len(prompts)} ──{C_RST}")
            print(f"  {C_DIM}user:{C_RST} {prompt[:120]}{'…' if len(prompt) > 120 else ''}")
            turn = await _send_prompt_and_collect(
                proc, prompt_id=f"p{i}", prompt=prompt
            )
            turns.append(turn)
    finally:
        try:
            proc.stdin.close() if proc.stdin else None
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        stderr_task.cancel()

    return {"turns": turns}


# ── Reporting ───────────────────────────────────────────────────────────────

def fmt_money(usd: float) -> str:
    return f"${usd:.6f}"


def report_sub_llm(evt: dict[str, Any]) -> dict[str, float]:
    """Print the real-vs-computed comparison for one sub-LLM tool call.
    Returns the cost breakdown for the caller to aggregate."""
    tool = evt.get("toolName") or "?"
    usage = extract_sub_llm_usage(evt)
    if usage is None:
        print(
            f"{C_YELLOW}  ! {tool}: tool_execution_end did NOT carry usage.{C_RST}\n"
            f"    This is a regression — extensions/typst-tools.ts no longer\n"
            f"    surfaces details.usage. Live billing would silently be $0."
        )
        return {"llm": 0.0, "total": 0.0}

    model_id = str(usage.get("model") or "")
    cost = estimate_prompt_cost(usage, model_id=model_id)
    spec = get_model(model_id)
    rates = spec.cost if spec is not None else None
    print(f"  {C_BOLD}[{tool}]{C_RST}")
    print(
        f"    real: in={usage.get('input', 0):>6}  "
        f"out={usage.get('output', 0):>6}  "
        f"cacheR={usage.get('cacheRead', 0):>6}  "
        f"cacheW={usage.get('cacheWrite', 0):>6}    "
        f"model={C_CYAN}{model_id or '?'}{C_RST}"
    )
    if rates:
        # Show what the per-class breakdown sums to, exactly the way
        # estimate_prompt_cost computes it. Useful for spotting "we
        # multiplied by the wrong rate" bugs.
        in_usd = (usage.get("input", 0) or 0) * rates.input / 1_000_000
        out_usd = (usage.get("output", 0) or 0) * rates.output / 1_000_000
        cr_usd = (usage.get("cacheRead", 0) or 0) * rates.cache_read / 1_000_000
        cw_usd = (usage.get("cacheWrite", 0) or 0) * rates.cache_write / 1_000_000
        print(
            f"    calc: in={fmt_money(in_usd)}  out={fmt_money(out_usd)}  "
            f"cacheR={fmt_money(cr_usd)}  cacheW={fmt_money(cw_usd)}    "
            f"= {C_GREEN}{fmt_money(cost.llm_usd)}{C_RST} (LLM only)"
        )
    print(
        f"    bill: tokens_charged={usage_token_total(usage):>6}    "
        f"ledger_debit={C_GREEN}{fmt_money(cost.total_usd)}{C_RST} "
        f"(after VM amortisation + markup)"
    )
    return {"llm": cost.llm_usd, "total": cost.total_usd}


def report_parent(evt: dict[str, Any], parent_model: str) -> dict[str, float]:
    """Same shape as report_sub_llm but for the message_end of the
    parent assistant turn (which uses pi-ai's pre-normalized usage)."""
    msg = evt.get("message") or {}
    usage = msg.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    cost = estimate_prompt_cost(usage, model_id=parent_model)
    pi_total = ((usage.get("cost") or {}).get("total") if isinstance(usage.get("cost"), dict) else None)
    print(f"  {C_BOLD}[message_end · parent assistant turn]{C_RST}")
    print(
        f"    real: in={usage.get('input', 0):>6}  "
        f"out={usage.get('output', 0):>6}  "
        f"cacheR={usage.get('cacheRead', 0):>6}  "
        f"cacheW={usage.get('cacheWrite', 0):>6}    "
        f"model={C_CYAN}{parent_model}{C_RST}"
    )
    print(
        f"    bill: pi_cost.total={fmt_money(pi_total or 0.0)}    "
        f"calc.llm_usd={C_GREEN}{fmt_money(cost.llm_usd)}{C_RST}    "
        f"ledger_debit={C_GREEN}{fmt_money(cost.total_usd)}{C_RST}"
    )
    if pi_total and abs(pi_total - cost.llm_usd) > 1e-9:
        # estimate_prompt_cost short-circuits to pi's cost.total when set,
        # so this can only diverge if pi sent a stale cost AND we
        # recomputed — interesting drift signal.
        print(f"    {C_YELLOW}note:{C_RST} pi.cost.total != calc.llm_usd (using pi's value)")
    return {"llm": cost.llm_usd, "total": cost.total_usd}


# ── Main ───────────────────────────────────────────────────────────────────

async def main_async(args: argparse.Namespace) -> int:
    if shutil.which("pi") is None:
        print("error: `pi` not on PATH. Did you run `npm install`?", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="pi-cost-test-"))
    workspace = tmp / "workspace"
    workspace.mkdir(parents=True)
    session_dir = tmp / "chats"
    session_dir.mkdir(parents=True)

    for entry in ("package.json", "extensions", "guides", "node_modules"):
        src = REPO_ROOT / entry
        if src.exists():
            (workspace / entry).symlink_to(src)

    # Make the test environment match prod: chat_ws.py spawns pi with the
    # backend's working dir as cwd, so uvicorn auto-loads web/backend/.env.
    # If we don't load it here, PI_TYPST_ROUTER_MODEL etc. silently differ.
    backend_env = REPO_ROOT / "web" / "backend" / ".env"
    if backend_env.exists():
        for ln in backend_env.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    provider = os.environ.get("PI_PROVIDER", "anthropic-vertex")
    parent_model = args.model or os.environ.get("PI_MODEL", "claude-haiku-4-5")

    if args.multi_turn:
        prompts = list(MULTI_TURN_PROMPTS)
        mode_label = f"multi-turn ({len(prompts)} prompts)"
    else:
        prompts = [args.prompt]
        mode_label = "single-turn"

    banner(
        f"Live cost-verification ({mode_label}): provider={provider}, "
        f"parent model={parent_model}"
    )
    print(
        f"{C_DIM}workspace: {workspace}\n"
        f"chats:     {session_dir}{C_RST}"
    )

    try:
        result = await run_pi_and_capture(
            workspace=workspace,
            session_dir=session_dir,
            provider=provider,
            model=parent_model,
            prompts=prompts,
        )
    finally:
        if not args.keep_workspace:
            shutil.rmtree(tmp, ignore_errors=True)

    grand_llm = 0.0
    grand_charged = 0.0
    grand_sub_calls = 0
    grand_side_effects = 0
    grand_wall = 0.0
    parent_turn_failures: list[int] = []

    for i, turn in enumerate(result["turns"], 1):
        banner(f"Turn {i} report")
        print(f"  {C_DIM}prompt:{C_RST} {turn['prompt'][:120]}{'…' if len(turn['prompt']) > 120 else ''}")
        side_effects = turn["side_effect_tools"]
        sub_evts = turn["sub_llm_events"]
        print(
            f"  side-effect tools called: "
            f"[{', '.join(side_effects) if side_effects else 'none'}]"
        )
        print(f"  sub-LLM tools called: {len(sub_evts)}")

        turn_llm = 0.0
        turn_charged = 0.0
        for evt in sub_evts:
            b = report_sub_llm(evt)
            turn_llm += b["llm"]
            turn_charged += b["total"]

        if turn["parent_message_end"] is not None:
            b = report_parent(turn["parent_message_end"], parent_model)
            turn_llm += b["llm"]
            turn_charged += b["total"]
        else:
            print(
                f"{C_YELLOW}  ! No message_end captured for turn {i}.{C_RST}"
            )
            parent_turn_failures.append(i)

        print(
            f"  {C_BOLD}turn {i}: LLM={fmt_money(turn_llm)}  "
            f"charged={fmt_money(turn_charged)}  "
            f"wall={turn['elapsed_s']:.1f}s{C_RST}"
        )

        grand_llm += turn_llm
        grand_charged += turn_charged
        grand_sub_calls += len(sub_evts)
        grand_side_effects += len(side_effects)
        grand_wall += turn["elapsed_s"]

    banner(f"GRAND TOTAL across {len(result['turns'])} turn(s)")
    print(
        f"  side-effect tool calls: {grand_side_effects}\n"
        f"  sub-LLM tool calls:     {grand_sub_calls}\n"
        f"  LLM cost:               {C_GREEN}{fmt_money(grand_llm)}{C_RST}\n"
        f"  ledger debit:           {C_GREEN}{fmt_money(grand_charged)}{C_RST}\n"
        f"  total wall-clock:       {grand_wall:.1f}s"
    )

    failures: list[str] = []
    if args.multi_turn and grand_sub_calls < 1:
        failures.append("no sub-LLM tool ran across any turn")
    if not args.multi_turn and grand_sub_calls < 1:
        failures.append("search_docs was never called in single-turn mode")
    if parent_turn_failures:
        failures.append(
            f"turns missing message_end: {parent_turn_failures}"
        )
    if failures:
        print(f"\n{C_YELLOW}{C_BOLD}FAIL{C_RST} — {'; '.join(failures)}")
        return 1
    print(
        f"\n{C_GREEN}{C_BOLD}OK{C_RST} — every turn produced a parent "
        f"message_end and {grand_sub_calls} sub-LLM call(s) were billed."
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Single-turn prompt (ignored when --multi-turn is set).",
    )
    p.add_argument(
        "--multi-turn",
        action="store_true",
        help="Run the built-in 3-turn forcing sequence "
        "(search_docs → style_guide → web_search). Recommended.",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Parent model id (defaults to $PI_MODEL).",
    )
    p.add_argument(
        "--keep-workspace",
        action="store_true",
        help="Leave the temp workspace on disk for post-mortem.",
    )
    args = p.parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
