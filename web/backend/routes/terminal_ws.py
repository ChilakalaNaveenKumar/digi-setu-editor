"""
Terminal WebSocket bridge: xterm.js ⇄ PTY.

Three message types from the client:
    {type: "input",  data: "..."}        keystrokes
    {type: "resize", cols: N, rows: N}   pty resize
    {type: "kill"}                       request graceful shutdown

Server broadcasts:
    {type: "ready",  id, cols, rows, closed}     once on connect
    {type: "output", data: "..."}                pty stdout/stderr
    {type: "exit",   reason?: "..."}             pty died

Auth: same model as chat_ws — verify *before* accept() so the upgrade
fails with 4401, then check that the terminal's owning workspace
belongs to the caller (404-collapsed to "not found" so terminal ids
can't be enumerated).
"""

from __future__ import annotations

import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.auth import user_for_websocket
from services.pty_terminal import PtyHub
from services.registry import Registry

router = APIRouter()


@router.websocket("/ws/terminal/{term_id}")
async def terminal_ws(ws: WebSocket, term_id: str) -> None:
    user_id = await user_for_websocket(ws)
    if user_id is None:
        await ws.close(code=4401)
        return

    await ws.accept()

    located = PtyHub.instance().find_by_terminal(term_id)
    if located is None:
        await ws.send_json({"type": "exit", "reason": "not found"})
        await ws.close()
        return
    wsid, _registry, term = located

    ws_rec = Registry.instance().get_workspace(wsid)
    if not ws_rec or ws_rec.get("owner_user_id") != user_id:
        # Same 404-collapse rationale as the REST routes.
        await ws.send_json({"type": "exit", "reason": "not found"})
        await ws.close()
        return

    async def _push(chunk: bytes) -> None:
        if not chunk:
            with contextlib.suppress(Exception):
                await ws.send_json({"type": "exit"})
            return
        try:
            await ws.send_json({"type": "output", "data": chunk.decode("utf-8", "replace")})
        except Exception:
            pass

    unsub = term.subscribe(_push)
    with contextlib.suppress(Exception):
        await ws.send_json(
            {"type": "ready", "id": term.id, "cols": term.cols, "rows": term.rows, "closed": term.closed}
        )

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")
            if mtype == "input":
                term.write(msg.get("data", "").encode("utf-8"))
            elif mtype == "resize":
                term.resize(int(msg.get("cols", 80)), int(msg.get("rows", 24)))
            elif mtype == "kill":
                term.kill()
    except WebSocketDisconnect:
        pass
    finally:
        unsub()
