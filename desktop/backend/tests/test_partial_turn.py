"""
Unit tests for ``services/partial_turn``.

The tracker is the safety net that prevents Stop / disconnect /
process-death from erasing in-flight assistant turns. We drive it
through synthetic pi → SPA event sequences and assert on what lands
on disk: both the synthetic ``*-aborted.jsonl`` (rendered into chat
history) and the per-turn ``*-inflight.jsonl`` tee (forensic copy).

Wire format reference
---------------------
The event shapes match what pi-mono 0.7x ships through the
``message_update`` channel — captured live from the running stack and
documented in ``desktop/frontend/src/lib/event-router.ts``. If pi
changes shape (e.g. renames ``toolcall_*`` to ``tool_call_*`` again),
these fixtures need updating in lockstep.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture()
def chats_dir(tmp_path: Path) -> Path:
    d = tmp_path / "chats"
    d.mkdir()
    return d


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _aborted_files(chats_dir: Path) -> list[Path]:
    return sorted(chats_dir.glob("*-aborted.jsonl"))


def _inflight_files(chats_dir: Path) -> list[Path]:
    return sorted(chats_dir.glob("*-inflight.jsonl"))


def _agent_start() -> dict[str, Any]:
    return {"type": "agent_start"}


def _text_delta(s: str, message_id: str = "msg-1") -> dict[str, Any]:
    return {
        "type": "message_update",
        "id": message_id,
        "assistantMessageEvent": {
            "type": "text_delta",
            "delta": s,
            "messageId": message_id,
        },
    }


def _thinking_delta(s: str, message_id: str = "msg-1") -> dict[str, Any]:
    return {
        "type": "message_update",
        "id": message_id,
        "assistantMessageEvent": {
            "type": "thinking_delta",
            "delta": s,
            "messageId": message_id,
        },
    }


def _toolcall_start(tc_id: str, name: str, idx: int = 0) -> dict[str, Any]:
    return {
        "type": "message_update",
        "assistantMessageEvent": {
            "type": "toolcall_start",
            "contentIndex": idx,
            "partial": {
                "content": [
                    {"type": "toolCall", "id": tc_id, "name": name, "arguments": {}},
                ],
            },
        },
    }


def _toolcall_delta(
    tc_id: str, name: str, args: dict, raw: str = "", idx: int = 0
) -> dict[str, Any]:
    return {
        "type": "message_update",
        "assistantMessageEvent": {
            "type": "toolcall_delta",
            "contentIndex": idx,
            "partial": {
                "content": [
                    {
                        "type": "toolCall",
                        "id": tc_id,
                        "name": name,
                        "arguments": args,
                        "partialJson": raw,
                    },
                ],
            },
        },
    }


def _toolcall_end(tc_id: str, name: str, args: dict) -> dict[str, Any]:
    return {
        "type": "message_update",
        "assistantMessageEvent": {
            "type": "toolcall_end",
            "toolCall": {"id": tc_id, "name": name, "arguments": args},
        },
    }


def _tool_exec_start(tc_id: str, name: str) -> dict[str, Any]:
    return {"type": "tool_execution_start", "toolCallId": tc_id, "toolName": name}


def _tool_exec_end(
    tc_id: str, name: str, *, is_error: bool, text: str
) -> dict[str, Any]:
    return {
        "type": "tool_execution_end",
        "toolCallId": tc_id,
        "toolName": name,
        "isError": is_error,
        "result": {"content": [{"type": "text", "text": text}]},
    }


def _message_end() -> dict[str, Any]:
    return {"type": "message_end"}


# ── tests ────────────────────────────────────────────────────────────


def test_empty_turn_writes_nothing(chats_dir: Path) -> None:
    """Abort fires before any deltas → no synthetic file, inflight
    file is closed but kept (with an `empty: true` marker) for
    forensics."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-1")
    t.observe(_agent_start())
    wrote = t.persist_if_in_flight(reason="user_stop")

    assert wrote is False
    assert _aborted_files(chats_dir) == []


def test_text_only_persists_with_banner(chats_dir: Path) -> None:
    """Classic case — pi streamed a few text deltas before the user
    pressed Stop. Synthetic message has the text + a banner; no tool
    calls, no toolResult lines."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-2")
    t.observe(_agent_start())
    t.observe(_text_delta("Hello, "))
    t.observe(_text_delta("world!"))
    wrote = t.persist_if_in_flight(reason="user_stop")

    assert wrote is True
    files = _aborted_files(chats_dir)
    assert len(files) == 1
    lines = _read_jsonl(files[0])
    assert len(lines) == 1  # one assistant message, zero toolResults
    msg = lines[0]
    assert msg["type"] == "message"
    assert msg["message"]["role"] == "assistant"
    content = msg["message"]["content"]
    assert any(
        c["type"] == "text" and "Hello, world!" in c["text"] and "stopped" in c["text"]
        for c in content
    )


def test_pending_tool_call_is_preserved_with_args(chats_dir: Path) -> None:
    """The exact bug the user hit — pi was streaming a `write` tool
    call's arguments when the WS dropped. Synthetic record must
    include the toolCall with whatever args we'd accumulated, plus a
    toolResult line marking the tool as aborted so the AI sees `I was
    half-way through writing this file` on reload."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-3")
    t.observe(_agent_start())
    t.observe(_text_delta("Let me create the file:\n"))
    t.observe(_toolcall_start("tc-1", "write"))
    # progressive arg parse — pi-ai replaces, never appends
    t.observe(_toolcall_delta(
        "tc-1", "write",
        {"path": "/workspace/foo.py"},
        raw='{"path":"/workspace/foo.py","content":"def',
    ))
    t.observe(_toolcall_delta(
        "tc-1", "write",
        {"path": "/workspace/foo.py", "content": "def hello():\n    pass"},
        raw='{"path":"/workspace/foo.py","content":"def hello():\\n    pass"}',
    ))
    # tool_execution_start fired — UI flipped from "queued" to
    # "running" — but execution_end never came (WS died here).
    t.observe(_tool_exec_start("tc-1", "write"))

    wrote = t.persist_if_in_flight(reason="disconnect")
    assert wrote is True

    files = _aborted_files(chats_dir)
    lines = _read_jsonl(files[0])
    assert len(lines) == 2  # assistant message + 1 toolResult

    asst = lines[0]
    assert asst["message"]["role"] == "assistant"
    asst_content = asst["message"]["content"]
    tool_blocks = [c for c in asst_content if c["type"] == "toolCall"]
    assert len(tool_blocks) == 1
    tc = tool_blocks[0]
    assert tc["id"] == "tc-1"
    assert tc["name"] == "write"
    assert tc["arguments"]["path"] == "/workspace/foo.py"
    assert "def hello()" in tc["arguments"]["content"]

    result = lines[1]
    assert result["message"]["role"] == "toolResult"
    assert result["message"]["toolCallId"] == "tc-1"
    assert result["message"]["isError"] is True
    assert result["message"]["aborted"] is True
    result_text = result["message"]["content"][0]["text"]
    assert "Aborted" in result_text


def test_completed_tool_call_keeps_real_result(chats_dir: Path) -> None:
    """Tool call completed cleanly (tool_execution_end fired with
    isError=False) BUT the assistant turn was aborted before
    message_end. We must surface the real result — not a fake
    "Aborted" placeholder — because the user-visible side effect of
    the tool already ran."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-4")
    t.observe(_agent_start())
    t.observe(_toolcall_start("tc-9", "bash"))
    t.observe(_toolcall_end("tc-9", "bash", {"command": "ls"}))
    t.observe(_tool_exec_start("tc-9", "bash"))
    t.observe(_tool_exec_end("tc-9", "bash", is_error=False, text="file1\nfile2"))
    # …and then user pressed Stop before the next text_delta.
    wrote = t.persist_if_in_flight(reason="user_stop")
    assert wrote is True

    lines = _read_jsonl(_aborted_files(chats_dir)[0])
    assert len(lines) == 2
    result = lines[1]["message"]
    assert result["role"] == "toolResult"
    assert result["isError"] is False
    assert result["aborted"] is False
    assert result["content"][0]["text"] == "file1\nfile2"


def test_message_end_deletes_inflight_and_disarms(chats_dir: Path) -> None:
    """Happy path: pi-mono finished the turn → message_end fired → we
    delete our tee file (canonical record exists in pi's own JSONL)
    AND subsequent persist_if_in_flight calls are no-ops."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-5")
    t.observe(_agent_start())
    t.observe(_text_delta("done"))
    assert len(_inflight_files(chats_dir)) == 1
    t.observe(_message_end())
    assert _inflight_files(chats_dir) == []
    assert _aborted_files(chats_dir) == []

    # Idempotent disarm — even if a stray disconnect fires later,
    # nothing should land on disk.
    wrote = t.persist_if_in_flight(reason="disconnect")
    assert wrote is False
    assert _aborted_files(chats_dir) == []


def test_inflight_tee_kept_on_abort(chats_dir: Path) -> None:
    """Verifies the forensic tee survives the abort path (so you can
    grep the raw event stream later if the synthetic projection is
    ever wrong)."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-6")
    t.observe(_agent_start())
    t.observe(_text_delta("partial"))
    t.persist_if_in_flight(reason="disconnect")

    inflights = _inflight_files(chats_dir)
    assert len(inflights) == 1
    body = _read_jsonl(inflights[0])
    # The text_delta we observed AND the abort marker we appended at
    # close should both be present.
    assert any(
        e.get("type") == "message_update" for e in body
    ), body
    assert body[-1]["type"] == "_aborted"
    assert body[-1]["reason"] == "disconnect"


def test_persist_is_idempotent(chats_dir: Path) -> None:
    """Stop handler + WS finally block both call persist; only one
    synthetic file may be written."""
    from services.partial_turn import PartialTurnTracker

    t = PartialTurnTracker(chats_dir=chats_dir, session_id="sess-7")
    t.observe(_agent_start())
    t.observe(_text_delta("hi"))

    a = t.persist_if_in_flight(reason="user_stop")
    b = t.persist_if_in_flight(reason="disconnect")
    assert a is True
    assert b is False
    assert len(_aborted_files(chats_dir)) == 1
