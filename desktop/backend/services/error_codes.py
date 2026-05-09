"""
Central error-code table for backend → frontend communication.

Principle (locked in by the user, not negotiable): the UI must NEVER
see raw exception strings, internal IDs, file paths, or technical
jargon ("sidecar", "bridge", "pi", "BYOK", "relay", "Vertex").
Instead the backend emits a stable error CODE and a friendly,
localisation-ready MESSAGE; the full technical detail (exception,
traceback, raw context) is logged to stderr only, where operators
and developers can inspect it.

Usage at error sites:

    from services.error_codes import bridge_error, log_error

    try:
        await spawn_pi(...)
    except Exception as exc:
        log_error("internal", session_id=session_id, exc=exc, where="spawn_pi")
        await ws.send_json(bridge_error("internal"))
        await ws.close()
        return

The frontend receives:

    { "type": "_bridge_error", "code": "internal",
      "message": "Something went wrong. Please try again." }

…while the backend log captures the full picture:

    [err] code=internal session=s_oMD… exc=KeyError('x') where=spawn_pi
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import Any, Final


# ── Error code → user-facing message ─────────────────────────────────
# Keep messages SHORT, neutral, and free of technical jargon. Action
# guidance ("Please sign in", "Please try again") lives here too so
# a single grep covers all UI strings emitted by the WS gate.
#
# Frontend has a matching i18n table; the message in this dict is
# the English fallback when the SPA hasn't loaded its locale yet.
_MESSAGES: Final[dict[str, str]] = {
    # ── Auth / setup ──────────────────────────────────────────────
    "setup_required":
        "Please sign in or add an AI key to start chatting.",
    "session_expired":
        "Your sign-in expired. Please sign in again.",

    # ── Resource lookup ───────────────────────────────────────────
    "session_unknown":
        "This chat is no longer available.",
    "workspace_missing":
        "This folder is no longer available.",

    # ── Network / runtime ─────────────────────────────────────────
    "network":
        "Connection lost. Please try again.",
    "timeout":
        "This is taking longer than expected. Please try again.",
    "rate_limit":
        "You're going a little fast. Please slow down and try again.",
    "capacity":
        "Our servers are busy right now. Please try again in a moment.",

    # ── Quotas / billing (no internal numbers leaked here — the
    # frontend renders a richer prompt with the usage page link) ─
    "quota_exceeded":
        "You've used up your plan's allowance for now. Please upgrade or try again later.",
    "storage_full":
        "This folder is full. Please free up some space and try again.",

    # ── Cancellation (user-initiated, not really an error) ────────
    "aborted":
        "Stopped.",

    # ── Catch-all ─────────────────────────────────────────────────
    "internal":
        "Something went wrong. Please try again.",
}


def message_for(code: str) -> str:
    """Return the friendly user-facing message for a code, falling back
    to the catch-all if the code is unrecognised."""
    return _MESSAGES.get(code, _MESSAGES["internal"])


def bridge_error(code: str, **extra: Any) -> dict[str, Any]:
    """
    Build the JSON payload sent over the WS as `_bridge_error`. Extra
    fields (e.g. `bucket` for rate-limit details, `model` for an
    upgrade prompt) are merged in shallowly. Critically, `extra`
    must NEVER carry user-uploaded paths or raw exception strings —
    those belong in `log_error` only.
    """
    payload: dict[str, Any] = {
        "type": "_bridge_error",
        "code": code,
        "message": message_for(code),
    }
    payload.update(extra)
    return payload


def log_error(
    code: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    exc: BaseException | None = None,
    where: str | None = None,
    **ctx: Any,
) -> None:
    """
    Emit a structured one-liner to stderr capturing everything we
    redacted from the UI message. Format is intentionally grep-able
    and stable so log aggregators can pivot on `code=`.

    When `exc` is given, the full traceback is appended on the next
    lines so we don't have to chase repro steps later.
    """
    bits: list[str] = [
        f"ts={int(time.time())}",
        f"code={code}",
    ]
    if session_id:
        bits.append(f"session={session_id}")
    if user_id:
        bits.append(f"user={user_id}")
    if where:
        bits.append(f"where={where}")
    if exc is not None:
        bits.append(f"exc={type(exc).__name__}({exc!r})")
    for k, v in ctx.items():
        bits.append(f"{k}={v!r}")
    print(f"[err] {' '.join(bits)}", file=sys.stderr)

    if exc is not None:
        # Full traceback on subsequent lines so log grouping by `[err]`
        # picks up the headline without repeating the stack for every
        # similar failure.
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
