"""
Frontend-facing config dump.

Returns:
    auth_required           bool   — when False the SPA skips Clerk init
    clerk_publishable_key   str    — frontend boot key (or "" in dev mode)
    byok_mode               bool   — operator wired their own AI keys
    byok_keys               list   — names of detected BYOK env vars

This endpoint is **unauthenticated by design** so the SPA can boot and
render its login screen without a chicken-and-egg problem.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from config import (
    AUTH_REQUIRED,
    BYOK_MODE,
    CLERK_PUBLISHABLE_KEY,
    DETECTED_BYOK_KEYS,
)

router = APIRouter()


@router.get("/api/config")
async def get_config() -> dict[str, Any]:
    return {
        "auth_required": AUTH_REQUIRED,
        "clerk_publishable_key": CLERK_PUBLISHABLE_KEY,
        # `byok_mode=true` tells the SPA the operator has dropped their
        # own AI keys into the backend env. The picker / chat views use
        # it to:
        #   - skip the "sign in" gate (no Clerk needed)
        #   - render a small "Using your own key" chip in the header
        #   - hide the Upgrade / billing CTAs (they pay their provider
        #     directly, our subscription is irrelevant)
        # Empty list when BYOK is off; tells which key kinds were
        # detected when on (for the chip's tooltip).
        "byok_mode": BYOK_MODE,
        "byok_keys": DETECTED_BYOK_KEYS if BYOK_MODE else [],
    }
