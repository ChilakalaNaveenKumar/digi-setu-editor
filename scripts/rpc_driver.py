#!/usr/bin/env python3
"""
Python ↔ pi over RPC. Proves two things at once:

  1. Pi can be driven entirely from code (Python here, but identical
     pattern in any language). Same path you'd use to plug pi into a
     FastAPI endpoint — subprocess + JSONL.

  2. Live progress works. Python reads pi's stdout line-by-line as
     events arrive. No 5-minute black box: every JSON event is
     printed with a wall-clock delta the moment it lands.

Protocol:
  - Send  : JSON object + "\n" on pi's stdin
  - Receive: one JSON object per "\n" on pi's stdout
  - Done  : close stdin → pi exits cleanly

Usage:
  python3 scripts/rpc_driver.py "Reply with exactly: OK"
  python3 scripts/rpc_driver.py "List 4 custom Typst tools, names only"
  python3 scripts/rpc_driver.py --raw "Compile workspace/main.typ"

Env (set by scripts/env.sh — source it before running):
  GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION
  PI_MODEL, PI_PROVIDER
  PI_TYPST_ROUTER_MODEL  (used by search_docs)
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def short(s: str, n: int = 220) -> str:
    s = s.replace("\n", "\\n")
    return s if len(s) <= n else s[:n] + f"…[+{len(s) - n}]"


def fmt_event(evt: dict, raw: bool) -> str | None:
    """Pretty one-liner for an RPC/agent event. Return None to skip."""
    if raw:
        return json.dumps(evt, ensure_ascii=False)

    t = evt.get("type")
    if t == "session":
        return f"▶ session   id={evt.get('id', '?')[:8]}  cwd={evt.get('cwd', '?')}"
    if t == "agent_start":
        return "▶ agent_start"
    if t == "turn_start":
        return "▶ turn_start"
    if t == "message_start":
        return f"→ message   role={evt.get('message', {}).get('role', '?')}"
    if t == "message_end":
        u = (evt.get("message") or {}).get("usage") or {}
        cost = (u.get("cost") or {}).get("total", 0)
        return f"← message   in={u.get('input', 0)} out={u.get('output', 0)} cost=${cost}"
    if t == "tool_execution":
        tid = str(evt.get("toolCallId", "?"))[:8]
        return f"⚙ tool      name={evt.get('toolName', '?')}  id={tid}"
    if t == "tool_result":
        body = " ".join(c.get("text", "") for c in (evt.get("content") or []))
        return f"✓ tool_done isError={evt.get('isError', False)}  text={short(body)}"
    if t == "turn_end":
        return "■ turn_end"
    if t == "agent_end":
        return "■ agent_end"
    if t == "response":
        return f"☎ response  cmd={evt.get('command', '?')}  ok={evt.get('success', '?')}"
    if t == "message_update":
        sub = (evt.get("assistantMessageEvent") or {}).get("type")
        delta = (evt.get("assistantMessageEvent") or {}).get("delta", "")
        if sub == "text_delta":
            return f"  …text:  {short(delta)}"
        if sub == "thinking_delta":
            return f"  …think: {short(delta)}"
        if sub == "tool_call_start":
            n = (evt.get("assistantMessageEvent") or {}).get("toolName", "?")
            return f"  ⚙ call_start  name={n}"
        return None
    return f"·{t or '?'}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="+", help="The user prompt to send to pi")
    parser.add_argument("--raw", action="store_true", help="Print raw JSONL events (don't prettify)")
    parser.add_argument("--no-extension", action="store_true", help="Don't load typst-tools.ts")
    parser.add_argument("--timeout", type=float, default=600.0, help="Hard timeout in seconds (default 600)")
    args = parser.parse_args()

    prompt = " ".join(args.prompt)

    pi_bin = os.environ.get("PI_BIN", "pi")
    provider = os.environ.get("PI_PROVIDER", "google-vertex")
    model = os.environ.get("PI_MODEL", "gemini-3.1-pro-preview-customtools")

    cmd = [
        pi_bin,
        "--mode", "rpc",
        "--provider", provider,
        "--model", model,
        "--no-session",
    ]
    if not args.no_extension:
        cmd += ["--extension", "./extensions/typst-tools.ts"]

    print(f"$ {' '.join(shlex.quote(c) for c in cmd)}", file=sys.stderr)
    print(f"  cwd     : {ROOT}", file=sys.stderr)
    print(f"  project : {os.environ.get('GOOGLE_CLOUD_PROJECT', '?')}", file=sys.stderr)
    print(f"  location: {os.environ.get('GOOGLE_CLOUD_LOCATION', '?')}", file=sys.stderr)
    print(f"  prompt  : {prompt}", file=sys.stderr)
    print(f"  ─── live events follow ───", file=sys.stderr)

    t0 = time.monotonic()

    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # line-buffered on the python side
        env=os.environ.copy(),
    )

    try:
        cmd_obj = {"id": "req-1", "type": "prompt", "message": prompt}
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(cmd_obj) + "\n")
        proc.stdin.flush()

        agent_done = False
        while True:
            if time.monotonic() - t0 > args.timeout:
                print(f"[{time.monotonic() - t0:6.1f}s] !! timeout, killing pi", file=sys.stderr)
                proc.kill()
                return 124

            assert proc.stdout is not None
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue

            line = line.rstrip("\r\n")
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                print(f"[{time.monotonic() - t0:6.1f}s] (non-json) {line}", file=sys.stderr)
                continue

            pretty = fmt_event(evt, args.raw)
            if pretty is not None:
                print(f"[{time.monotonic() - t0:6.1f}s] {pretty}")
                sys.stdout.flush()

            if evt.get("type") == "agent_end":
                agent_done = True
                proc.stdin.close()

        rc = proc.wait(timeout=10)
        elapsed = time.monotonic() - t0
        print(f"\n── pi exited rc={rc} after {elapsed:.1f}s, agent_end={agent_done} ──", file=sys.stderr)
        if proc.stderr:
            err = proc.stderr.read()
            if err:
                print(f"── pi stderr ──\n{err}", file=sys.stderr)
        return rc
    except KeyboardInterrupt:
        print("\n!! interrupted, killing pi", file=sys.stderr)
        proc.kill()
        return 130


if __name__ == "__main__":
    sys.exit(main())
