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

from config import BYOK_MODE
from services.auth import require_user
from services.billing import CreditLedger
from services.byok import route_for_model
from services.models_registry import DEFAULT_MODEL_ID, get_model, list_models

router = APIRouter(tags=["models"])


@router.get("/api/models")
async def get_models(user_id: str = Depends(require_user)) -> dict[str, Any]:
    plan_id = CreditLedger.instance().get_plan_id(user_id)
    entries = list_models(plan_id)
    # Annotate each entry with the routing path it would actually
    # take ("byok" | "cloud") so the model picker can show a badge
    # AND so chat_ws can later reject cloud-only picks for users
    # without an active subscription. The hosted SaaS deployment runs
    # without BYOK credentials so every entry resolves to "cloud";
    # self-hosted operators with BYOK keys in the backend env get
    # "byok" entries for the providers they have keys for.
    for entry in entries:
        spec = get_model(entry["id"])
        entry["route"] = route_for_model(spec) if spec else "cloud"
    return {
        "default": DEFAULT_MODEL_ID,
        "plan": plan_id,
        "byok_mode": BYOK_MODE,
        "models": entries,
    }
