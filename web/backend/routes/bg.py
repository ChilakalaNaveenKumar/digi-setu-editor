"""
Background-process control plane, scoped to a workspace.

Every workspace gets its own BackgroundProcessRegistry (resolved through
the BackgroundProcessHub). Listing and killing therefore require a wsid
in the URL — there is no longer a global view across workspaces. This
fixes the multi-tenant leak the previous global singleton had: a kill
in workspace A could otherwise hit workspace B's pid.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from routes._helpers import workspace_for_user_or_404
from services.auth import require_user
from services.bg_processes import BackgroundProcessHub

router = APIRouter(tags=["bg"])


@router.get("/api/workspaces/{wsid}/bg")
async def list_bg_processes(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    return {"processes": BackgroundProcessHub.instance().for_workspace(wsid).list()}


@router.post("/api/workspaces/{wsid}/bg/{process_id}/kill")
async def kill_bg_process(
    wsid: str, process_id: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    reg = BackgroundProcessHub.instance().for_workspace(wsid)
    result = await reg.kill(process_id)
    if not result.get("ok") and result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail=f"Unknown bg process: {process_id}")
    return result
