"""
Desktop skills endpoints.

A "skill" is a markdown document the LLM consults per turn. The desktop app
exposes three sources:

  - `compile-loop`: auto-generated per workspace based on the user's actual
    machine (typst/quarto versions, files in the folder). Refreshed on a
    weekly cadence and on demand.
  - workspace skills: anything the user drops into
    `<workspace>/.digi-setu/skills/<name>/SKILL.md`.
  - global skills: anything under `~/.digi-setu/skills/<name>/SKILL.md`.

The frontend uses GET /api/skills to populate the `@`-mention autocomplete
and the Skills section in settings. POST upload + DELETE only affect global
skills — workspace skills are user-owned and must be edited directly on
disk (the SPA exposes a "Reveal in Finder" button via Tauri).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services import skills as skills_svc
from services.auth import require_user
from services.registry import Registry

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    body: str = Field(..., min_length=1, max_length=200_000)


def _resolve_workspace(wsid: Optional[str], user_id: str) -> Optional[Path]:
    if not wsid:
        return None
    try:
        rec = Registry.instance().get_workspace(wsid)
    except Exception:
        return None
    if not rec or rec.get("owner_user_id") != user_id:
        return None
    return Path(rec["path"])


@router.get("")
async def list_skills_endpoint(
    workspace_id: Optional[str] = Query(default=None, alias="workspace_id"),
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Return all skills visible to `workspace_id` (or just global if omitted)."""
    workspace = _resolve_workspace(workspace_id, user_id) or Path.home()
    skills = skills_svc.list_skills_summary(workspace)
    return {"skills": skills}


@router.post("")
async def create_skill_endpoint(
    body: SkillCreate, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    try:
        target = skills_svc.upload_global_skill(body.name, body.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "path": str(target)}


@router.delete("/{name}")
async def delete_skill_endpoint(
    name: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    deleted = skills_svc.delete_global_skill(name)
    if not deleted:
        raise HTTPException(status_code=404, detail="skill not found")
    return {"ok": True}


@router.post("/refresh")
async def refresh_workspace_skill_endpoint(
    workspace_id: str = Query(..., alias="workspace_id"),
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Force a re-probe of the user's environment for this workspace."""
    workspace = _resolve_workspace(workspace_id, user_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="unknown workspace")
    profile = await skills_svc.ensure_workspace_skills(workspace, force=True)
    return {
        "ok": True,
        "workspace": str(workspace),
        "typst": profile.typst_version,
        "quarto": profile.quarto_version,
    }
