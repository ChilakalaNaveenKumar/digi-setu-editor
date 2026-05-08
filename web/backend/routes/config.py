"""
Frontend-facing config dump.

Returns:
    mode                    "web" | "desktop"  — picker UX branches on this
    auth_required           bool   — when False the SPA skips Clerk init
    clerk_publishable_key   str    — frontend boot key (or "" in dev mode)

This endpoint is **unauthenticated by design** so the SPA can boot and
render its login screen without a chicken-and-egg problem.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from config import AUTH_REQUIRED, CLERK_PUBLISHABLE_KEY, DEPLOY_MODE

router = APIRouter()


@router.get("/api/config")
async def get_config() -> dict[str, Any]:
    return {
        "mode": DEPLOY_MODE,
        "auth_required": AUTH_REQUIRED,
        "clerk_publishable_key": CLERK_PUBLISHABLE_KEY,
    }
