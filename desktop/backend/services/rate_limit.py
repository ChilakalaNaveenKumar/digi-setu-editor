"""
Per-user rate limiting + token quotas.

We expose **two primitives**, both stored in-process for v1:

  TokenBucket   — classic capacity + refill_per_sec pair, used for
                  burst-tolerant counts (HTTP requests, WS opens,
                  prompts per minute).
  DailyQuota    — calendar-day counter that resets at UTC midnight,
                  used for LLM token budgets.

Why in-memory and not Redis: a single VM serves the entire site for
v1. When we go multi-VM the swap is a one-method call on each class
(`_acquire`/`_consume`) — the public surface stays identical so
route handlers don't change.

Public surface:

    RateLimiter.instance().check(user_id, "ws.connect")
        → None on success, raises HTTPException(429) on overflow

    RateLimiter.instance().consume_tokens(user_id, n)
        → True if charged; False if today's budget is exhausted

    RateLimiter.instance().usage(user_id)
        → snapshot dict for /api/usage (frontend can show "you've used
          X / Y tokens today")

Configuration: every limit is read from an env var with a sane default
(see top of file). Operators can crank them up/down without a code
change. Setting a limit to 0 DISABLES it (useful for the dev loop).
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException


# ── tunables (env-overridable) ────────────────────────────────────
def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


# Bucket spec: (capacity, refill_per_second).
# Capacity is the burst the user can do back-to-back; refill_per_second
# is the steady-state allowance once the burst is spent.
#
# Why connection-shaped buckets (ws.connect / pi.spawn) are NOT
# rate-limited on desktop — and even on web are very generous:
#
#   The user doesn't choose to "reconnect", the SYSTEM does:
#     * laptop sleep/wake breaks the TCP socket → bridge reconnects
#     * NAT idle timeout drops the socket   → bridge reconnects
#     * our own sidecar watchdog respawns   → bridge reconnects
#     * the user closes their laptop lid for an hour → reconnects
#   None of those are actions the user can throttle. Charging a
#   token bucket against them just turns a transient network
#   condition into a "you're connecting too fast" error wall the
#   user has no way to clear without waiting out a refill window.
#
#   The right place to rate-limit is the ACTUAL user action:
#   sending a prompt (`chat.message`). That bucket stays tight.
#
# Defaults are set so a real user never hits ``ws.connect`` /
# ``pi.spawn`` in the course of normal use, even with hourly sleep
# cycles or our own respawn loop. Operators worried about abuse
# can crank them down via env. Setting capacity=0 disables a
# bucket entirely (already-supported in `_bucket()`).
def _is_desktop_mode() -> bool:
    return os.environ.get("PI_MODE", "web").strip().lower() == "desktop"


# WS upgrades. Each reconnect (sleep/wake, watchdog respawn) costs
# one token, so capacity must comfortably cover the worst-case
# reconnect storm. On desktop the limit is effectively off (1000
# capacity, 60/sec refill) — desktop is single-user so there's
# nothing to abuse. On web we keep a healthy ceiling (200 burst,
# 60/min refill) so a panicking SPA can't DoS the upgrade path.
_WS_CONNECT_DEFAULT_CAP = 1000 if _is_desktop_mode() else 200
_WS_CONNECT_DEFAULT_RATE = 60 if _is_desktop_mode() else 60  # per minute

# Pi subprocess spawn — was the real culprit behind "you're
# connecting too fast" loops. Each reconnect spawns one fresh pi.
# Old default was 10 cap / 1 per minute refill — a user with a
# laggy network or a sleeping laptop blew through that in a few
# cycles. Bump WAY up. On desktop, effectively disabled. On web,
# 200 burst / 60 per minute refill (3.3/sec) — pi spawn really
# is more expensive than a WS open so we keep SOMETHING in place
# to bound damage from a malicious tight loop on the public
# endpoint, but the real-user reconnect path never trips it.
_PI_SPAWN_DEFAULT_CAP = 1000 if _is_desktop_mode() else 200
_PI_SPAWN_DEFAULT_RATE = 60 if _is_desktop_mode() else 60  # per minute

_BUCKETS: dict[str, tuple[int, float]] = {
    # WebSocket upgrades. See the long comment above for rationale —
    # this is a connection mechanic, not a user action.
    "ws.connect":  (_int_env("RL_WS_CONNECT_CAPACITY", _WS_CONNECT_DEFAULT_CAP),
                    _int_env("RL_WS_CONNECT_PER_MIN", _WS_CONNECT_DEFAULT_RATE) / 60.0),
    # Pi subprocess spawn — see comment above. Was the choke point
    # producing 4429 close codes on otherwise-healthy reconnects.
    "pi.spawn":    (_int_env("RL_PI_SPAWN_CAPACITY", _PI_SPAWN_DEFAULT_CAP),
                    _int_env("RL_PI_SPAWN_PER_MIN", _PI_SPAWN_DEFAULT_RATE) / 60.0),
    # User prompts within a session — THIS is the real "user action"
    # bucket. Stays as-is (20 burst, 30/min refill).
    "chat.message": (_int_env("RL_CHAT_MSG_CAPACITY", 20),
                     _int_env("RL_CHAT_MSG_PER_MIN", 30) / 60.0),
    # Feedback submissions (anti-spam).
    "feedback":    (_int_env("RL_FEEDBACK_CAPACITY", 3),
                    _int_env("RL_FEEDBACK_PER_HOUR", 5) / 3600.0),
}

# Daily LLM token budget. Charged from the `message_end` event
# pi emits (input + output + cache reads/writes summed). Set to a
# positive integer to enable defence-in-depth on top of the credit
# cap; default 0 = OFF because the per-month dollar credit (in
# services/billing.py) is the source of truth and a second daily
# token gate confused users who'd already paid for headroom. Operators
# who want belt-and-suspenders for abuse mitigation should set
# RL_DAILY_TOKEN_BUDGET=10_000_000 (or whatever fits their VM size).
_DAILY_TOKEN_BUDGET = _int_env("RL_DAILY_TOKEN_BUDGET", 0)


def _is_admin_user(user_id: str) -> bool:
    """Lazy import so rate_limit stays import-cheap. Returns False on
    any auth failure so a Clerk outage can't accidentally unlock
    everyone (or lock everyone out via the wrong direction)."""
    if not user_id:
        return False
    try:
        from services.auth import is_admin_user
        return is_admin_user(user_id)
    except Exception:
        return False


class _TokenBucket:
    """Single user × single bucket key. Caller holds the lock."""

    __slots__ = ("capacity", "refill_per_sec", "tokens", "updated")

    def __init__(self, capacity: int, refill_per_sec: float) -> None:
        self.capacity = float(capacity)
        self.refill_per_sec = refill_per_sec
        # Start full so a fresh user immediately gets the burst.
        self.tokens = float(capacity)
        self.updated = time.monotonic()

    def try_take(self, n: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
            self.updated = now
        if self.tokens + 1e-9 < n:
            return False
        self.tokens -= n
        return True

    def retry_after_seconds(self, n: float = 1.0) -> float:
        if self.refill_per_sec <= 0:
            return 0.0
        deficit = max(0.0, n - self.tokens)
        return deficit / self.refill_per_sec


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class RateLimiter:
    """Process-wide singleton. Per-user state lives in plain dicts.

    Memory shape:
        self._buckets[user_id][bucket_key] -> _TokenBucket
        self._tokens[user_id]              -> {"day": "YYYY-MM-DD",
                                                "used": int,
                                                "messages": int}

    The state is intentionally lossy across restarts: rate limits are
    a fairness signal, not a billing system. If you want durable
    accounting, ship the events to a sink (Phase 6).
    """

    _instance: Optional["RateLimiter"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "RateLimiter":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, dict[str, _TokenBucket]] = {}
        self._tokens: dict[str, dict[str, Any]] = {}

    # ── bucket access ────────────────────────────────────────────
    def _bucket(self, user_id: str, key: str) -> Optional[_TokenBucket]:
        spec = _BUCKETS.get(key)
        if spec is None or spec[0] <= 0:
            return None
        per_user = self._buckets.setdefault(user_id, {})
        b = per_user.get(key)
        if b is None:
            b = _TokenBucket(spec[0], spec[1])
            per_user[key] = b
        return b

    def try_take(self, user_id: str, key: str, n: float = 1.0) -> bool:
        """Non-raising consume. True iff the request fits."""
        with self._lock:
            b = self._bucket(user_id, key)
            return True if b is None else b.try_take(n)

    def check(self, user_id: str, key: str, n: float = 1.0) -> None:
        """Raise 429 if the bucket is empty. Use as a FastAPI dep glue."""
        with self._lock:
            b = self._bucket(user_id, key)
            if b is None:
                return
            if not b.try_take(n):
                retry = max(1, int(b.retry_after_seconds(n)))
                raise HTTPException(
                    status_code=429,
                    detail=f"rate limit hit ({key}); try again in ~{retry}s",
                    headers={"Retry-After": str(retry)},
                )

    # ── daily token quota ────────────────────────────────────────
    def _today_bucket(self, user_id: str) -> dict[str, Any]:
        rec = self._tokens.get(user_id)
        today = _today_utc()
        if rec is None or rec.get("day") != today:
            rec = {"day": today, "used": 0, "messages": 0}
            self._tokens[user_id] = rec
        return rec

    def remaining_tokens(self, user_id: str) -> int:
        if _DAILY_TOKEN_BUDGET <= 0 or _is_admin_user(user_id):
            return -1  # disabled / admin → unlimited
        with self._lock:
            rec = self._today_bucket(user_id)
            return max(0, _DAILY_TOKEN_BUDGET - int(rec["used"]))

    def can_send_message(self, user_id: str) -> bool:
        """Pre-check before a prompt. False iff today's budget is gone.
        Admins bypass — same allow-list as the credit ledger."""
        if _DAILY_TOKEN_BUDGET <= 0 or _is_admin_user(user_id):
            return True
        with self._lock:
            rec = self._today_bucket(user_id)
            return rec["used"] < _DAILY_TOKEN_BUDGET

    def charge_tokens(self, user_id: str, tokens: int) -> int:
        """Add to today's tally; returns new used total. Always succeeds —
        the cap is enforced at the next *send*, not in the middle of a
        streaming response (we'd never want to amputate a half-finished
        answer the user already paid for)."""
        if tokens <= 0:
            return 0
        with self._lock:
            rec = self._today_bucket(user_id)
            rec["used"] = int(rec["used"]) + int(tokens)
            return int(rec["used"])

    def note_message(self, user_id: str) -> int:
        with self._lock:
            rec = self._today_bucket(user_id)
            rec["messages"] = int(rec.get("messages", 0)) + 1
            return int(rec["messages"])

    # ── readouts ─────────────────────────────────────────────────
    def usage(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._today_bucket(user_id)
            limits = {
                k: {"capacity": int(c), "refill_per_sec": r}
                for k, (c, r) in _BUCKETS.items()
                if c > 0
            }
            return {
                "day": rec["day"],
                "tokens_used": int(rec["used"]),
                "tokens_budget": _DAILY_TOKEN_BUDGET,
                "messages_today": int(rec.get("messages", 0)),
                "limits": limits,
            }
