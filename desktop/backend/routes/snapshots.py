"""
Per-tool-call snapshot endpoints (powered by the per-workspace shadow git).

The actual snapshot recording happens in the chat WS bridge — every
`tool_execution_end` triggers ShadowGit.snapshot_after_tool_call. These
endpoints are read/restore only.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from routes._helpers import workspace_path_for_user_or_404
from services.auth import require_user
from services.shadow_git import ShadowGitRegistry

router = APIRouter(prefix="/api/workspaces/{wsid}", tags=["snapshots"])


@router.get("/snapshots/{tool_call_id}/diff")
async def get_snapshot_diff(
    wsid: str, tool_call_id: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    sg = ShadowGitRegistry.instance().for_workspace(ws)
    payload = sg.diff_for_tool_call(tool_call_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshot recorded for tool_call_id={tool_call_id} in workspace {wsid}",
        )
    return payload


@router.post("/snapshots/{tool_call_id}/restore")
async def restore_snapshot(
    wsid: str, tool_call_id: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    sg = ShadowGitRegistry.instance().for_workspace(ws)
    result = await sg.restore_to_before_tool_call(tool_call_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No snapshot for {tool_call_id}")
    return result


@router.post("/turns/{user_message_id}/revert")
async def revert_turn(
    wsid: str, user_message_id: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    sg = ShadowGitRegistry.instance().for_workspace(ws)
    result = await sg.revert_user_turn(user_message_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"No snapshots for user_message_id={user_message_id}"
        )
    return result
