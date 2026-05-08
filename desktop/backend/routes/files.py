"""
Read-only views over a workspace's user-files dir: tree, content, raw bytes.

Mutating endpoints live in `routes/fs.py` (POST/DELETE) — keeping the
read-only surface separate makes it trivial to add e.g. a "read-only
viewer" mode for shared sessions later.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from routes._helpers import fs_error, workspace_path_for_user_or_404
from services.auth import require_user
from services.file_ops import list_tree, read_file, stream_raw_path

router = APIRouter(prefix="/api/workspaces/{wsid}/files", tags=["files"])


@router.get("")
async def get_tree(wsid: str, user_id: str = Depends(require_user)) -> dict[str, Any]:
    return {"items": list_tree(workspace_path_for_user_or_404(wsid, user_id))}


@router.get("/content")
async def get_content(
    wsid: str, path: str = Query(...), user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return read_file(ws, path)
    except (PermissionError, FileNotFoundError, IsADirectoryError, OSError) as exc:
        raise fs_error(exc)


@router.get("/raw")
async def get_raw(
    wsid: str, path: str = Query(...), user_id: str = Depends(require_user)
) -> FileResponse:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        abs_path, mime = stream_raw_path(ws, path)
    except (PermissionError, FileNotFoundError, IsADirectoryError) as exc:
        raise fs_error(exc)
    return FileResponse(
        path=str(abs_path),
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{abs_path.name}"'},
    )
