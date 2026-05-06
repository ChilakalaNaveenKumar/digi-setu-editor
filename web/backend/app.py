"""
FastAPI bridge: browser ⇄ pi RPC subprocess.

One WebSocket per session id. The bridge is intentionally thin — every JSON
event from pi is forwarded verbatim to the browser, every JSON command from
the browser is forwarded verbatim to pi. No translation, no filtering. The
Vue side is responsible for rendering.

In addition to the pi event stream, each WS also receives `fs_change` events
from a global WorkspaceWatcher (watchdog over PROJECT_ROOT/workspace) so the
file tree updates live as pi creates/modifies/deletes files.

Endpoints
─────────
GET  /api/sessions                       → list saved sessions
POST /api/sessions                       → allocate a new session id
GET  /api/files                          → flat list of workspace contents
GET  /api/files/content?path=relative    → read a file's text contents
GET  /healthz                            → liveness
WS   /ws/sessions/{session_id}           → bidirectional bridge to pi + fs events
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from bg_processes import BackgroundProcessRegistry
from fastapi.responses import FileResponse
from file_watcher import (
    WORKSPACE_ROOT,
    WorkspaceWatcher,
    copy_path,
    create_file,
    create_folder,
    delete_path,
    list_tree,
    move_path,
    read_file,
    rename_path,
    stream_raw_path,
)
from pi_session import SESSIONS_ROOT, PiSession
from pty_terminal import discover_shell_profiles, registry as pty_registry
from shadow_git import ShadowGit

app = FastAPI(title="pi-typst-test web bridge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _bootstrap_watcher() -> None:
    """Start the workspace file watcher once when the server boots."""
    await WorkspaceWatcher.instance().ensure_started()
    # Initialize the shadow git repo (Cline / Roo Code / Aider pattern) used
    # for accurate per-tool-call diffs that survive multiple subsequent edits.
    await ShadowGit.instance().ensure_init()


# ── REST: session catalogue ─────────────────────────────────────────────────
@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sessions")
async def list_sessions() -> dict[str, list[dict[str, Any]]]:
    """List sessions = subdirectories under web/sessions/, newest first."""
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for entry in SESSIONS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        items.append(
            {
                "id": entry.name,
                "path": str(entry),
                "modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            }
        )
    items.sort(key=lambda x: x["modified"], reverse=True)
    return {"sessions": items}


@app.post("/api/sessions")
async def create_session() -> dict[str, str]:
    """Allocate a new session id. The folder is created lazily by PiSession."""
    sid = secrets.token_urlsafe(8)
    return {"id": sid}


# ── REST: workspace files ───────────────────────────────────────────────────
@app.get("/api/files")
async def get_files() -> dict[str, Any]:
    """Snapshot the workspace as a flat list. Frontend builds the visual tree."""
    return {"items": list_tree()}


@app.get("/api/files/content")
async def get_file_content(path: str = Query(..., description="Workspace-relative posix path")) -> dict[str, Any]:
    try:
        return read_file(path)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except IsADirectoryError:
        raise HTTPException(status_code=400, detail=f"Path is a directory: {path}")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"OS error: {exc}")


@app.get("/api/files/raw")
async def get_file_raw(path: str = Query(..., description="Workspace-relative posix path")) -> FileResponse:
    """Stream a workspace file with the right Content-Type. Used by the
    editor pane to render images, PDFs, audio, and video previews
    without ever reading the bytes through Python."""
    try:
        abs_path, mime = stream_raw_path(path)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except IsADirectoryError:
        raise HTTPException(status_code=400, detail=f"Path is a directory: {path}")
    return FileResponse(
        path=str(abs_path),
        media_type=mime,
        # `inline` so the browser displays it instead of downloading.
        headers={"Content-Disposition": f"inline; filename=\"{abs_path.name}\""},
    )


# ── REST: workspace mutations (create / mkdir / rename / delete / save) ────
def _fs_error(exc: BaseException) -> HTTPException:
    """Translate a file-system error into the right HTTP status."""
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc) or "permission denied")
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc) or "not found")
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=409, detail=str(exc) or "already exists")
    if isinstance(exc, IsADirectoryError):
        return HTTPException(status_code=400, detail=str(exc) or "is a directory")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc) or "bad request")
    return HTTPException(status_code=500, detail=str(exc) or "internal error")


@app.post("/api/fs/file")
async def fs_create_file(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new file (or overwrite when `overwrite=true`). Body:
        { path: "workspace/foo.txt", content?: string, overwrite?: bool }
    """
    path = payload.get("path")
    content = payload.get("content", "") or ""
    overwrite = bool(payload.get("overwrite", False))
    if not isinstance(path, str) or not isinstance(content, str):
        raise HTTPException(status_code=400, detail="path and content must be strings")
    try:
        return create_file(path, content, overwrite=overwrite)
    except (PermissionError, FileExistsError, IsADirectoryError, ValueError, FileNotFoundError) as exc:
        raise _fs_error(exc)


@app.post("/api/fs/folder")
async def fs_create_folder(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a folder. Body: { path: "workspace/new_dir" }"""
    path = payload.get("path")
    if not isinstance(path, str):
        raise HTTPException(status_code=400, detail="path must be a string")
    try:
        return create_folder(path)
    except (PermissionError, FileExistsError, ValueError) as exc:
        raise _fs_error(exc)


@app.delete("/api/fs/path")
async def fs_delete(path: str = Query(..., description="Workspace-relative posix path")) -> dict[str, Any]:
    """Delete a file or recursively delete a folder."""
    try:
        return delete_path(path)
    except (PermissionError, FileNotFoundError) as exc:
        raise _fs_error(exc)


@app.post("/api/fs/rename")
async def fs_rename(payload: dict[str, Any]) -> dict[str, Any]:
    """Rename / move. Body: { from: "old/path", to: "new/path" }"""
    src = payload.get("from")
    dst = payload.get("to")
    if not isinstance(src, str) or not isinstance(dst, str):
        raise HTTPException(status_code=400, detail="`from` and `to` must be strings")
    try:
        return rename_path(src, dst)
    except (PermissionError, FileNotFoundError, FileExistsError, ValueError) as exc:
        raise _fs_error(exc)


@app.post("/api/fs/copy")
async def fs_copy(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Copy a file or folder. Body: { from: "src/path", to?: "dst/path" }.
    If `to` is omitted we duplicate next to the source ("foo (copy).py").
    If `to` is an existing directory we copy INTO it.
    """
    src = payload.get("from")
    dst = payload.get("to")
    if not isinstance(src, str):
        raise HTTPException(status_code=400, detail="`from` must be a string")
    if dst is not None and not isinstance(dst, str):
        raise HTTPException(status_code=400, detail="`to` must be a string when present")
    try:
        return copy_path(src, dst)
    except (PermissionError, FileNotFoundError, ValueError) as exc:
        raise _fs_error(exc)


@app.post("/api/fs/move")
async def fs_move(payload: dict[str, Any]) -> dict[str, Any]:
    """Move (cut+paste) a file or folder. Body: { from: ..., to: ... }."""
    src = payload.get("from")
    dst = payload.get("to")
    if not isinstance(src, str) or not isinstance(dst, str):
        raise HTTPException(status_code=400, detail="`from` and `to` must be strings")
    try:
        return move_path(src, dst)
    except (PermissionError, FileNotFoundError, ValueError) as exc:
        raise _fs_error(exc)


# ── REST: per-tool-call snapshot diff (shadow-git backed) ──────────────────
@app.get("/api/snapshots/{tool_call_id}/diff")
async def get_snapshot_diff(tool_call_id: str) -> dict[str, Any]:
    """
    Return the full-context unified diff for a single tool call, resolved
    against the workspace state immediately BEFORE that call ran. This is
    the source-of-truth for the editor's "View diff" mode and is correct
    even after dozens of subsequent edits to the same file.
    """
    payload = ShadowGit.instance().diff_for_tool_call(tool_call_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshot recorded for tool_call_id={tool_call_id}",
        )
    return payload


@app.post("/api/snapshots/{tool_call_id}/restore")
async def restore_snapshot(tool_call_id: str) -> dict[str, Any]:
    """
    Rewind the workspace to the state RIGHT BEFORE this tool call ran.
    Files this tool call (and every later tool call) touched are restored
    to their pre-call versions. Files that didn't exist back then are
    deleted. Files the user manually edited (never tracked by the agent)
    are untouched.

    This is the "rewind from here" semantic used by Cursor and opencode.
    """
    result = await ShadowGit.instance().restore_to_before_tool_call(tool_call_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshot recorded for tool_call_id={tool_call_id}",
        )
    return result


@app.post("/api/turns/{user_message_id}/revert")
async def revert_turn(user_message_id: str) -> dict[str, Any]:
    """
    Revert every file change made in response to one user prompt. Equivalent
    to clicking restore on the FIRST tool call of that turn — undoes the
    whole agent reply.
    """
    result = await ShadowGit.instance().revert_user_turn(user_message_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshots recorded for user_message_id={user_message_id}",
        )
    return result


# ── REST: background-process control (LLM-free path) ───────────────────────
@app.get("/api/bg")
async def list_bg_processes() -> dict[str, Any]:
    """Snapshot of every bg process the @aliou/pi-processes extension started."""
    return {"processes": BackgroundProcessRegistry.instance().list()}


@app.post("/api/bg/{process_id}/kill")
async def kill_bg_process(process_id: str) -> dict[str, Any]:
    """
    SIGTERM (then SIGKILL after 5s) the named bg process directly via its pid.
    No LLM in the loop — this returns within ~5s worst-case and broadcasts
    `bg_ended` to every WS subscriber so the UI flips to "killed" instantly.
    """
    result = await BackgroundProcessRegistry.instance().kill(process_id)
    if not result.get("ok") and result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail=f"Unknown bg process: {process_id}")
    return result


# ── REST: interactive PTY terminals (xterm.js bridge) ─────────────────────
@app.get("/api/terminals/profiles")
async def list_terminal_profiles() -> dict[str, Any]:
    """Available shell profiles for the user to pick when creating a
    new interactive terminal. Picked from $SHELL + /etc/shells."""
    return {"profiles": discover_shell_profiles()}


@app.get("/api/terminals")
async def list_terminals() -> dict[str, Any]:
    """All live interactive terminal sessions (PTYs)."""
    return {
        "terminals": [pty_registry.serialize(t) for t in pty_registry.all()],
    }


@app.post("/api/terminals")
async def create_terminal(body: dict[str, Any]) -> dict[str, Any]:
    """
    Spawn a fresh PTY running the requested shell. Body:
      { shell?: string, cwd?: string, cols?: int, rows?: int }
    """
    shell = str(body.get("shell") or "").strip() or "default"
    cwd = str(body.get("cwd") or "").strip() or str(WORKSPACE_ROOT)
    cols = int(body.get("cols") or 80)
    rows = int(body.get("rows") or 24)
    try:
        term = pty_registry.create(shell=shell, cwd=cwd, cols=cols, rows=rows)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"failed to spawn pty: {exc}")
    return pty_registry.serialize(term)


@app.delete("/api/terminals/{term_id}")
async def delete_terminal(term_id: str) -> dict[str, Any]:
    """Kill the underlying shell + remove the registry entry."""
    if not pty_registry.kill(term_id):
        raise HTTPException(status_code=404, detail=f"Unknown terminal: {term_id}")
    pty_registry.remove(term_id)
    return {"ok": True}


@app.websocket("/ws/terminal/{term_id}")
async def terminal_ws(ws: WebSocket, term_id: str) -> None:
    """
    Bi-directional bridge between the browser's xterm.js instance and
    the PTY identified by `term_id`.

    Client→server messages (text frames carrying JSON):
        {"type": "input", "data": "..."}   # raw keystrokes
        {"type": "resize", "cols": 80, "rows": 24}

    Server→client messages:
        {"type": "output", "data": "..."}  # stdout chunks (utf-8 best-effort)
        {"type": "exit"}                   # session terminated

    We DON'T close the terminal when the websocket disconnects — the user
    may simply have closed a browser tab; the shell keeps running and
    a future ws connection picks up where they left off.
    """
    await ws.accept()
    term = pty_registry.get(term_id)
    if not term:
        await ws.send_json({"type": "exit", "reason": "not found"})
        await ws.close()
        return

    async def _push(chunk: bytes) -> None:
        if not chunk:
            with contextlib.suppress(Exception):
                await ws.send_json({"type": "exit"})
            return
        # xterm.js parses utf-8; bad bytes get the replacement char.
        try:
            await ws.send_json({"type": "output", "data": chunk.decode("utf-8", "replace")})
        except Exception:
            pass

    unsub = term.subscribe(_push)
    # Send initial geometry confirmation + closed flag so the client
    # can update its UI state.
    with contextlib.suppress(Exception):
        await ws.send_json(
            {
                "type": "ready",
                "id": term.id,
                "cols": term.cols,
                "rows": term.rows,
                "closed": term.closed,
            }
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
                data = msg.get("data", "")
                term.write(data.encode("utf-8"))
            elif mtype == "resize":
                term.resize(int(msg.get("cols", 80)), int(msg.get("rows", 24)))
            elif mtype == "kill":
                term.kill()
    except WebSocketDisconnect:
        pass
    finally:
        unsub()


# ── WebSocket: pi RPC bridge + fs_change broadcast ──────────────────────────
@app.websocket("/ws/sessions/{session_id}")
async def session_ws(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    pi = PiSession(session_id=session_id)

    try:
        await pi.start()
    except Exception as exc:
        print(f"[ws {session_id}] failed to start pi: {exc}", file=sys.stderr)
        await ws.send_json(
            {
                "type": "_bridge_error",
                "message": f"Failed to start pi subprocess: {exc}",
            }
        )
        await ws.close()
        return

    # Subscribe this WS to filesystem events. Unsubscribe on disconnect so
    # the watcher doesn't grow a stale subscriber list.
    fs_watcher = WorkspaceWatcher.instance()
    fs_queue = fs_watcher.subscribe()

    # Subscribe to background-process events (bg_started, bg_output, bg_ended)
    # from the global registry. Same fan-out semantics as fs_watcher.
    bg_registry = BackgroundProcessRegistry.instance()
    bg_queue = bg_registry.subscribe()

    # Track tool_call_id → (tool_name, path) so we can record snapshots
    # against the right path on tool_execution_end. Args ride on a few
    # different events depending on pi version, so we capture from each.
    pending_tool_calls: dict[str, dict[str, str]] = {}
    shadow = ShadowGit.instance()
    # Most-recent user message id forwarded to pi. Every tool call we
    # snapshot until the NEXT prompt arrives is attributed to this id, so
    # "revert turn" can find them all in one query.
    current_user_message_id: dict[str, Optional[str]] = {"id": None}

    def _remember_tool_args(evt: dict[str, Any]) -> None:
        """
        Best-effort pull of (tool_name, path) for snapshot bookkeeping.
        Looks at toolcall_end (full toolCall object) and tool_execution_start
        (carries args) — whichever fires.
        """
        sub = evt.get("assistantMessageEvent") or {}
        if sub.get("type") == "toolcall_end":
            tc = sub.get("toolCall") or {}
            tid = tc.get("id")
            if isinstance(tid, str):
                args = tc.get("arguments") or {}
                pending_tool_calls[tid] = {
                    "name": str(tc.get("name") or "tool"),
                    "path": str(args.get("path") or args.get("file_path") or ""),
                }
            return

        if evt.get("type") in ("tool_execution", "tool_execution_start"):
            tid = evt.get("toolCallId")
            if isinstance(tid, str):
                args = evt.get("args") or evt.get("arguments") or {}
                if not isinstance(args, dict):
                    args = {}
                prev = pending_tool_calls.get(tid, {})
                pending_tool_calls[tid] = {
                    "name": str(evt.get("toolName") or prev.get("name") or "tool"),
                    "path": str(
                        args.get("path")
                        or args.get("file_path")
                        or prev.get("path")
                        or ""
                    ),
                }

    async def _maybe_snapshot(evt: dict[str, Any]) -> None:
        """On successful tool_execution_end, snapshot the workspace."""
        if evt.get("type") not in ("tool_execution_end", "tool_result"):
            return
        if evt.get("isError"):
            return
        tid = evt.get("toolCallId")
        if not isinstance(tid, str):
            return
        meta = pending_tool_calls.pop(tid, {})
        try:
            await shadow.snapshot_after_tool_call(
                tool_call_id=tid,
                tool_name=meta.get("name") or str(evt.get("toolName") or "tool"),
                path=meta.get("path") or "",
                user_message_id=current_user_message_id["id"],
            )
        except Exception as exc:
            print(
                f"[ws {session_id}] shadow-git snapshot failed for {tid}: {exc}",
                file=sys.stderr,
            )

    def _maybe_track_bg_process(evt: dict[str, Any]) -> None:
        """
        React to `process` (from @aliou/pi-processes) tool results.

        - action=start, success=true → register a tailer; user gets live output.
        - action=kill, success=true  → mark our local record as killed; the
          tailer also self-terminates on its next liveness probe.

        The tool_execution_end event carries the tool's full result payload
        in `result.details` (see start.ts:113 — that's where the extension
        emits the ProcessInfo). We grab it from there.
        """
        if evt.get("type") not in ("tool_execution_end", "tool_result"):
            return
        if evt.get("isError"):
            return
        if evt.get("toolName") != "process":
            return
        result = evt.get("result")
        if not isinstance(result, dict):
            return
        details = result.get("details")
        if not isinstance(details, dict):
            return
        action = details.get("action")
        if action == "start" and details.get("success"):
            bg_registry.register_from_start_result(details)
        elif action == "kill" and details.get("success"):
            bg_registry.mark_ended_from_result(details)

    async def pi_to_ws() -> None:
        async for evt in pi.events():
            _remember_tool_args(evt)
            try:
                await ws.send_text(json.dumps(evt, ensure_ascii=False))
            except Exception as exc:
                print(f"[ws {session_id}] send failed: {exc}", file=sys.stderr)
                return
            await _maybe_snapshot(evt)
            _maybe_track_bg_process(evt)

    async def fs_to_ws() -> None:
        while True:
            try:
                msg = await fs_queue.get()
            except asyncio.CancelledError:
                return
            try:
                await ws.send_text(json.dumps(msg, ensure_ascii=False))
            except Exception as exc:
                print(f"[ws {session_id}] fs send failed: {exc}", file=sys.stderr)
                return

    async def bg_to_ws() -> None:
        while True:
            try:
                msg = await bg_queue.get()
            except asyncio.CancelledError:
                return
            try:
                await ws.send_text(json.dumps(msg, ensure_ascii=False))
            except Exception as exc:
                print(f"[ws {session_id}] bg send failed: {exc}", file=sys.stderr)
                return

    async def ws_to_pi() -> None:
        while True:
            try:
                raw = await ws.receive_text()
            except WebSocketDisconnect:
                return
            try:
                command = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json(
                    {
                        "type": "_bridge_error",
                        "message": f"Invalid JSON from client: {raw[:120]!r}",
                    }
                )
                continue
            # Stamp this prompt as the "owner" of any tool calls until the
            # next prompt — that's how revert-turn knows what to undo.
            if command.get("type") == "prompt":
                cid = command.get("id")
                if isinstance(cid, str) and cid:
                    current_user_message_id["id"] = cid
            try:
                await pi.send(command)
            except Exception as exc:
                await ws.send_json(
                    {
                        "type": "_bridge_error",
                        "message": f"Failed to forward command to pi: {exc}",
                    }
                )
                return

    pump_out = asyncio.create_task(pi_to_ws(), name=f"pi_to_ws[{session_id}]")
    pump_fs = asyncio.create_task(fs_to_ws(), name=f"fs_to_ws[{session_id}]")
    pump_bg = asyncio.create_task(bg_to_ws(), name=f"bg_to_ws[{session_id}]")
    pump_in = asyncio.create_task(ws_to_pi(), name=f"ws_to_pi[{session_id}]")

    done, pending = await asyncio.wait(
        {pump_out, pump_fs, pump_bg, pump_in},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

    fs_watcher.unsubscribe(fs_queue)
    bg_registry.unsubscribe(bg_queue)
    await pi.close()
    try:
        await ws.close()
    except Exception:
        pass

    print(f"[ws {session_id}] closed", file=sys.stderr)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
