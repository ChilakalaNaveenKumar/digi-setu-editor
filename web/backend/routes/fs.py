"""
Filesystem mutations on a workspace's user-files dir.

Every endpoint is sandboxed via `services.paths.safe_path` (called from
file_ops). The agent's pi subprocess uses these same helpers for its own
write/edit tools, so traversal protection is enforced in one place.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from models.files import FileWrite, FolderCreate, PathCopy, PathMove, PathRename
from routes._helpers import fs_error, workspace_path_for_user_or_404
from services.auth import require_user
from services.file_ops import (
    copy_path,
    create_file,
    create_folder,
    delete_path,
    move_path,
    rename_path,
)

router = APIRouter(prefix="/api/workspaces/{wsid}/fs", tags=["fs"])


@router.post("/file")
async def fs_create_file(
    wsid: str, payload: FileWrite, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return create_file(ws, payload.path, payload.content, overwrite=payload.overwrite)
    except (PermissionError, FileExistsError, IsADirectoryError, ValueError, FileNotFoundError) as exc:
        raise fs_error(exc)


@router.post("/folder")
async def fs_create_folder(
    wsid: str, payload: FolderCreate, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return create_folder(ws, payload.path)
    except (PermissionError, FileExistsError, ValueError) as exc:
        raise fs_error(exc)


@router.delete("/path")
async def fs_delete(
    wsid: str, path: str = Query(...), user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return delete_path(ws, path)
    except (PermissionError, FileNotFoundError) as exc:
        raise fs_error(exc)


@router.post("/rename")
async def fs_rename(
    wsid: str, payload: PathRename, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return rename_path(ws, payload.from_, payload.to)
    except (PermissionError, FileNotFoundError, FileExistsError, ValueError) as exc:
        raise fs_error(exc)


@router.post("/copy")
async def fs_copy(
    wsid: str, payload: PathCopy, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return copy_path(ws, payload.from_, payload.to)
    except (PermissionError, FileNotFoundError, ValueError) as exc:
        raise fs_error(exc)


@router.post("/move")
async def fs_move(
    wsid: str, payload: PathMove, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return move_path(ws, payload.from_, payload.to)
    except (PermissionError, FileNotFoundError, ValueError) as exc:
        raise fs_error(exc)
