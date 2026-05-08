"""
Shared route helpers: ownership-aware workspace lookup + OS-error mapping.

Why route-layer enforcement (instead of inside the Registry):

  - Tests + admin tooling can read any row without a fake user.
  - Auth concerns stay in one layer (`services.auth` for identity,
    `routes._helpers` for authorisation), keeping the data layer pure.

Every public route that touches a workspace MUST go through
`workspace_for_user_or_404`. A bare `Registry.get_workspace(wsid)` in a
route handler is a multi-tenant leak.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.registry import Registry


def workspace_for_user_or_404(wsid: str, user_id: str) -> dict[str, Any]:
    """
    Look up a workspace by id, scoped to `user_id`.

    Returns a copy of the record. Raises 404 in two cases:
      - the workspace is missing entirely
      - the workspace exists but is owned by someone else

    We deliberately collapse "not found" and "not yours" into the same
    404 so a hostile client can't use the API to enumerate workspace
    ids belonging to other users.
    """
    rec = Registry.instance().get_workspace(wsid)
    if not rec or rec.get("owner_user_id") != user_id:
        raise HTTPException(status_code=404, detail=f"unknown workspace: {wsid}")
    return rec


def workspace_path_for_user_or_404(wsid: str, user_id: str) -> Path:
    """Convenience wrapper that returns just the on-disk path."""
    return Path(workspace_for_user_or_404(wsid, user_id)["path"])


def session_for_user_or_404(sid: str, user_id: str) -> dict[str, Any]:
    """
    Look up a session by id, scoped to `user_id`. The owner check is
    transitive: the session is reachable iff its parent workspace is.
    Same 404-collapse rationale as above.
    """
    reg = Registry.instance()
    sess = reg.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail=f"unknown session: {sid}")
    ws = reg.get_workspace(sess.get("workspace_id", ""))
    if not ws or ws.get("owner_user_id") != user_id:
        raise HTTPException(status_code=404, detail=f"unknown session: {sid}")
    return sess


def fs_error(exc: BaseException) -> HTTPException:
    """Map common filesystem errors to typed HTTP responses."""
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc) or "permission denied")
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc) or "not found")
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=409, detail=str(exc) or "already exists")
    if isinstance(exc, IsADirectoryError):
        return HTTPException(status_code=400, detail=str(exc) or "is a directory")
    if isinstance(exc, NotADirectoryError):
        return HTTPException(status_code=400, detail=str(exc) or "not a directory")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc) or "bad request")
    return HTTPException(status_code=500, detail=str(exc) or "internal error")
