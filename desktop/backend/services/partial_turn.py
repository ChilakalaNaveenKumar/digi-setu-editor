"""
Mirror the in-flight assistant turn so we can persist a synthetic
``type: "message"`` JSONL line when the user clicks Stop (or the prompt
watchdog kills pi, or the WS drops mid-stream) BEFORE pi-mono's own
``message_end`` event fires.

Why this exists
---------------
pi-mono only writes a turn to its session JSONL on ``message_end`` —
that is the moment the assistant's content[] is fully assembled and pi
can persist a complete, well-typed record. Streaming deltas
(``text_delta``, ``thinking_delta``) are transient: they ship out on the
WS for the SPA to render in real time, but they never hit disk.

That's fine for happy-path turns. The failure mode is the user clicking
the red Stop button mid-stream::

    1. SPA sends `{type: "abort"}` over the WS.
    2. chat_ws sets `aborted["flag"] = True` and calls `pi.terminate()`.
    3. pi gets a SIGTERM before it ever reaches `message_end`.
    4. The synthetic JSONL on disk is unchanged — there's no record of
       the half-finished response the user already saw streaming.
    5. On reconnect, `services/history.load_history` walks the JSONL
       files and finds nothing for that turn. The chat history shows
       the user's prompt followed by *silence*.

We accumulate text + thinking deltas as they pass through the
``pi_to_ws`` pump and, on abort/timeout/disconnect, write our own
synthetic line into the same chats_dir pi-mono uses. ``load_history``
treats it like any other completed turn — content[] just gets a stop
banner appended so the user can see why it cut off.

The file is named ``<UTC ISO>-aborted.jsonl`` so it sorts after pi's
existing files (pi uses the same ISO-prefix convention) but before any
future pi spawn. The history loader globs ``*.jsonl`` and folds them
in chronological order, so the partial turn lands exactly where the
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
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PartialTurnTracker:
    """Track text + thinking deltas of the in-flight assistant turn.

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
    )

    def __init__(self, *, chats_dir: Path, session_id: str) -> None:
        self._chats_dir = chats_dir
        self._session_id = session_id
        self._active = False
        self._ended = False
        self._message_id = ""
        self._text = ""
        self._thinking = ""

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
            return
        if et == "message_end":
            # pi will persist the canonical line itself; drop our buffer
            # so the next abort doesn't double-write.
            self._ended = True
            self._active = False
            self._message_id = ""
            self._text = ""
            self._thinking = ""
            return
        if et != "message_update":
            return
        sub = evt.get("assistantMessageEvent")
        if not isinstance(sub, dict):
            return
        sub_type = sub.get("type")
        delta = sub.get("delta")
        # Some pi versions ship the running text in a different shape
        # (e.g. {text: "..."} on text_end) — those are non-essential for
        # the abort case because text_delta already streamed every char.
        if not isinstance(delta, str) or not delta:
            return
        if not self._active:
            self._reset_for_new_turn()
        if sub_type == "text_delta":
            self._text += delta
        elif sub_type == "thinking_delta":
            self._thinking += delta
        if not self._message_id:
            mid = sub.get("messageId") or evt.get("id")
            if isinstance(mid, str) and mid:
                self._message_id = mid

    def _reset_for_new_turn(self) -> None:
        self._active = True
        self._ended = False
        self._message_id = ""
        self._text = ""
        self._thinking = ""

    # ── persistence ──────────────────────────────────────────────────

    def persist_if_in_flight(self, *, reason: str) -> bool:
        """Write a synthetic ``type: "message"`` line if the current
        turn never reached ``message_end``.

        Returns True if a file was written, False otherwise. Idempotent
        across multiple teardown calls.
        """
        if not self._active or self._ended:
            return False
        text = self._text
        thinking = self._thinking
        if not text and not thinking:
            # Nothing to preserve — pi never streamed any content for
            # this turn (maybe abort fired before the first delta).
            self._active = False
            self._ended = True
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
        if text:
            content.append({"type": "text", "text": text + banner})
        else:
            # No streamed text but we did capture thinking — surface a
            # standalone banner part so the turn isn't completely empty
            # in the rendered transcript.
            content.append({"type": "text", "text": banner.lstrip()})

        msg_id = self._message_id or f"abort-{int(time.time() * 1000)}"
        line = {
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
        }

        try:
            self._chats_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%f")
            out = self._chats_dir / f"{stamp}-aborted.jsonl"
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        except Exception as exc:
            # Persistence is best-effort — never let a disk error tear
            # down the abort handler.
            print(
                f"[partial_turn {self._session_id}] persist failed "
                f"(reason={reason}): {exc!r}",
                file=sys.stderr,
            )
            return False

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
        return f"\n\n_(stopped: {reason} — partial response saved)_"
