"""
Append-only per-workspace audit log for tool-call governance.

Every observable tool-call lifecycle event lands here as a single JSON line so
the user (and us, when debugging) can answer "what did the AI actually do in
this session?" without having to replay the full chat transcript.

We log regardless of permission mode — even Auto mode produces a trail. That's
the whole point: Auto trades pre-flight prompts for post-hoc accountability.

Layout
------
    web/data/audits/<wsid>.jsonl   ← one file per workspace, append-only

Each line:
    {
      "ts":      "2026-05-06T20:31:00Z",
      "sid":     "s_xxxxxx",          # session id within the workspace
      "uid":     "user_xxx",          # owning Clerk user id (or "dev")
      "tool":    "bash",              # tool name
      "event":   "policy_blocked",    # see EVENT_KINDS
      "input":   {...},               # tool args (truncated if huge)
      "reason":  "blocked: sudo",     # human-readable explanation, optional
      "extra":   {...}                # event-specific payload, optional
    }

We never read this file from inside hot paths. Reads are for the user-facing
"audit trail" UI in v1.1; for now writers only.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from config import DATA_ROOT

AUDIT_ROOT = DATA_ROOT / "audits"

# We cap the args payload so a multi-MB `write` doesn't bloat the log file.
# 8 KB is enough to identify what was being written without storing whole
# documents — the file itself is in shadow-git for the actual content.
_MAX_INPUT_SERIALIZED = 8 * 1024

# Coarse buckets we use across the system. Frontend may key off these to
# colour-code rows ("denied" red, "allowed" green, "blocked" orange).
EVENT_KINDS = frozenset(
    {
        "started",          # tool_execution_start observed (no permission gate)
        "completed",        # tool_execution_end with success
        "failed",           # tool_execution_end with isError
        "asked",            # permission prompt sent to user
        "allow_once",       # user approved, this call only
        "allow_session",    # user approved + remembered for the pi session
        "deny_once",        # user denied, this call only
        "deny_session",     # user denied + remembered for the pi session
        "policy_blocked",   # services/policy.check_bash short-circuited the call
        "timeout",          # user did not answer the permission prompt in time
    }
)

# A single global lock is fine — log writes are O(microseconds) and we
# never expect contention to dominate. Per-file locks would buy us nothing
# at the throughput we're targeting.
_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate_input(value: Any) -> Any:
    """Best-effort: keep the JSON small. Long strings get an ellipsis tail."""
    try:
        s = json.dumps(value, ensure_ascii=False)
    except Exception:
        return {"_unserializable": True, "type": type(value).__name__}
    if len(s) <= _MAX_INPUT_SERIALIZED:
        return value
    head = s[: _MAX_INPUT_SERIALIZED - 64]
    return {"_truncated": True, "preview": head, "original_bytes": len(s)}


def _path_for(wsid: str) -> Path:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    return AUDIT_ROOT / f"{wsid}.jsonl"


def record(
    *,
    wsid: str,
    sid: str,
    uid: str,
    tool: str,
    event: str,
    input: Optional[dict[str, Any]] = None,
    reason: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """
    Append one event line. Never raises — audit failures must not break the
    chat flow. If we can't write the log, we print a warning to stderr and
    keep going.
    """
    if not wsid or not sid or not tool or not event:
        # Defensive: silently drop malformed rows rather than crash a hot
        # path. Caller bug, not user-visible.
        return
    if event not in EVENT_KINDS:
        # Same — accept-and-warn beats crash.
        print(f"[audit] WARN: unknown event kind {event!r}", file=sys.stderr)

    row: dict[str, Any] = {
        "ts": _now_iso(),
        "sid": sid,
        "uid": uid or "anonymous",
        "tool": tool,
        "event": event,
    }
    if input is not None:
        row["input"] = _truncate_input(input)
    if reason:
        row["reason"] = reason
    if extra:
        row["extra"] = extra

    try:
        path = _path_for(wsid)
        line = json.dumps(row, ensure_ascii=False) + "\n"
        # We don't fsync — it's an audit log, not a financial ledger. A
        # crashed backend losing the last few hundred milliseconds of
        # writes is acceptable.
        with _lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
    except Exception as exc:
        print(f"[audit] WARN: failed to record {event!r} for {wsid}/{sid}: {exc}", file=sys.stderr)


def tail(wsid: str, limit: int = 200) -> list[dict[str, Any]]:
    """
    Return the last `limit` events for a workspace, oldest-first. Best-effort:
    skips malformed lines silently. Used by the (planned) audit-trail UI.
    """
    path = _path_for(wsid)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        # Cheap: read the file, take the last N parseable lines. For our
        # expected file sizes (KBs to low MBs) this is fine; if logs ever
        # grow past tens of MBs we'd switch to a reverse-chunked reader.
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for raw in lines[-max(limit, 0):]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except Exception as exc:
        print(f"[audit] WARN: failed to tail {wsid}: {exc}", file=sys.stderr)
    return out


def file_for(wsid: str) -> Path:
    """Public accessor in case other services want to e.g. attach the log
    to a deletion request or rotate it. No side effects."""
    return _path_for(wsid)


# Make sure the directory exists on import so the first writer doesn't race.
try:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
except Exception as exc:
    print(f"[audit] WARN: cannot create {AUDIT_ROOT}: {exc}", file=sys.stderr)
    # Not fatal; record() will retry on each call.
    _ = os
