"""
Per-user UI preferences API.

Currently exposes:
  GET  /api/me/prefs            → snapshot (permission_mode + future keys)
  PATCH /api/me/prefs/permission_mode {mode: ...}

We deliberately don't bundle this into /api/usage even though both are
"things about the current user" — usage is polled every few seconds
(billing chip), prefs change ~once. Keeping them separate avoids cache
invalidation churn on the frequently-polled endpoint.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.auth import require_user
from services.billing import CreditLedger
from services.user_prefs import VALID_PERMISSION_MODES, user_prefs

router = APIRouter(tags=["prefs"])


class PermissionModeUpdate(BaseModel):
    mode: str = Field(min_length=1, max_length=32)


@router.get("/api/me/prefs")
async def get_my_prefs(user_id: str = Depends(require_user)) -> dict[str, Any]:
    plan_id = CreditLedger.instance().get_plan_id(user_id)
    return {
        "permission_mode": user_prefs().get_permission_mode(user_id, plan_id=plan_id),
        "permission_modes_available": list(VALID_PERMISSION_MODES),
        "stored": user_prefs().snapshot(user_id),
    }


@router.patch("/api/me/prefs/permission_mode")
async def set_permission_mode(
    payload: PermissionModeUpdate,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    if payload.mode not in VALID_PERMISSION_MODES:
        # We don't silently clamp here — a 400 makes it obvious to the
        # frontend that its picker drifted from the backend's allowed
        # list (e.g. after a deploy that adds a new mode).
        raise HTTPException(
            status_code=400,
            detail=(
                f"unknown permission mode {payload.mode!r}; "
                f"allowed: {', '.join(VALID_PERMISSION_MODES)}"
            ),
        )
    stored = user_prefs().set_permission_mode(user_id, payload.mode)
    return {"permission_mode": stored}
