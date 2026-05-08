"""
User feedback intake.

Why we ship a real backend route and not a mailto: link in the SPA:
   - mailto: leaks the user's email client config and breaks on web
     mobile;
   - it gives no audit trail (we want to read every message);
   - it can't be rate-limited (a public mailto is a free spam vector).

What this does today (v1):
   - Append every submission to data/feedback.jsonl with the caller's
     user_id, the user-agent, and an ISO timestamp.
   - Mirror to stderr so it shows up in `journalctl -u pi.service`
     during the early-feedback phase.

What it does NOT do yet (and why):
   - Doesn't actually send email. We'll wire SES / Postmark after the
     first real users land — no point standing up an outbound MTA for
     zero traffic.
   - Doesn't rate-limit. The token-bucket layer that lands in Phase 5
     will protect this endpoint along with the LLM call path.

Authentication:
   Required. Anonymous feedback is a spam funnel; if you can sign up
   to leave it, you can also be banned for abusing it.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from config import DATA_ROOT, FEEDBACK_EMAIL_TO
from services.auth import require_user
from services.rate_limit import RateLimiter

router = APIRouter(tags=["feedback"])

_FEEDBACK_LOG = DATA_ROOT / "feedback.jsonl"
_MAX_MESSAGE_CHARS = 4000


class FeedbackPayload(BaseModel):
    """User-submitted message body. `category` is freeform (we use it
    purely for triage; the frontend currently sends "bug" | "idea"
    | "other" but we don't enforce that here so the categories can
    evolve without a backend deploy)."""

    message: str = Field(..., min_length=1, max_length=_MAX_MESSAGE_CHARS)
    category: str = Field(default="other", max_length=32)
    contact_email: str | None = Field(default=None, max_length=320)


@router.post("/api/feedback")
async def submit_feedback(
    payload: FeedbackPayload,
    request: Request,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Record a feedback entry. Returns the durable id we assigned."""
    # Rate-limit *before* parsing — keeps a spam loop cheap.
    RateLimiter.instance().check(user_id, "feedback")

    msg = payload.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is empty after trimming")

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "user_agent": request.headers.get("user-agent", ""),
        "ip": request.client.host if request.client else "",
        "category": payload.category[:32] or "other",
        "message": msg,
        "contact_email": (payload.contact_email or "").strip()[:320] or None,
        "destination": FEEDBACK_EMAIL_TO,
    }

    _FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _FEEDBACK_LOG.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"[feedback] failed to append jsonl: {exc}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="failed to record feedback")

    print(
        f"[feedback] {entry['category']} from {user_id}: {msg[:120]!r}",
        file=sys.stderr,
    )
    return {"ok": True, "destination": FEEDBACK_EMAIL_TO}
