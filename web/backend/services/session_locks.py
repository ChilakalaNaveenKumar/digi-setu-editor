"""
Session ownership tracker — "one live WebSocket per session id".

Why this exists:
    Open the same chat session in two browser tabs and (without this
    tracker) two pi RPC subprocesses spawn against the same workspace
    + same JSONL chat log. They race on the log file, the second
    subprocess sees a half-written entry, the first emits stale
    snapshots — at best the chat history is corrupted, at worst the
    shadow-git commits double-fire.

    The user-friendly fix is "the older tab loses". When a new WS
    arrives for a session we're already serving, we politely close
    the old one with a custom 4409 code and the SPA shows
    "Continued in another tab — close this one to reconnect".

Design constraints:
  * Single-process. We're a single uvicorn worker by design (chat is
    sticky to a workspace's pi subprocess; multi-worker would need
    Redis or a router and we'd lose the on-disk simplicity that makes
    this stack debuggable). If we ever scale out, swap this for a
    Redis SETEX with the worker id.
  * Async-safe. asyncio.Lock around the dict so two WS upgrades that
    arrive within the same event-loop tick don't both think they
    "won".
  * Idempotent release. If the WS task crashes mid-handler, the
    `release` call inside the `finally` block must be safe to call
    multiple times.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from fastapi import WebSocket


# Custom WS close code for "kicked by a newer tab". 4xxx is reserved
# for application use by the WS spec; 4409 mirrors HTTP 409 Conflict
# which is the closest semantic match. The frontend listens for it
# explicitly so the user sees a nice "you opened another tab" notice
# rather than a generic disconnect.
KICKED_BY_NEWER_TAB = 4409


class _SessionLocks:
    def __init__(self) -> None:
        self._owners: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def claim(self, session_id: str, ws: WebSocket) -> None:
        """Register `ws` as the live owner of `session_id`. If another
        WS already owns it, close the old one with code 4409 first.
        Returns when the new owner is recorded."""
        async with self._lock:
            old = self._owners.get(session_id)
            self._owners[session_id] = ws
        if old is not None and old is not ws:
            print(
                f"[session_locks] {session_id}: kicking older tab "
                f"({id(old)}) for new connection ({id(ws)})",
                file=sys.stderr,
            )
            # Skip the close() entirely if the old socket is already in a
            # terminal state. Calling close() on a closed/closing socket
            # raises "Unexpected ASGI message" inside Starlette which then
            # bubbles out as an unhandled-exception traceback in the
            # uvicorn log — confusing despite being harmless.
            client_state = getattr(getattr(old, "client_state", None), "name", "")
            app_state = getattr(getattr(old, "application_state", None), "name", "")
            if client_state in ("DISCONNECTED",) or app_state in ("DISCONNECTED",):
                return
            try:
                await old.close(code=KICKED_BY_NEWER_TAB)
            except (RuntimeError, Exception) as exc:
                # Race: peer disconnected between the state check and the
                # close call. Logged at debug-level, not error.
                print(
                    f"[session_locks] kick race for {session_id} "
                    f"(peer already gone): {exc}",
                    file=sys.stderr,
                )

    async def release(self, session_id: str, ws: WebSocket) -> None:
        """Drop ownership IFF we still own the slot. We check identity
        because a newer connection may have taken over while we were
        winding down — in that case our release is a no-op."""
        async with self._lock:
            current = self._owners.get(session_id)
            if current is ws:
                self._owners.pop(session_id, None)

    def owner(self, session_id: str) -> Optional[WebSocket]:
        return self._owners.get(session_id)


_singleton: Optional[_SessionLocks] = None


def session_locks() -> _SessionLocks:
    global _singleton
    if _singleton is None:
        _singleton = _SessionLocks()
    return _singleton
