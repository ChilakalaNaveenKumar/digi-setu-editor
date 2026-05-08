"""
Per-user UI preferences API.

Currently exposes:
  GET   /api/me/prefs                   → snapshot (permission_mode +
                                           routing_default + future keys)
  PATCH /api/me/prefs/permission_mode   { mode: ... }
  PATCH /api/me/prefs/routing_default   { value: "byok" | "cloud" }

We deliberately don't bundle this into /api/usage even though both are
"things about the current user" — usage is polled every few seconds
(billing chip), prefs change ~once. Keeping them separate avoids cache
invalidation churn on the frequently-polled endpoint.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import BYOK_MODE
from services.auth import require_user
from services.billing import CreditLedger
from services.user_prefs import (
    UserPrefs,
    VALID_PERMISSION_MODES,
    user_prefs,
)

router = APIRouter(tags=["prefs"])


class PermissionModeUpdate(BaseModel):
    mode: str = Field(min_length=1, max_length=32)


class RoutingDefaultUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=16)


@router.get("/api/me/prefs")
async def get_my_prefs(user_id: str = Depends(require_user)) -> dict[str, Any]:
    plan_id = CreditLedger.instance().get_plan_id(user_id)
    # When the user has BYOK keys configured we default the routing
    # toggle to "byok" — the whole point of dropping a key in .env is
    # to use it. Otherwise default to "cloud".
    routing_fallback = "byok" if BYOK_MODE else "cloud"
    return {
        "permission_mode": user_prefs().get_permission_mode(user_id, plan_id=plan_id),
        "permission_modes_available": list(VALID_PERMISSION_MODES),
        "routing_default": user_prefs().get_routing_default(
            user_id, fallback=routing_fallback
        ),
        "routing_defaults_available": list(UserPrefs.VALID_ROUTING_DEFAULTS),
        "byok_mode": BYOK_MODE,
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


@router.patch("/api/me/prefs/routing_default")
async def set_routing_default(
    payload: RoutingDefaultUpdate,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Persist the BYOK-vs-Cloud default for new chats. Per-chat picks
    in the model picker still override this — it only kicks in when a
    new chat hasn't pinned a model yet."""
    if payload.value not in UserPrefs.VALID_ROUTING_DEFAULTS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unknown routing default {payload.value!r}; "
                f"allowed: {', '.join(UserPrefs.VALID_ROUTING_DEFAULTS)}"
            ),
        )
    stored = user_prefs().set_routing_default(user_id, payload.value)
    return {"routing_default": stored}
