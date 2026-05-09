"""
Frontend-facing config dump.

Returns:
    mode                    "web" | "desktop"  — picker UX branches on this
    auth_required           bool   — when False the SPA skips Clerk init
    clerk_publishable_key   str    — frontend boot key (or "" in dev mode)
    byok_mode               bool   — desktop has user-provided AI keys
    byok_keys               list[str] — detected BYOK env vars (for chip tooltip)
    requires_setup          bool   — desktop has neither a cached Clerk
                                     session nor any BYOK keys; the SPA
                                     should land on the Welcome / setup
                                     screen until one of those is true.
    clerk_tenant            "prod" | "test" | "unknown" — which Clerk
                                     tenant the sidecar is wired to.
                                     "test" against api.digi-setu.com
                                     means JWTs will be 401-rejected
                                     by the cloud and the user can't
                                     fetch their real plan; the SPA
                                     surfaces a banner in that case.
    cloud_api_base          str    — the cloud HTTP base the sidecar
                                     forwards billing/usage reads to.
                                     Used by the SPA's tenant-mismatch
                                     banner.

This endpoint is **unauthenticated by design** so the SPA can boot and
render its login screen without a chicken-and-egg problem.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

# IMPORTANT: import the module — not the constants — so we observe
# live updates from services/dotenv_watcher.py when the user edits
# ~/.digi-setu/.env. Using `from config import BYOK_MODE` would
# capture the boot-time value and the live-reload mechanism would
# silently fail (exactly what the user complained about: "I dropped
# the key and nothing happens until I restart").
import config  # noqa: E402

router = APIRouter()


def _requires_setup() -> bool:
    """
    Desktop is in 'setup required' state when the user has neither
    signed in (no cached Clerk session) NOR dropped any BYOK keys
    into ~/.digi-setu/.env. In this state the SPA renders a Welcome
    screen by default and the chat surface shows an inline "sign in
    or add a key" gate; routes themselves are not blocked.

    Web mode never sets this flag — the existing auth-required gate
    handles it there.
    """
    if config.DEPLOY_MODE != "desktop":
        return False
    if config.BYOK_MODE:
        return False
    # Lazy-import to avoid touching desktop_auth at module load time
    # (which would re-trigger _bootstrap_env side effects in tests).
    try:
        from routes.desktop_auth import get_cached_desktop_session
    except ImportError:
        return True
    return get_cached_desktop_session() is None


@router.get("/api/config")
async def get_config() -> dict[str, Any]:
    return {
        "mode": config.DEPLOY_MODE,
        "auth_required": config.AUTH_REQUIRED,
        "clerk_publishable_key": config.CLERK_PUBLISHABLE_KEY,
        # `byok_mode=true` tells the SPA the user has dropped their
        # own AI keys into ~/.digi-setu/.env. The picker / chat
        # views use it to:
        #   - skip the "sign in" gate (no Clerk needed)
        #   - render a small "Using your own key" chip in the header
        #   - hide the Upgrade / billing CTAs (they pay their
        #     provider directly, our subscription is irrelevant)
        # Empty list when BYOK is off; tells which key kinds were
        # detected when on (for the chip's tooltip).
        "byok_mode": config.BYOK_MODE,
        "byok_keys": list(config.DETECTED_BYOK_KEYS) if config.BYOK_MODE else [],
        "requires_setup": _requires_setup(),
        # See the docstring at the top of this module — surfaced so
        # the SPA can render a "your desktop is signed into the test
        # Clerk tenant; the cloud only accepts prod sessions, so plan
        # / activity / billing will look wrong" banner instead of
        # silently showing a stale Free snapshot.
        "clerk_tenant": getattr(config, "CLERK_TENANT_KIND", "unknown"),
        "cloud_api_base": config.PI_CLOUD_API_BASE,
    }
