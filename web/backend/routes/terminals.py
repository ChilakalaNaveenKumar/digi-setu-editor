"""
Interactive PTY terminals (xterm.js sessions), scoped to a workspace.

REST: shell-profile discovery is global (host-level), but create/list/kill
all live under `/api/workspaces/{wsid}/terminals`. The actual byte
stream still runs over `/ws/terminal/{term_id}` — the terminal id is a
12-char uuid that the PtyHub looks up across all workspace registries.

Default cwd is the workspace's sandbox path so a fresh shell drops the
user straight into their files.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from models.files import TerminalCreate
from routes._helpers import workspace_path_for_user_or_404
from services.auth import require_user
from services.pty_terminal import PtyHub, discover_shell_profiles

router = APIRouter(tags=["terminals"])


@router.get("/api/terminals/profiles")
async def list_terminal_profiles(
    _user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Host-level shell discovery — same answer regardless of workspace."""
    return {"profiles": discover_shell_profiles()}


@router.get("/api/workspaces/{wsid}/terminals")
async def list_terminals(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_path_for_user_or_404(wsid, user_id)
    reg = PtyHub.instance().for_workspace(wsid)
    return {"terminals": [reg.serialize(t) for t in reg.all()]}


@router.post("/api/workspaces/{wsid}/terminals")
async def create_terminal(
    wsid: str, body: TerminalCreate, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    """Spawn a fresh PTY inside the workspace.

    `cwd` defaults to the workspace path. Callers may pass a relative
    sub-path (resolved against the workspace root); we currently trust
    desktop-mode users with absolute paths but that will be locked down
    in web mode (Phase 5).
    """
    ws_path = workspace_path_for_user_or_404(wsid, user_id)
    shell = (body.shell or "default").strip() or "default"
    cwd = (body.cwd or "").strip() or str(ws_path)
    cols = int(body.cols or 80)
    rows = int(body.rows or 24)
    try:
        term = PtyHub.instance().for_workspace(wsid).create(
            shell=shell, cwd=cwd, cols=cols, rows=rows
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"failed to spawn pty: {exc}")
    return PtyHub.instance().for_workspace(wsid).serialize(term)


@router.delete("/api/workspaces/{wsid}/terminals/{term_id}")
async def delete_terminal(
    wsid: str, term_id: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_path_for_user_or_404(wsid, user_id)
    reg = PtyHub.instance().for_workspace(wsid)
    if not reg.kill(term_id):
        raise HTTPException(status_code=404, detail=f"Unknown terminal: {term_id}")
    reg.remove(term_id)
    return {"ok": True}
