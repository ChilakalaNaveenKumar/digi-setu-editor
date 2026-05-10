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
# A note on connection-shaped buckets vs user-action buckets:
#
#   ws.connect / pi.spawn fire on EVERY socket reconnect — laptop
#   sleep/wake, NAT idle timeout, network blip, our own watchdog
#   respawn on the desktop, etc. None of those are user actions and
#   none of them are something the user can throttle by "trying
#   again later". Charging a tight token bucket against them just
#   converts a transient network blip into a "you're connecting too
#   fast" error wall.
#
#   The right place to shape user behaviour is the bucket the user
#   actually drives: chat.message (sending a prompt). That stays at
#   20 burst / 30 per minute.
#
# Web is multi-tenant so we keep these buckets in place as a DoS
# brake (a malicious script could open WS upgrades in a tight loop
# from a public endpoint), but the ceilings are now high enough that
# real reconnect storms — even from a tab-hoarder coming back from
# overnight sleep — never trip them.
_BUCKETS: dict[str, tuple[int, float]] = {
    # WebSocket upgrades. Bumped from 30 cap / 1 per sec refill to
    # 200 / 1 per sec — comfortably absorbs a 50-tab user reconnecting
    # all at once, while still bounding a malicious open/close loop.
    "ws.connect":  (_int_env("RL_WS_CONNECT_CAPACITY", 200),
                    _int_env("RL_WS_CONNECT_PER_MIN", 60) / 60.0),
    # New pi subprocess spawn. The OLD limit (10 cap / 1 per minute
    # refill) was the actual cause of the "you're connecting too fast"
    # close codes users saw after a few sleep/wake cycles. Bumped to
    # 200 cap / 1 per sec refill — still enough to make a deliberate
    # spawn-flood expensive, but invisible to real users.
    "pi.spawn":    (_int_env("RL_PI_SPAWN_CAPACITY", 200),
                    _int_env("RL_PI_SPAWN_PER_MIN", 60) / 60.0),
    # User prompts within a session.
    "chat.message": (_int_env("RL_CHAT_MSG_CAPACITY", 20),
                     _int_env("RL_CHAT_MSG_PER_MIN", 30) / 60.0),
    # LLM-relay messages (desktop local-pi cloud auth path). Separate
    # from `chat.message` because the relay is a different transport:
    # one chat WS may fan out to many provider calls (multi-step agents,
    # retries, sub-LLM tools), and we don't want a 30-msg/min ceiling on
    # the WS to silently throttle a perfectly normal multi-tool turn.
    # 60-burst / 120-per-min matches an aggressive but realistic agent
    # loop (one turn ≈ 5–10 provider calls; sustained 12 turns/min).
    "relay.message": (_int_env("RL_RELAY_CAPACITY", 60),
                      _int_env("RL_RELAY_PER_MIN", 120) / 60.0),
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


# Hard cap on concurrent (open at the same instant) chat WebSockets per
# user. Distinct from the burst-limited "ws.connect" bucket above:
# - "ws.connect" stops a script that opens 100 sockets in 5 s.
# - This cap stops a single user (or a tab-hoarder) from holding 50
#   live pi subprocesses open at once. Cursor's web product uses the
#   same model: you can open multiple chats but only N run at a time.
# Default 5 satisfies the user-visible promise: "≥3 in parallel on web,
# ≥5 in parallel on desktop". Both transports share the same cloud pi
# pool (web hits /ws/sessions/* directly, desktop tunnels through
# /v1/ws/desktop-relay) so a single integer is enough — we don't need
# to split the budget per transport. Setting RL_MAX_CONCURRENT_CHATS=0
# disables the cap (e.g. for the dev loop or integration tests).
_MAX_CONCURRENT_CHATS = _int_env("RL_MAX_CONCURRENT_CHATS", 5)


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
        # Concurrent-chat counters. Keyed by user_id. We don't shard
        # by purpose like the buckets do — the only consumer right now
        # is the chat WS, and one int per user is plenty.
        self._concurrent: dict[str, int] = {}

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

    # ── concurrent-chat slot management ──────────────────────────
    def acquire_chat_slot(self, user_id: str) -> tuple[bool, int, int]:
        """Try to claim one of the user's concurrent chat slots.

        Returns a 3-tuple `(granted, current, cap)`:
          granted — True if the slot was reserved, False if the cap
                    is hit. Caller must close the WS with 4429 when
                    granted is False (we don't raise here because
                    the chat WS handler decides the close code).
          current — number of chats now open for this user (post-claim
                    when granted, post-rejection when denied).
          cap     — the configured maximum (so the SPA can show
                    "3 of 3 chats open — close one to start a new one").

        Caller MUST pair every successful acquire with a
        `release_chat_slot(user_id)` in a finally block, otherwise the
        counter will leak across reconnects until the process restarts.
        Admin users bypass the cap (we still increment so /api/usage
        shows real activity, but never deny).
        """
        cap = _MAX_CONCURRENT_CHATS
        with self._lock:
            current = self._concurrent.get(user_id, 0)
            if cap > 0 and current >= cap and not _is_admin_user(user_id):
                return (False, current, cap)
            self._concurrent[user_id] = current + 1
            return (True, current + 1, cap)

    def release_chat_slot(self, user_id: str) -> None:
        """Drop the user's chat-slot count by one. No-op when already
        at zero — the close handler may be called twice on connection
        teardown and we'd rather under-count than panic.
        """
        with self._lock:
            current = self._concurrent.get(user_id, 0)
            if current <= 1:
                self._concurrent.pop(user_id, None)
            else:
                self._concurrent[user_id] = current - 1

    def concurrent_chats(self, user_id: str) -> tuple[int, int]:
        """Snapshot for the SPA's chat-slot indicator. (current, cap)."""
        with self._lock:
            return (self._concurrent.get(user_id, 0), _MAX_CONCURRENT_CHATS)

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


# ── module-level convenience for the LLM relay ─────────────────────
def consume_user_quota(user_id: str) -> None:
    """Charge one slot of the `relay.message` bucket for `user_id`.

    Raises 429 if the bucket is empty (with `Retry-After`). Admins are
    NOT bypassed at the bucket layer because a runaway script holding
    an admin JWT could DOS the VM regardless of paying status — the
    rate limiter is a system-protection measure, not a billing gate
    (the credit gate sits in billing.check_relay_budget).

    Defined as a module-level function (not a `RateLimiter` method) so
    the relay route handler can inject it as a `Depends(...)` straight
    out of the import — same shape the SPA uses for its own check.
    """
    RateLimiter.instance().check(user_id, "relay.message")
