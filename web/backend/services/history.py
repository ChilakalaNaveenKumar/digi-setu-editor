"""
Project pi's per-session JSONL log into render-ready ChatMessage dicts.

Why a translation step at all?
    pi's persisted format ("message" with `role` ∈ user|assistant|toolResult,
    each carrying a content[] of typed parts) is *finalized* — completed
    turns, no streaming chunks. The frontend's event-router, on the other
    hand, builds the same domain model from a stream of granular RPC events
    (text_delta, toolcall_delta, tool_execution_end, etc.).

    Replaying the JSONL through the router would require synthesising a
    plausible stream, which is fragile (deltas, ordering, partial parses).
    History is by definition done — we project straight into the final
    ChatMessage shape and hand it to the chat store as-is.

Source-of-truth for the input format: a live capture of pi's
session-dir output, cross-referenced with pi-mono-main's
SessionPersister docs. The shape is stable across pi 0.7x.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.skills import strip_skill_prefix


def _flatten_assistant_content(content: list[dict]) -> tuple[list[dict], list[dict]]:
    """Project an assistant message's content[] into (parts, toolCalls).

    `parts` mirrors what the live event-router builds: ordered slices of
    "text", "thinking", and "tool" blocks so the UI can interleave them
    in the exact order pi emitted them.
    """
    parts: list[dict] = []
    tool_calls: list[dict] = []
    for c in content:
        ct = c.get("type")
        if ct == "text":
            text = c.get("text") or ""
            if not text:
                continue
            parts.append({
                "kind": "text",
                "id": f"hist-text-{len(parts)}",
                "text": text,
            })
        elif ct == "thinking":
            text = c.get("thinking") or c.get("text") or ""
            if not text:
                continue
            parts.append({
                "kind": "thinking",
                "id": f"hist-think-{len(parts)}",
                "text": text,
                "startedAt": 0,
                "endedAt": 0,
            })
        elif ct == "toolCall":
            args_raw = c.get("arguments")
            args = args_raw if isinstance(args_raw, dict) else {}
            tc: dict[str, Any] = {
                "id": str(c.get("id") or f"hist-tc-{len(tool_calls)}"),
                "name": str(c.get("name") or "tool"),
                "args": args,
                "argsPartial": "",
                "status": "pending",
            }
            tool_calls.append(tc)
            parts.append({
                "kind": "tool",
                "id": tc["id"],
                "call": tc,
            })
    return parts, tool_calls


def load_history(chats_dir: Path) -> list[dict[str, Any]]:
    """Read every *.jsonl in `chats_dir` (chronological by filename) and
    return a flat list of frontend ChatMessage dicts (kind=user|assistant).

    Each pi process spawn writes a new JSONL file inside the same session
    directory. Filenames are ISO-timestamp prefixed so lexicographic sort
    == chronological order, even across resumes.

    Tool results in pi's stream live as their own toolResult-role messages
    that *follow* the assistant message that emitted the tool call. We use
    a running index keyed by toolCallId to attach each result back to the
    ToolCall it belongs to, so the rendered card shows status + output
    just like a live one.
    """
    if not chats_dir.exists():
        return []
    files = sorted(chats_dir.glob("*.jsonl"))
    if not files:
        return []

    messages: list[dict[str, Any]] = []
    tool_call_index: dict[str, dict[str, Any]] = {}
    # Reverse lookup: which assistant message owns each toolCallId.
    # Used by the orphan sweep below to stamp `stopReason: "aborted"`
    # on the parent message when its tool call never produced a
    # result (e.g. pi was SIGKILL'd mid-execution).
    tool_call_to_message: dict[str, dict[str, Any]] = {}

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            continue

        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") != "message":
                continue

            payload = evt.get("message") or {}
            role = payload.get("role")
            content = payload.get("content") or []
            if not isinstance(content, list):
                continue

            if role == "user":
                # Pi sometimes records synthesised tool-result-only "user"
                # messages internally; only keep those that carry actual
                # human text.
                text = "".join(
                    (c.get("text") or "") for c in content if c.get("type") == "text"
                ).strip()
                if not text:
                    continue
                # The chat_sse route prepends `<skill ...>...</skill>\n\n`
                # blocks to user prompts at send time so the model sees
                # the skill body in-context. Pi persists the prompt
                # verbatim, so we strip the leading skill chunks back
                # out here — otherwise reload / resume surfaces the
                # raw skill markup inside the user's chat bubble.
                text = strip_skill_prefix(text).strip()
                if not text:
                    continue
                messages.append({
                    "kind": "user",
                    "id": str(evt.get("id") or f"hist-u-{len(messages)}"),
                    "text": text,
                })

            elif role == "assistant":
                parts, tool_calls = _flatten_assistant_content(content)
                if not parts and not tool_calls:
                    continue
                text_acc = "".join(p["text"] for p in parts if p["kind"] == "text")
                thinking_acc = "".join(p["text"] for p in parts if p["kind"] == "thinking")
                asst: dict[str, Any] = {
                    "kind": "assistant",
                    "id": str(evt.get("id") or f"hist-a-{len(messages)}"),
                    "parts": parts,
                    "text": text_acc,
                    "thinking": thinking_acc,
                    "toolCalls": tool_calls,
                    "done": True,
                }
                usage = payload.get("usage")
                if isinstance(usage, dict):
                    cost = usage.get("cost") if isinstance(usage.get("cost"), dict) else {}
                    asst["usage"] = {
                        "input": int(usage.get("input") or 0),
                        "output": int(usage.get("output") or 0),
                        "cacheRead": int(usage.get("cacheRead") or 0),
                        "cacheWrite": int(usage.get("cacheWrite") or 0),
                        "cost": float((cost or {}).get("total") or 0),
                    }
                messages.append(asst)
                stop_reason = payload.get("stopReason")
                if isinstance(stop_reason, str):
                    asst["stopReason"] = stop_reason
                err_msg = payload.get("errorMessage")
                if isinstance(err_msg, str) and err_msg:
                    asst["errorMessage"] = err_msg
                for tc in tool_calls:
                    tool_call_index[tc["id"]] = tc
                    tool_call_to_message[tc["id"]] = asst

            elif role == "toolResult":
                tc_id = payload.get("toolCallId")
                if not isinstance(tc_id, str):
                    continue
                tc = tool_call_index.get(tc_id)
                if tc is None:
                    continue
                text = "\n".join(
                    (c.get("text") or "") for c in content
                    if c.get("type") == "text" and c.get("text")
                ).strip()
                is_error = bool(payload.get("isError"))
                tc["status"] = "error" if is_error else "success"
                tc["result"] = {
                    "text": text,
                    "isError": is_error,
                    "raw": content,
                }

    # ── orphan sweep ────────────────────────────────────────────────
    # Any tool call still marked `pending` after replay never received
    # its `toolResult` — almost always because pi was SIGKILL'd or
    # crashed mid-execution (e.g. user pressed Stop during a slow
    # subagent fan-out and we escalated past the graceful grace
    # window). If we left these as `pending`, the SPA would render an
    # eternal spinner the moment the user refreshes the chat — the
    # exact "subagent card still spinning after refresh" symptom from
    # 2026-05-16. Flip them to `error` and stamp the parent assistant
    # message with `stopReason: "aborted"` so Messages.vue renders
    # the italic "Request aborted" affordance (mirrors pi-mono web-ui
    # Messages.ts:126 behaviour for ungranted tool results).
    for tcid, tc in tool_call_index.items():
        if tc.get("status") != "pending":
            continue
        tc["status"] = "error"
        tc["result"] = {
            "text": "Aborted (the previous run was interrupted).",
            "isError": True,
            "raw": [{"type": "text", "text": "Aborted (the previous run was interrupted)."}],
        }
        parent = tool_call_to_message.get(tcid)
        if parent is not None and not parent.get("stopReason"):
            parent["stopReason"] = "aborted"
            parent.setdefault("errorMessage", "Request was aborted.")

    return messages
