"""
Mirror the in-flight assistant turn so we can persist it on Stop /
timeout / disconnect / crash BEFORE pi-mono's own ``message_end``
event fires.

Why this exists
---------------
pi-mono only writes a turn to its session JSONL on ``message_end`` —
that is the moment the assistant's content[] is fully assembled and pi
can persist a complete, well-typed record. Streaming deltas
(``text_delta``, ``thinking_delta``, ``toolcall_delta``, …) are
transient: they ship out on the WS for the SPA to render in real time,
but they never hit disk.

That's fine for happy-path turns. The failure mode is the user clicking
the red Stop button mid-stream, OR the WS dropping mid-stream, OR pi
crashing while a tool call's args are still being progressively-parsed::

    1. Assistant streams text + thinking → toolcall_start("write") →
       a flood of toolcall_deltas accumulating the file body.
    2. tool_execution_start hasn't fired yet (UI shows "queued").
    3. Connection dies / Stop pressed / pi crashed.
    4. pi-mono had nothing to persist — there is no record on disk
       of the half-finished tool call we already showed the user.
    5. On reconnect, ``services/history.load_history`` walks the JSONL
       and finds nothing for that turn. The chat shows the user's
       prompt followed by *silence*. Worse: the AI loaded into a fresh
       session has no idea what it was about to do.

We accumulate text + thinking + tool-call args + tool-execution status
as they pass through the ``pi_to_ws`` pump and, on
abort/timeout/disconnect, write our own synthetic line into the same
chats_dir pi-mono uses. ``load_history`` treats it like any other
completed turn — content[] just gets a stop banner appended so the user
can see why it cut off, and tool calls show up with their final
accumulated args + an "Aborted" toolResult so the AI can resume by
retrying instead of starting from zero.

Belt-and-braces: alongside the in-memory tracker, every relevant event
is *also* appended verbatim to a per-turn
``<turn-id>-inflight.jsonl`` file. That file is deleted on the normal
``message_end`` path (canonical record exists) and *kept* on any abort
path so you can grep it later if the synthetic line ever fails to
project the right state.

Files written
-------------
- ``YYYYMMDDTHHMMSS-…-inflight.jsonl`` — opened at turn start, every
  relevant event appended verbatim, deleted on message_end, *kept* on
  abort/disconnect/timeout.
- ``YYYYMMDDTHHMMSS-…-aborted.jsonl`` — single-or-multi-line JSONL
  containing the synthetic assistant ``message`` plus one
  ``toolResult`` per still-pending tool call, written from
  ``persist_if_in_flight``. This is the file ``load_history`` consumes
  on reload.

The file is named ``<UTC ISO>-aborted.jsonl`` so it sorts after pi's
existing files (pi uses the same ISO-prefix convention) but before any
future pi spawn. The history loader globs ``*.jsonl`` and folds them in
chronological order, so the partial turn lands exactly where the
user's eye expects it.

This module is intentionally self-contained and free of FastAPI / pi /
billing imports — it only touches stdlib + the chats_dir Path. That
makes it cheap to unit test and trivial to mirror into the desktop
backend (``desktop/backend/services/partial_turn.py``), which has the
same Stop-loses-history bug.

Usage from chat_ws::

    tracker = PartialTurnTracker(chats_dir=chats_dir, session_id=session_id)
    # In the pi_to_ws pump:
    async for evt in pi.events():
        tracker.observe(evt)
        ...
    # In the abort handler, BEFORE pi.terminate():
    tracker.persist_if_in_flight(reason="user_stop")
    # In the watchdog timeout handler:
    tracker.persist_if_in_flight(reason="timeout")
    # In the WS finally block:
    tracker.persist_if_in_flight(reason="disconnect")

`persist_if_in_flight` is idempotent — safe to call from multiple
teardown paths. Once a `message_end` event is observed for the active
turn the tracker disarms itself and subsequent persist calls are
no-ops, because pi already wrote the canonical record.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, IO


class PartialTurnTracker:
    """Track text + thinking + tool calls of the in-flight assistant
    turn. Also tees every observed event to a per-turn ``inflight``
    JSONL file so a hard process death (kernel panic, OOM kill before
    finally runs) still leaves a recoverable record on disk.

    Not thread-safe; each WS session owns its own tracker and is
    accessed from the single asyncio loop that runs the four pumps.
    """

    __slots__ = (
        "_chats_dir",
        "_session_id",
        "_active",
        "_ended",
        "_message_id",
        "_text",
        "_thinking",
        "_bg_stream",
        "_tool_calls",
        "_tool_call_order",
        "_stream_path",
        "_stream_fp",
    )

    def __init__(self, *, chats_dir: Path, session_id: str) -> None:
        self._chats_dir = chats_dir
        self._session_id = session_id
        self._active = False
        self._ended = False
        self._message_id = ""
        self._text = ""
        self._thinking = ""
        self._bg_stream = ""
        # tc_id → {id, name, arguments, arguments_partial_json,
        #          execution_status, result_text, is_error}
        # `arguments` is replaced (not appended) on each toolcall_delta
        # because pi-ai already does the progressive-JSON parsing and
        # ships us the running parsed object, NOT a raw delta string.
        self._tool_calls: dict[str, dict[str, Any]] = {}
        self._tool_call_order: list[str] = []
        self._stream_path: Path | None = None
        self._stream_fp: IO[str] | None = None

    # ── observation ──────────────────────────────────────────────────

    def observe(self, evt: dict[str, Any]) -> None:
        """Update internal state from a pi → SPA event.

        Hot path: called once per RPC event. Keep this branchless on
        the common cases (delta forwarding) and only reset state at
        turn boundaries."""
        if not isinstance(evt, dict):
            return
        et = evt.get("type")
        if et in ("agent_start", "turn_start"):
            self._reset_for_new_turn()
            self._open_stream_file()
            return
        if et == "message_end":
            # pi will persist the canonical line itself; drop our
            # buffer + delete the inflight tee so the next abort
            # doesn't double-write.
            self._ended = True
            self._active = False
            self._close_stream_file(delete=True)
            self._message_id = ""
            self._text = ""
            self._thinking = ""
            self._bg_stream = ""
            self._tool_calls = {}
            self._tool_call_order = []
            return

        # Every observed event after agent_start (and before
        # message_end) gets teed to disk verbatim. This is the
        # forensic safety net: even if persist_if_in_flight is never
        # called (process died abruptly), the inflight file is
        # already on disk with everything pi sent.
        if self._active:
            self._tee(evt)

        if et == "tool_execution_start":
            tc_id = evt.get("toolCallId")
            if isinstance(tc_id, str) and tc_id:
                self._ensure_tool_call(tc_id, name=evt.get("toolName"))
                self._tool_calls[tc_id]["execution_status"] = "running"
            return

        if et == "tool_execution_end":
            tc_id = evt.get("toolCallId")
            if isinstance(tc_id, str) and tc_id:
                tc = self._ensure_tool_call(tc_id, name=evt.get("toolName"))
                is_error = bool(evt.get("isError"))
                tc["execution_status"] = "error" if is_error else "success"
                tc["is_error"] = is_error
                tc["result_text"] = self._extract_result_text(evt.get("result"))
            return

        if et != "message_update":
            return

        sub = evt.get("assistantMessageEvent")
        if not isinstance(sub, dict):
            return

        if not self._active:
            self._reset_for_new_turn()
            self._open_stream_file()

        sub_type = sub.get("type")

        # ── text / thinking deltas ──────────────────────────────────
        if sub_type in ("text_delta", "thinking_delta"):
            delta = sub.get("delta")
            if isinstance(delta, str) and delta:
                if sub_type == "text_delta":
                    self._text += delta
                else:
                    self._thinking += delta
            if not self._message_id:
                mid = sub.get("messageId") or evt.get("id")
                if isinstance(mid, str) and mid:
                    self._message_id = mid
            return

        # ── tool-call lifecycle ─────────────────────────────────────
        # Event shape comes from pi-ai (verified against pi 0.73 +
        # the patched anthropic-vertex provider): the toolCall block
        # lives at sub.partial.content[contentIndex] for start/delta,
        # and sub.toolCall has the final dict on toolcall_end.
        if sub_type == "toolcall_start":
            block = self._pick_tool_call_block(sub)
            if isinstance(block, dict):
                tc_id = block.get("id")
                if isinstance(tc_id, str) and tc_id:
                    name = block.get("name")
                    self._ensure_tool_call(tc_id, name=name)
            return

        if sub_type == "toolcall_delta":
            block = self._pick_tool_call_block(sub)
            if isinstance(block, dict):
                tc_id = block.get("id")
                if isinstance(tc_id, str) and tc_id:
                    tc = self._ensure_tool_call(tc_id, name=block.get("name"))
                    args = block.get("arguments")
                    # pi-ai ships the *running parsed* arguments dict
                    # (not a delta) — we replace, never append.
                    if isinstance(args, dict):
                        tc["arguments"] = args
                    raw = block.get("partialJson")
                    if isinstance(raw, str):
                        tc["arguments_partial_json"] = raw
            return

        if sub_type == "toolcall_end":
            final = sub.get("toolCall")
            if isinstance(final, dict):
                tc_id = final.get("id")
                if isinstance(tc_id, str) and tc_id:
                    tc = self._ensure_tool_call(tc_id, name=final.get("name"))
                    args = final.get("arguments")
                    if isinstance(args, dict):
                        tc["arguments"] = args
            return

    def note_bg_output(self, stream: str, chunk: str) -> None:
        """Accumulate ``bg_output`` chunks (background bash / daemons) so
        disconnect / background-drain snapshots include terminal bytes the
        client already saw. Also tees a synthetic ``bg_output`` record into
        the per-turn inflight JSONL."""
        if not self._active or not isinstance(chunk, str) or not chunk:
            return
        self._tee({"type": "bg_output", "stream": stream, "chunk": chunk})
        self._bg_stream += chunk

    # ── helpers ─────────────────────────────────────────────────────

    def _ensure_tool_call(self, tc_id: str, *, name: Any = None) -> dict[str, Any]:
        tc = self._tool_calls.get(tc_id)
        if tc is None:
            tc = {
                "id": tc_id,
                "name": str(name) if isinstance(name, str) and name else "tool",
                "arguments": {},
                "arguments_partial_json": "",
                "execution_status": "pending",
                "is_error": False,
                "result_text": "",
            }
            self._tool_calls[tc_id] = tc
            self._tool_call_order.append(tc_id)
        elif isinstance(name, str) and name and tc["name"] == "tool":
            # Lazy-fill name if we discover it later (e.g. tool_execution_start
            # before toolcall_end on legacy variants).
            tc["name"] = name
        return tc

    @staticmethod
    def _pick_tool_call_block(sub: dict[str, Any]) -> dict[str, Any] | None:
        partial = sub.get("partial")
        if not isinstance(partial, dict):
            return None
        content = partial.get("content")
        if not isinstance(content, list) or not content:
            return None
        idx = sub.get("contentIndex")
        if not isinstance(idx, int) or idx < 0 or idx >= len(content):
            idx = len(content) - 1
        block = content[idx]
        if not isinstance(block, dict):
            return None
        if block.get("type") != "toolCall":
            return None
        return block

    @staticmethod
    def _extract_result_text(result: Any) -> str:
        """Pull a textual summary out of a tool_execution_end result.
        Used to enrich the synthetic toolResult line for tool calls
        that DID complete but whose assistant message_end never fired
        (e.g. user pressed Stop right between tool-end and the next
        text delta)."""
        if not isinstance(result, dict):
            return ""
        content = result.get("content")
        if not isinstance(content, list):
            return ""
        out: list[str] = []
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                t = c.get("text")
                if isinstance(t, str) and t:
                    out.append(t)
        return "\n".join(out)

    def _reset_for_new_turn(self) -> None:
        # Close any leaked inflight file from a prior turn that never
        # saw message_end (shouldn't happen normally — observe()
        # itself resets between turns — but defensive against pi
        # restarting mid-session).
        if self._stream_fp is not None:
            self._close_stream_file(delete=False)
        self._active = True
        self._ended = False
        self._message_id = ""
        self._text = ""
        self._thinking = ""
        self._bg_stream = ""
        self._tool_calls = {}
        self._tool_call_order = []

    # ── streaming-to-disk tee ───────────────────────────────────────

    def _open_stream_file(self) -> None:
        """Open a per-turn ``inflight`` JSONL file the moment a turn
        starts. Every observed event is appended verbatim. On
        message_end the file is deleted (canonical pi record exists);
        on any abort path it stays put so you can grep through it
        later if anything misbehaves."""
        try:
            self._chats_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%f")
            tag = uuid.uuid4().hex[:8]
            self._stream_path = self._chats_dir / f"{stamp}-{tag}-inflight.jsonl"
            # line buffering (1) keeps the OS page cache reasonably
            # fresh without forcing fsync per write — good balance of
            # safety vs throughput on a chatty hot path.
            self._stream_fp = self._stream_path.open(
                "w", encoding="utf-8", buffering=1
            )
        except Exception as exc:
            print(
                f"[partial_turn {self._session_id}] tee open failed: {exc!r}",
                file=sys.stderr,
            )
            self._stream_path = None
            self._stream_fp = None

    def _tee(self, evt: dict[str, Any]) -> None:
        fp = self._stream_fp
        if fp is None:
            return
        try:
            fp.write(json.dumps(evt, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            # Disk full / closed — disable the tee so we don't spam
            # logs once per event for the rest of the turn.
            print(
                f"[partial_turn {self._session_id}] tee write failed: {exc!r}",
                file=sys.stderr,
            )
            try:
                fp.close()
            except Exception:
                pass
            self._stream_fp = None

    def _close_stream_file(self, *, delete: bool, marker: dict[str, Any] | None = None) -> None:
        fp = self._stream_fp
        path = self._stream_path
        self._stream_fp = None
        self._stream_path = None
        if fp is None:
            return
        try:
            if marker is not None and not delete:
                try:
                    fp.write(
                        json.dumps(marker, ensure_ascii=False, default=str) + "\n"
                    )
                except Exception:
                    pass
            fp.close()
        except Exception:
            pass
        if delete and path is not None:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    # ── persistence ──────────────────────────────────────────────────

    def persist_if_in_flight(self, *, reason: str) -> bool:
        """Write a synthetic ``type: "message"`` line if the current
        turn never reached ``message_end``. Also writes one
        ``toolResult`` line per pending/running tool call so the
        history loader marks them as errored on reload.

        Returns True if a file was written, False otherwise.
        Idempotent across multiple teardown calls.
        """
        if not self._active or self._ended:
            return False
        text = self._text
        thinking = self._thinking
        tool_calls = [self._tool_calls[i] for i in self._tool_call_order]
        combined_text = text
        if self._bg_stream:
            bg = self._bg_stream.rstrip()
            if combined_text:
                combined_text = combined_text + "\n\n" + bg
            else:
                combined_text = bg
        if not text and not thinking and not tool_calls and not self._bg_stream:
            # Nothing to preserve — pi never streamed any content for
            # this turn (maybe abort fired before the first delta).
            self._active = False
            self._ended = True
            self._close_stream_file(
                delete=False,
                marker={"type": "_aborted", "reason": reason, "empty": True},
            )
            return False

        content: list[dict[str, Any]] = []
        if thinking:
            content.append({"type": "thinking", "thinking": thinking})
        # Tag the visible text so the user sees WHY it cut off. Reasons
        # are short slugs the SPA already understands; the user-facing
        # string is intentionally generic so we don't have to localise
        # here (history.py:_flatten_assistant_content just passes the
        # text through).
        banner = self._banner_for(reason)
        if combined_text:
            content.append({"type": "text", "text": combined_text + banner})
        elif not tool_calls:
            # No streamed text but we did capture thinking — surface a
            # standalone banner part so the turn isn't completely empty
            # in the rendered transcript.
            content.append({"type": "text", "text": banner.lstrip()})
        else:
            # Tool call(s) already visible (bash queued / running) but no
            # assistant prose yet — without a text part, reload looks like
            # the turn vanished. Mirror the banner we append when text exists.
            content.append({"type": "text", "text": banner.lstrip()})

        # Append every tool call we tracked. The history loader
        # (services/history.py::_flatten_assistant_content) already
        # handles type="toolCall" with id/name/arguments, so the AI
        # sees the full args (path + content for write, command for
        # bash, etc.) on reload — and can resume by retrying instead
        # of starting from zero.
        for tc in tool_calls:
            content.append({
                "type": "toolCall",
                "id": tc["id"],
                "name": tc["name"],
                "arguments": tc["arguments"] if isinstance(tc["arguments"], dict) else {},
            })

        msg_id = self._message_id or f"abort-{int(time.time() * 1000)}"
        lines: list[dict[str, Any]] = [{
            "type": "message",
            "id": msg_id,
            "message": {
                "role": "assistant",
                "content": content,
                # Non-standard fields; load_history ignores unknown
                # keys, but anyone tailing the JSONL for debugging gets
                # an obvious "this was a stop, not a normal end" marker.
                "aborted": True,
                "stopReason": reason,
            },
        }]

        # For each tool call, write a toolResult line. For ones that
        # actually completed (status success/error) we have the real
        # result text and pass it through; for ones that never reached
        # tool_execution_end (status pending/running) we synthesize an
        # error result with the abort reason so the rendered card
        # shows the user WHY the tool didn't finish.
        for tc in tool_calls:
            status = tc.get("execution_status", "pending")
            if status in ("success", "error"):
                result_text = tc.get("result_text") or ""
                is_error = bool(tc.get("is_error"))
            else:
                result_text = self._tool_abort_text(reason, tc["name"])
                is_error = True
            lines.append({
                "type": "message",
                "id": f"abort-result-{tc['id']}",
                "message": {
                    "role": "toolResult",
                    "toolCallId": tc["id"],
                    "content": [{"type": "text", "text": result_text}],
                    "isError": is_error,
                    "aborted": status not in ("success", "error"),
                },
            })

        try:
            self._chats_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%f")
            out = self._chats_dir / f"{stamp}-aborted.jsonl"
            with out.open("a", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except OSError:
                    pass
        except Exception as exc:
            # Persistence is best-effort — never let a disk error tear
            # down the abort handler.
            print(
                f"[partial_turn {self._session_id}] persist failed "
                f"(reason={reason}): {exc!r}",
                file=sys.stderr,
            )
            # Still close the inflight tee even if the synthetic
            # write failed — the tee file IS the recovery copy of
            # last resort.
            self._close_stream_file(
                delete=False,
                marker={"type": "_aborted", "reason": reason, "synth_failed": True},
            )
            self._active = False
            self._ended = True
            return False

        self._close_stream_file(
            delete=False,
            marker={"type": "_aborted", "reason": reason, "lines": len(lines)},
        )
        self._active = False
        self._ended = True
        return True

    @staticmethod
    def _banner_for(reason: str) -> str:
        # Plain-text banner appended to the surfaced text part. We keep
        # this short and emoji-free so it renders cleanly in the chat
        # bubble's markdown view AND in plain-text exports.
        if reason == "user_stop":
            return "\n\n_(stopped by user — partial response saved)_"
        if reason == "timeout":
            return "\n\n_(prompt timeout — partial response saved)_"
        if reason == "disconnect":
            return "\n\n_(connection closed — partial response saved)_"
        if reason in ("bg_cleanup", "bg_error"):
            return "\n\n_(connection closed — partial response saved)_"
        if reason == "bg_timeout":
            return "\n\n_(streaming timed out — partial response saved)_"
        return f"\n\n_(stopped: {reason} — partial response saved)_"

    @staticmethod
    def _tool_abort_text(reason: str, tool_name: str) -> str:
        if reason == "user_stop":
            return (
                f"Aborted: user pressed Stop before {tool_name} finished. "
                f"Arguments above are the latest snapshot pi streamed; the "
                f"call was not executed."
            )
        if reason == "timeout":
            return (
                f"Aborted: prompt timeout fired while {tool_name} was still "
                f"streaming arguments. The call was not executed."
            )
        if reason == "disconnect":
            return (
                f"Aborted: WebSocket closed before {tool_name} finished. "
                f"Arguments above are the last snapshot we received; the "
                f"call may or may not have been executed by pi — re-run "
                f"to be sure."
            )
        return (
            f"Aborted: {reason}. {tool_name} did not finish. Arguments "
            f"above are the latest snapshot pi streamed."
        )


# ── partial-context replay helpers ──────────────────────────────────────
#
# Mirrors web/backend/services/partial_turn.py — see that file for the
# full design rationale. Short version: pi-mono's session JSONL only
# contains entries pi itself wrote; the partial assistant text + tool
# calls live in the `*-aborted.jsonl` we created above. Pi never sees
# that file when `--continue` resumes (it requires a `{type:"session"}`
# header which our synthetic file omits). This means after Stop+resume
# pi has no memory of what it had been saying or about to do.
#
# Fix: when the WS reconnects, scan chats_dir for the most recent
# UN-CONSUMED `*-aborted.jsonl`, rehydrate it into a context block,
# and prepend it to the FIRST prompt the user sends. We then rename
# the file so we don't double-inject. The rendered transcript still
# reads from `*-aborted-consumed.jsonl` because load_history globs
# `*.jsonl` — only pi's side-channel context changes.


def find_recent_unconsumed_aborted(
    chats_dir: Path, *, max_age_seconds: float = 3600.0
) -> Path | None:
    """Return the path of the newest `*-aborted.jsonl` in ``chats_dir``
    that hasn't been marked consumed and isn't too old to bother
    rehydrating. Returns ``None`` if there's nothing to inject.

    The age cap is a safety net — silently injecting "I was about to
    write…" context into a conversation the user resumed a week later
    would be far more confusing than the dangling user msg pi
    naturally sees.
    """
    try:
        if not chats_dir.exists():
            return None
        candidates: list[tuple[float, Path]] = []
        for p in chats_dir.iterdir():
            name = p.name
            if not name.endswith("-aborted.jsonl"):
                continue
            try:
                mtime = p.stat().st_mtime
            except OSError:
                continue
            if mtime < time.time() - max_age_seconds:
                continue
            candidates.append((mtime, p))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    except Exception:
        return None


def load_aborted_summary(path: Path) -> dict[str, Any] | None:
    """Parse a `*-aborted.jsonl` into a flattened summary dict::

        {
            "text":     "<assistant prose, banner stripped>",
            "thinking": "<thinking blocks, joined>",
            "tools":    [{"name", "arguments", "status"}, ...],
            "reason":   "user_stop" | "timeout" | "disconnect" | ...,
        }

    Returns ``None`` on any parse failure. Caller renders the summary
    into a context block AND marks the file consumed once forwarded.
    """
    if not path.exists():
        return None
    text_parts: list[str] = []
    thinking_parts: list[str] = []
    tools: list[dict[str, Any]] = []
    reason: str = ""
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    line = json.loads(raw)
                except Exception:
                    continue
                if not isinstance(line, dict):
                    continue
                msg = line.get("message")
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") == "assistant":
                    if not reason and isinstance(msg.get("stopReason"), str):
                        reason = msg["stopReason"]
                    content = msg.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            bt = block.get("type")
                            if bt == "text":
                                t = block.get("text")
                                if isinstance(t, str):
                                    cleaned = t
                                    for marker in (
                                        "\n\n_(stopped",
                                        "\n\n_(prompt timeout",
                                        "\n\n_(connection closed",
                                        "\n\n_(streaming timed out",
                                    ):
                                        idx = cleaned.find(marker)
                                        if idx >= 0:
                                            cleaned = cleaned[:idx]
                                            break
                                    cleaned = cleaned.rstrip()
                                    if cleaned:
                                        text_parts.append(cleaned)
                            elif bt == "thinking":
                                tk = block.get("thinking")
                                if isinstance(tk, str) and tk:
                                    thinking_parts.append(tk.rstrip())
                            elif bt == "toolCall":
                                tools.append({
                                    "name": str(block.get("name") or "tool"),
                                    "arguments": block.get("arguments") if isinstance(block.get("arguments"), dict) else {},
                                    "status": "pending",
                                })
                elif msg.get("role") == "toolResult":
                    if tools:
                        last = tools[-1]
                        last["status"] = (
                            "error" if msg.get("isError") else "success"
                        )
    except Exception:
        return None
    return {
        "text": "\n\n".join(text_parts),
        "thinking": "\n\n".join(thinking_parts),
        "tools": tools,
        "reason": reason or "interrupted",
    }


def render_partial_context_block(summary: dict[str, Any]) -> str:
    """Format a flattened aborted-turn summary into a context block we
    prepend to the next user prompt. Wrapped in pseudo-XML tags so the
    LLM treats it as out-of-band context rather than a literal
    instruction. Long tool-call arguments are truncated so a single
    Stop in the middle of a huge `write` doesn't blow context budget."""
    text = (summary.get("text") or "").strip()
    tools = summary.get("tools") or []
    reason = str(summary.get("reason") or "interrupted")

    reason_blurb = {
        "user_stop": "the user pressed Stop",
        "timeout": "the request timed out",
        "disconnect": "the connection dropped",
        "bg_cleanup": "the connection dropped",
        "bg_error": "a background process error fired",
        "bg_timeout": "a background process timed out",
    }.get(reason, f"the previous turn was interrupted ({reason})")

    parts: list[str] = []
    parts.append(
        f"You started answering the user's previous message but {reason_blurb} "
        "before you could finish. The user has now sent the message that "
        "appears AFTER this block. Use this snapshot of your interrupted "
        "work to keep continuity — do NOT re-ask anything you already "
        "knew, and do NOT redo work you already finished:"
    )

    if text:
        parts.append("Partial reply you had streamed (verbatim):")
        snippet = text if len(text) <= 4000 else "…" + text[-4000:]
        parts.append(snippet)

    if tools:
        parts.append(
            "Tool calls that were in progress (NOT yet successfully "
            "completed unless marked success):"
        )
        for tc in tools:
            name = tc.get("name") or "tool"
            status = tc.get("status") or "pending"
            args = tc.get("arguments") or {}
            try:
                arg_blob = json.dumps(args, ensure_ascii=False)
            except Exception:
                arg_blob = str(args)
            if len(arg_blob) > 1500:
                arg_blob = arg_blob[:1500] + "…(truncated)"
            parts.append(f"- [{status}] {name}({arg_blob})")

    if not text and not tools:
        parts.append(
            "(You hadn't streamed any visible content yet — just "
            "acknowledge that the previous attempt was cut short and "
            "respond to the new message below.)"
        )

    body = "\n\n".join(parts)
    return (
        "<context-from-interrupted-turn>\n"
        f"{body}\n"
        "</context-from-interrupted-turn>"
    )


def mark_aborted_consumed(path: Path) -> None:
    """Rename ``*-aborted.jsonl`` → ``*-aborted-consumed.jsonl`` so we
    don't re-inject the same partial on every subsequent prompt of the
    new connection. Best-effort; failure falls back to deleting the
    file so we don't loop forever."""
    if not path.exists():
        return
    try:
        target = path.with_name(path.stem + "-consumed.jsonl")
        path.rename(target)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
