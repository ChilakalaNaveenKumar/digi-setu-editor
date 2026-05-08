"""
GET /api/models — model picker catalogue, filtered by the caller's plan.

Drives the dropdown in the chat header. Returning `available: bool` per
model (rather than just hiding the locked ones) lets the SPA show
greyed-out entries with an "Upgrade" affordance — much better UX than
"why isn't Opus in my list?".
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from services.auth import require_user
from services.billing import CreditLedger
from services.models_registry import DEFAULT_MODEL_ID, list_models

router = APIRouter(tags=["models"])


@router.get("/api/models")
async def get_models(user_id: str = Depends(require_user)) -> dict[str, Any]:
    plan_id = CreditLedger.instance().get_plan_id(user_id)
    return {
        "default": DEFAULT_MODEL_ID,
        "plan": plan_id,
        "models": list_models(plan_id),
    }
