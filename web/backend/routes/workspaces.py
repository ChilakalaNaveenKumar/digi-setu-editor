"""
Workspace catalogue endpoints.

The Registry owns the actual create/list/rename/delete logic. This module
maps it to HTTP, validates input via pydantic, and scopes every operation
to the caller's user_id (Clerk in prod, "dev" in dev mode).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from models.workspace import WorkspaceCreate, WorkspaceRename
from routes._helpers import workspace_for_user_or_404
from services.auth import require_user
from services.registry import Registry

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("")
async def list_workspaces(user_id: str = Depends(require_user)) -> dict[str, Any]:
    return {"workspaces": Registry.instance().list_workspaces(owner_user_id=user_id)}


@router.post("")
async def create_workspace(
    payload: WorkspaceCreate, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    """
    Allocate a sandbox under web/data/workspaces/. `path` on the payload
    is ignored; `name` defaults to "Untitled workspace".
    """
    name = (payload.name or "").strip()
    return Registry.instance().create_web_workspace(name=name, owner_user_id=user_id)


@router.patch("/{wsid}")
async def rename_workspace(
    wsid: str, payload: WorkspaceRename, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    try:
        return Registry.instance().rename_workspace(wsid, payload.name.strip())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown workspace: {wsid}")


@router.delete("/{wsid}")
async def delete_workspace(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    try:
        rec = Registry.instance().delete_workspace(wsid)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown workspace: {wsid}")
    return {"ok": True, "workspace": rec}
