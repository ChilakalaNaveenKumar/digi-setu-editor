"""
Web skills endpoints.

Mirrors the desktop's `/api/skills` surface but stores user uploads under
`<DATA_ROOT>/users/<sanitized_id>/skills/<name>/SKILL.md` instead of in
the user's filesystem. Bundled skills (read-only) live alongside the
project at `<PROJECT_ROOT>/.pi/skills/`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import skills as skills_svc
from services.auth import require_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    body: str = Field(..., min_length=1, max_length=200_000)


@router.get("")
async def list_skills_endpoint(
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Return bundled skills + this Clerk user's uploaded skills."""
    skills = skills_svc.list_skills_summary(user_id)
    return {"skills": skills}


@router.post("")
async def create_skill_endpoint(
    body: SkillCreate, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    try:
        target = skills_svc.upload_user_skill(user_id, body.name, body.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "path": str(target)}


@router.delete("/{name}")
async def delete_skill_endpoint(
    name: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    deleted = skills_svc.delete_user_skill(user_id, name)
    if not deleted:
        raise HTTPException(status_code=404, detail="skill not found")
    return {"ok": True}
