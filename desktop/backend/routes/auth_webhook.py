"""
Clerk → backend webhook. Cascade-deletes everything a user owns.

Why we need it:
   When a user clicks "Delete account" inside Clerk's `<UserProfile />`,
   Clerk wipes them from its own DB but never touches our data. Without
   this hook we'd leave orphan workspaces, chat logs, and shadow-git
   repos belonging to a dead `sub`. That's a privacy bug *and* a
   storage leak.

Security:
   Webhook bodies arrive over plain HTTPS with no session cookie. We
   verify them via Svix (Clerk's webhook signing layer): every payload
   carries `svix-id`, `svix-timestamp`, `svix-signature`. The
   `CLERK_WEBHOOK_SECRET` env var is the shared secret that produces
   the signature. If verification fails we return 401 — no body,
   no leak.

Idempotency:
   `user.deleted` may be retried. The cascade is idempotent: if a
   workspace id is already gone, `delete_workspace` raises KeyError
   which we swallow.
"""

from __future__ import annotations

import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from config import CLERK_WEBHOOK_SECRET
from services.registry import Registry

router = APIRouter(tags=["auth"])


@router.post("/api/auth/webhook")
async def clerk_webhook(request: Request) -> dict[str, Any]:
    """Single endpoint for every Clerk event we care about (today: user.deleted)."""
    if not CLERK_WEBHOOK_SECRET:
        # Misconfigured prod, or dev mode probing the route. Fail loud.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="webhook receiver not configured",
        )

    raw_body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    if not all(headers.values()):
        raise HTTPException(status_code=400, detail="missing svix-* headers")

    # Lazy import — svix is only needed in prod, and importing it on
    # every dev reload tick costs ~80 ms.
    from svix.webhooks import Webhook, WebhookVerificationError  # type: ignore

    try:
        payload = Webhook(CLERK_WEBHOOK_SECRET).verify(raw_body, headers)
    except WebhookVerificationError as exc:
        print(f"[auth-webhook] signature verify failed: {exc}", file=sys.stderr)
        raise HTTPException(status_code=401, detail="invalid signature")

    if not isinstance(payload, dict):
        return {"ok": True, "ignored": "non-object payload"}

    event_type = payload.get("type")
    data = payload.get("data") or {}
    user_id = data.get("id")

    if event_type == "user.deleted" and isinstance(user_id, str) and user_id:
        deleted = _cascade_delete_user(user_id)
        return {"ok": True, "user_id": user_id, "deleted_workspaces": deleted}

    return {"ok": True, "ignored": event_type or "unknown"}


def _cascade_delete_user(user_id: str) -> int:
    """
    Remove every workspace owned by `user_id`. The Registry's
    `delete_workspace` already cascades to sessions, chat logs,
    shadow-git, bg processes, and PTYs; we just iterate the ids.

    Returns the count of workspaces actually removed.
    """
    reg = Registry.instance()
    wsids = reg.workspaces_owned_by(user_id)
    removed = 0
    for wsid in wsids:
        try:
            reg.delete_workspace(wsid)
            removed += 1
        except KeyError:
            # Already gone (concurrent webhook retry). Idempotent.
            continue
        except Exception as exc:
            print(
                f"[auth-webhook] failed to delete ws={wsid} for user={user_id}: {exc}",
                file=sys.stderr,
            )
    return removed
