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

    # Sent right before closing a duplicate-tab WebSocket (code 4409) so
    # clients that lose the close code still show the right message.
    "session_kicked":
        "Another tab has this chat — reload this page to reconnect. "
        "(Only one live connection per chat is allowed so your session stays consistent.)",

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


# Codes that are normal user / session lifecycle events, NOT operational
# problems. They were previously logged via `log_error` (`[err]` prefix),
# which made dev / prod stderr look like the system was constantly on
# fire — every Stop button press surfaced as `[err] code=aborted`,
# every duplicate-tab refresh as `[err] code=session_kicked`. Logging
# them as `[info]` keeps the audit trail intact (we still see them when
# debugging) but they don't pollute error dashboards or trigger alert
# thresholds. The user explicitly called this out as "soo many errors
# spawning on the chat" / "even when reloading … flickering occurs"
# despite the actual session being healthy.
_LIFECYCLE_CODES: Final[frozenset[str]] = frozenset({
    # User pressed the Stop button (or the WS dropped mid-stream and
    # the watchdog fired). Not an error — that's the expected control
    # path for "I changed my mind".
    "aborted",
    # Same user opened the chat in a second tab and we kicked the
    # first one. Expected single-writer behaviour, surfaced to the
    # original tab as a clear "another tab has this chat" card.
    "session_kicked",
})


def _emit(level: str, code: str, ctx: dict[str, Any], exc: BaseException | None) -> None:
    """Shared formatter for `log_info` / `log_error` — single grep-able
    one-liner with consistent field ordering."""
    bits: list[str] = [f"ts={int(time.time())}", f"code={code}"]
    for k in ("session_id", "user_id", "where"):
        v = ctx.pop(k, None)
        if v is None:
            continue
        # Field-name normalisation: callers pass session_id / user_id
        # but the on-the-wire labels stay short for grep-friendliness.
        short = "session" if k == "session_id" else ("user" if k == "user_id" else k)
        bits.append(f"{short}={v}")
    if exc is not None:
        bits.append(f"exc={type(exc).__name__}({exc!r})")
    for k, v in ctx.items():
        bits.append(f"{k}={v!r}")
    print(f"[{level}] {' '.join(bits)}", file=sys.stderr)

    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)


def log_info(
    code: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    where: str | None = None,
    **ctx: Any,
) -> None:
    """Emit a routine lifecycle event — same one-liner shape as
    `log_error` but tagged `[info]` so dashboards / alerting that key
    on `[err]` ignore it. Use this for normal user actions (Stop
    pressed, duplicate-tab kicked, …) that we still want grep-able
    in the audit trail but that aren't operational problems."""
    _emit("info", code, dict(ctx, session_id=session_id, user_id=user_id, where=where), None)


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

    Routine lifecycle codes (`aborted`, `session_kicked`, …) are
    auto-demoted to `[info]` so dashboards keying on `[err]` don't
    light up on every Stop button press. See `_LIFECYCLE_CODES`.
    """
    if code in _LIFECYCLE_CODES and exc is None:
        log_info(code, session_id=session_id, user_id=user_id, where=where, **ctx)
        return
    _emit("err", code, dict(ctx, session_id=session_id, user_id=user_id, where=where), exc)
