"""
Cost calculator + subscription credit ledger.

Mirrors pi-mono's billing model:

  - Per-request cost is computed by `calculate_cost(model, usage)`,
    which maps the four token classes against the model's per-MTok
    rates (see `models_registry.py:ModelSpec.cost`). Same shape as
    pi-mono/packages/ai/src/models.ts:calculateCost.
  - When pi already populated `usage.cost.total` (the stream's
    message_end event ships it for every response), we trust that
    instead of recomputing — saves us one source of drift if pi's
    model table moves before ours does. (pi-mono/scripts/cost.ts
    aggregates the same field.)
  - On top of the LLM cost we amortise the VM hourly across the
    concurrent-user assumption, then apply INFRA_MARKUP. That gives
    us an "all-in" dollar cost we charge against the user's monthly
    plan credit.

Plans are denominated in dollars (that's the unit users understand on
the pricing page); the per-prompt cost above gets debited from there.
When a user hits their monthly cap we soft-block prompts in chat_ws
with a `_bridge_error` carrying `code: "credit_exhausted"`.

The CreditLedger is in-memory for v1 — when the first paying user
lands we'll add a tiny SQLite table behind the same API. Stripe
webhooks call `set_plan(user_id, plan_id)` to advance/downgrade tiers.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from services.models_registry import (
    DEFAULT_MODEL_ID,
    ModelSpec,
    get_model,
)


def _is_admin_user(user_id: str) -> bool:
    """Lazy import so billing.py stays import-cheap (auth.py pulls in the
    Clerk SDK when CLERK_SECRET_KEY is set). Returns False on any error
    so a Clerk outage can never lock a paying user out of their plan."""
    if not user_id:
        return False
    try:
        from services.auth import is_admin_user
        return is_admin_user(user_id)
    except Exception:
        return False


def _f_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


# When billing isn't wired up (no STRIPE_SECRET_KEY) we treat every
# user as if they were on this plan. Default "enterprise" because the
# only people running without Stripe are operators in dev/staging —
# they want every model unlocked and unlimited credit. Operators who
# DO want to test the free-tier UX without setting up Stripe can flip
# this env var to "free".
_DEV_DEFAULT_PLAN = (os.environ.get("BILLING_DEFAULT_PLAN", "").strip() or "enterprise").lower()
_BILLING_ENABLED_FOR_LEDGER = bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())


# ── infra cost constants (overridable via env) ────────────────────
# e2-small in us-central1, on-demand: $0.0168/h.
# Bump if we resize the VM. Source: cloud.google.com/compute/all-pricing
_VM_HOURLY_USD = _f_env("BILLING_VM_HOURLY_USD", 0.0168)
# Concurrency assumption used to amortise VM cost across active users.
# An e2-small handles roughly 10 concurrent low-rate users.
_VM_USERS_AT_ONCE = max(1.0, _f_env("BILLING_VM_USERS_AT_ONCE", 10.0))
# Margin we keep on top of cost. 1.5 = 50% margin, the floor for any
# sustainable SaaS once Stripe fees + support time are factored in.
_INFRA_MARKUP = max(1.0, _f_env("BILLING_INFRA_MARKUP", 1.5))


# ── plans ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PlanSpec:
    id: str
    label: str
    monthly_price_usd: float
    monthly_credit_usd: float
    stripe_price_id: str          # populated from env per-environment
    description: str


_PLANS: dict[str, PlanSpec] = {
    "free": PlanSpec(
        id="free",
        label="Free",
        monthly_price_usd=0.0,
        # $10 of credit/month so signed-up users can actually try the
        # cloud models end-to-end (a typical Sonnet chat costs ~$0.05;
        # $10 covers ~150–200 prompts before they hit the gate). The
        # previous $2 was effectively "two short Haiku threads", which
        # didn't show off what the product can do — and forced the
        # Upgrade modal to pop after the very first conversation.
        monthly_credit_usd=_f_env("BILLING_FREE_CREDIT_USD", 10.0),
        stripe_price_id="",
        description="Try it out. Haiku + Gemini Flash models. ~50–100 prompts/month.",
    ),
    "starter": PlanSpec(
        id="starter",
        label="Starter",
        monthly_price_usd=20.0,
        monthly_credit_usd=_f_env("BILLING_STARTER_CREDIT_USD", 20.0),
        stripe_price_id=os.environ.get("STRIPE_PRICE_STARTER", "").strip(),
        description="Sonnet + Gemini Pro. $20 of usage included.",
    ),
    "pro": PlanSpec(
        id="pro",
        label="Pro",
        monthly_price_usd=100.0,
        # 2× value: pay $100, spend up to $200 of compute. Modest
        # subsidy keeps the tier attractive vs going direct to
        # Anthropic ($100 of API time at retail) while leaving us a
        # safety margin if a user maxes out.
        monthly_credit_usd=_f_env("BILLING_PRO_CREDIT_USD", 200.0),
        stripe_price_id=os.environ.get("STRIPE_PRICE_PRO", "").strip(),
        description="Adds Opus 4.7. Pay $100, spend up to $200. Best value for daily users.",
    ),
    "enterprise": PlanSpec(
        id="enterprise",
        label="Enterprise",
        monthly_price_usd=200.0,
        # 1.75× value: pay $200, spend up to $350 of compute. Sized to
        # the realistic ceiling of a power-user month (calibrated by
        # actual usage, not a marketing multiplier). If we ever see an
        # Enterprise user actually approaching the cap, that's a real
        # signal we should add a bigger plan, not eat more cost.
        # NOTE: env var stays BILLING_MAX_CREDIT_USD / STRIPE_PRICE_MAX
        # because the customer's existing prod env files use those.
        # Rename in a future migration.
        monthly_credit_usd=_f_env("BILLING_MAX_CREDIT_USD", 350.0),
        stripe_price_id=os.environ.get("STRIPE_PRICE_MAX", "").strip(),
        description="Pay $200, spend up to $350. For full-time Opus / multi-hour Gemini Pro sessions.",
    ),
}


def plans() -> list[dict[str, Any]]:
    """Public catalogue (drives the SPA's pricing chip + upgrade flow).
    `stripe_price_id` is included so the frontend can pass it back to
    /api/billing/checkout without hard-coding the env-specific id."""
    return [
        {
            "id": p.id,
            "label": p.label,
            "monthly_price_usd": p.monthly_price_usd,
            "monthly_credit_usd": p.monthly_credit_usd,
            "stripe_price_id": p.stripe_price_id,
            "description": p.description,
        }
        for p in _PLANS.values()
    ]


def plan_for(plan_id: str) -> PlanSpec:
    return _PLANS.get(plan_id) or _PLANS["free"]


def known_plan_id(plan_id: str) -> bool:
    """True if `plan_id` is a tier we actually ship. Used by the Stripe
    webhook handler to reject garbage `metadata.plan_id` values before
    they hit the ledger."""
    return plan_id in _PLANS


def plan_for_stripe_price(stripe_price_id: str) -> Optional[PlanSpec]:
    """Reverse-lookup used by the Stripe webhook to map a price id back
    to the local plan tier when a checkout completes."""
    if not stripe_price_id:
        return None
    for p in _PLANS.values():
        if p.stripe_price_id and p.stripe_price_id == stripe_price_id:
            return p
    return None


# ── per-prompt cost calculator ────────────────────────────────────
@dataclass(frozen=True)
class CostBreakdown:
    model_id: str
    llm_usd: float
    vm_usd: float
    margin_usd: float
    total_usd: float


def _llm_cost_from_tokens(model: ModelSpec, usage: dict[str, Any]) -> float:
    """Same formula as pi-mono `calculateCost`: per-class token count
    times per-MTok price, summed."""
    return (
        (int(usage.get("input") or 0)        * model.cost.input       / 1_000_000)
        + (int(usage.get("output") or 0)     * model.cost.output      / 1_000_000)
        + (int(usage.get("cacheRead") or 0)  * model.cost.cache_read  / 1_000_000)
        + (int(usage.get("cacheWrite") or 0) * model.cost.cache_write / 1_000_000)
    )


# Tools whose execute() bodies make their own provider call and report
# usage in result.details.usage. Without this allow-list those calls are
# free for the user and we eat the bill. Adding a new sub-LLM tool? Just
# surface `details.usage = { input, output, cacheRead, cacheWrite, model }`
# from the tool and add its name here. See chat_ws.py:_maybe_charge_tool_sub_llm
# for the orchestration side and extensions/usage.ts for the typescript helpers
# that produce the usage payload.
SUB_LLM_TOOLS: set[str] = {"search_docs", "web_search"}


def extract_sub_llm_usage(evt: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Pull a sub-LLM `usage` payload out of a tool_execution_end event.

    Returns the inner usage dict (with `model` set) if the event is from a
    known sub-LLM tool AND the tool surfaced its usage payload as designed,
    otherwise None. Pure function — no side effects, easy to unit test.

    The reason this is its own helper (vs. inlined in the chat_ws closure):
    every "did pi tell us about a side LLM call?" decision lives here, and
    we want to be able to assert against it without spinning up a real WS.
    """
    if evt.get("type") not in ("tool_execution_end", "tool_result"):
        return None
    tool_name = str(evt.get("toolName") or "")
    if tool_name not in SUB_LLM_TOOLS:
        return None
    result = evt.get("result")
    if not isinstance(result, dict):
        return None
    details = result.get("details")
    if not isinstance(details, dict):
        return None
    usage = details.get("usage")
    if not isinstance(usage, dict):
        return None
    return usage


def usage_token_total(usage: dict[str, Any]) -> int:
    """Sum of the four token classes — matches what calculate_cost
    multiplies by per-class rates. Used for rate-limit charge_tokens()."""
    return (
        int(usage.get("input") or 0)
        + int(usage.get("output") or 0)
        + int(usage.get("cacheRead") or 0)
        + int(usage.get("cacheWrite") or 0)
    )


def estimate_prompt_cost(
    usage: dict[str, Any],
    *,
    model_id: str = DEFAULT_MODEL_ID,
    wall_seconds: float = 0.0,
) -> CostBreakdown:
    """Compute the all-in dollar cost of a single assistant turn.

    `usage` mirrors pi's `message_end.usage` payload:
        {input, output, cacheRead, cacheWrite, [cost: {total, …}]}

    If pi already produced a `cost.total` (pi-mono populates it for
    every assistant message via models.ts:calculateCost), trust that
    as the LLM cost — no double-counting if pi's model table moves
    before ours does. Otherwise recompute from token counts."""
    model = get_model(model_id) or get_model(DEFAULT_MODEL_ID)

    cost_subtree = usage.get("cost") if isinstance(usage.get("cost"), dict) else {}
    pi_total = float((cost_subtree or {}).get("total") or 0)

    if pi_total > 0:
        llm = pi_total
    elif model is not None:
        llm = _llm_cost_from_tokens(model, usage)
    else:
        llm = 0.0

    vm = (_VM_HOURLY_USD * max(0.0, wall_seconds) / 3600.0) / _VM_USERS_AT_ONCE
    base = llm + vm
    total = base * _INFRA_MARKUP

    return CostBreakdown(
        model_id=model.id if model else model_id,
        llm_usd=round(llm, 6),
        vm_usd=round(vm, 6),
        margin_usd=round(total - base, 6),
        total_usd=round(total, 6),
    )


def _month_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _now_iso_utc() -> str:
    """ISO-8601 with millisecond resolution. Matches what pi writes
    in its JSONL log so events sort cleanly when interleaved."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + (
        f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
    )


# ── persistence (SQLite) ──────────────────────────────────────────
# Why SQLite:
#   * The credit ledger (events, monthly spend, plan, Stripe customer)
#     used to be in-memory only. Every uvicorn restart wiped the
#     activity log, and a server restart between Stripe webhook and
#     the next cost charge meant we'd undercharge the user.
#   * SQLite gives durable, GCS-syncable state with zero ops cost.
#     One file, ~200 KB at steady state, lives in `web/data/billing.db`
#     so it travels with the rest of the workspace tree when we rsync
#     to GCS for backups (deploy/README documents the exclusion list,
#     and `billing.db` is NOT excluded — see services/storage_exclusions).
#
# Concurrency model:
#   * Single connection, `check_same_thread=False`, `isolation_level=None`
#     (autocommit). FastAPI runs all coroutine work on the same loop;
#     the lock inside CreditLedger serialises writes. Reads (recent
#     events) hit a different prepared statement that's safe to share.
#   * `journal_mode=WAL` because we read while writing — the credit
#     gate runs `can_spend` on every chat WS receive, while sub-LLM
#     tool calls run `note_cost` mid-turn from the same loop.
# Default lives alongside registry.json under config.DATA_ROOT so all
# durable state ships to GCS together. In production
# (PI_DATA_ROOT=/srv/pi/data) this resolves to /srv/pi/data/billing.db
# on the persistent volume; in dev it stays under web/data/. The legacy
# parents[2]/"data" derivation pinned this to /app/web/data which broke
# the moment the container rootfs went read_only — never derive a
# writable path from __file__ in container land.
#
# Operators can still override with BILLING_DB_PATH for one-off staging
# instances that want their own DB on a different volume.
_BILLING_DB_OVERRIDE = os.environ.get("BILLING_DB_PATH", "").strip()
if _BILLING_DB_OVERRIDE:
    _DB_PATH = Path(_BILLING_DB_OVERRIDE).expanduser().resolve()
else:
    from config import DATA_ROOT  # local import: avoids circular at module load
    _DB_PATH = (DATA_ROOT / "billing.db").resolve()


def _connect_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(_DB_PATH),
        check_same_thread=False,
        isolation_level=None,  # autocommit; we control batching ourselves
    )
    # Lock down to 0600 IMMEDIATELY after the file exists. SQLite creates
    # new files with the process umask which is typically 0022 → 0644
    # world-readable. In our dual-uid model the sandbox uid (1000) lives
    # in the same container, so a world-readable billing.db means every
    # AI bash subprocess can `cat` the entire spend ledger. The boot-time
    # chmod in pi-prepare.service catches this on RESTART, but we need
    # the safe mode from the moment the file appears.
    #
    # Same hardening applies to the WAL/SHM siblings created by SQLite
    # in WAL mode; we attempt-and-ignore on those (they may not exist
    # until the first checkpoint).
    try:
        os.chmod(_DB_PATH, 0o600)
        for sibling in (_DB_PATH.with_suffix(_DB_PATH.suffix + "-wal"),
                        _DB_PATH.with_suffix(_DB_PATH.suffix + "-shm")):
            if sibling.exists():
                os.chmod(sibling, 0o600)
    except OSError as exc:
        # On dev (where umask is whatever), warn but don't crash. In prod
        # the chmod always succeeds because the file is owned by uid 1100
        # which is our own uid.
        import logging
        logging.getLogger(__name__).warning(
            "billing: chmod 0600 on %s failed: %s", _DB_PATH, exc
        )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Schema. `IF NOT EXISTS` so this is safe to call on every boot.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cost_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT    NOT NULL,
            ts              TEXT    NOT NULL,           -- ISO-8601 UTC ms
            source          TEXT,                       -- 'chat' | 'tool'
            tool            TEXT,
            model           TEXT,
            session_id      TEXT,
            workspace_id    TEXT,
            input_tokens    INTEGER NOT NULL DEFAULT 0,
            output_tokens   INTEGER NOT NULL DEFAULT 0,
            cache_read      INTEGER NOT NULL DEFAULT 0,
            cache_write     INTEGER NOT NULL DEFAULT 0,
            cost_usd        REAL    NOT NULL DEFAULT 0,
            breakdown_json  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cost_events_user_ts
            ON cost_events(user_id, ts DESC);

        CREATE TABLE IF NOT EXISTS monthly_spend (
            user_id     TEXT NOT NULL,
            month       TEXT NOT NULL,                -- YYYY-MM
            spent_usd   REAL NOT NULL DEFAULT 0,
            prompts     INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, month)
        );

        CREATE TABLE IF NOT EXISTS user_plan (
            user_id  TEXT PRIMARY KEY,
            plan_id  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stripe_customers (
            user_id      TEXT PRIMARY KEY,
            customer_id  TEXT NOT NULL
        );
        """
    )
    return conn


# Module-level so multiple CreditLedger.instance() calls share one
# connection. SQLite (with check_same_thread=False) is fine for FastAPI's
# single event-loop + worker thread model.
_db_conn: Optional[sqlite3.Connection] = None
_db_lock = threading.Lock()


def _db() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is not None:
        return _db_conn
    with _db_lock:
        if _db_conn is None:
            _db_conn = _connect_db()
    return _db_conn


# ── per-user credit ledger ────────────────────────────────────────
class CreditLedger:
    """
    Tracks USD spend per user per billing month + the user's plan.

    In-memory for v1. Stripe webhooks call `set_plan` to mirror the
    canonical state held by Stripe; if we restart the process we'll
    rebuild on the next webhook event (Stripe replays on demand via
    the dashboard). When we're ready for "stripe is the source of
    truth, we cache locally" we'll add a SQLite table behind the
    same API — the interface stays identical."""

    _instance: Optional["CreditLedger"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "CreditLedger":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # user_id → {"month": "YYYY-MM", "spent_usd": float, "prompts": int}
        # In-memory cache; hydrated from SQLite on boot, write-through
        # on every note_cost. Reads of `can_spend` happen on every WS
        # message so we don't want to hit SQLite on the hot path.
        self._spend: dict[str, dict[str, Any]] = {}
        # user_id → plan id ("free" if missing). Updated by Stripe
        # webhook (customer.subscription.updated / .deleted).
        self._plan: dict[str, str] = {}
        # user_id → stripe customer id. Lets us send the user back to
        # the Stripe Customer Portal for self-serve plan changes.
        self._stripe_customer: dict[str, str] = {}
        # Cost events live in SQLite (`cost_events` table). We don't
        # cache them in-memory at all — the activity view's ~200-row
        # `SELECT … ORDER BY id DESC LIMIT N` is fast enough on the
        # indexed table and removes one whole class of "lost log on
        # restart" bug. See _DB_PATH for the durable file location.
        self._hydrate_from_db()

    def _hydrate_from_db(self) -> None:
        """Pull persistent state into the in-memory caches at boot.

        After this returns:
          * `self._plan` knows every user we've ever set a plan for,
            so the first request post-restart doesn't see them as
            "free" (we'd undercharge).
          * `self._stripe_customer` is rebuilt so the Customer Portal
            link works without waiting for the next Stripe webhook.
          * `self._spend` carries the current month's accumulated
            spend so soft-block (`can_spend`) keeps working across
            restarts.

        Past-month rows in `monthly_spend` are intentionally NOT
        loaded — they're only useful to historical reports, and the
        next call to `_bucket(user_id)` lazily inserts a fresh
        zeroed row when the calendar rolls over.
        """
        conn = _db()
        try:
            for row in conn.execute("SELECT user_id, plan_id FROM user_plan"):
                self._plan[row["user_id"]] = row["plan_id"]
            for row in conn.execute(
                "SELECT user_id, customer_id FROM stripe_customers"
            ):
                self._stripe_customer[row["user_id"]] = row["customer_id"]
            month = _month_utc()
            for row in conn.execute(
                "SELECT user_id, spent_usd, prompts FROM monthly_spend "
                "WHERE month = ?",
                (month,),
            ):
                self._spend[row["user_id"]] = {
                    "month": month,
                    "spent_usd": float(row["spent_usd"] or 0.0),
                    "prompts": int(row["prompts"] or 0),
                }
        except Exception as exc:
            # Hydration MUST NOT fail boot; the worst outcome is we
            # show empty totals until the user does something that
            # writes to the DB. Log loudly so we know.
            import sys
            print(f"[billing] DB hydrate failed: {exc}", file=sys.stderr)

    def _bucket(self, user_id: str) -> dict[str, Any]:
        rec = self._spend.get(user_id)
        month = _month_utc()
        if rec is None or rec.get("month") != month:
            rec = {"month": month, "spent_usd": 0.0, "prompts": 0}
            self._spend[user_id] = rec
        return rec

    def _persist_event(self, user_id: str, evt: dict[str, Any]) -> None:
        """Write one cost event to the durable cost_events table.
        Caller holds `self._lock`."""
        tokens = evt.get("tokens") or {}
        breakdown = evt.get("breakdown")
        try:
            _db().execute(
                "INSERT INTO cost_events (user_id, ts, source, tool, model, "
                "session_id, workspace_id, input_tokens, output_tokens, "
                "cache_read, cache_write, cost_usd, breakdown_json) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    evt.get("ts"),
                    evt.get("source"),
                    evt.get("tool"),
                    evt.get("model"),
                    evt.get("session_id"),
                    evt.get("workspace_id"),
                    int(tokens.get("input") or 0),
                    int(tokens.get("output") or 0),
                    int(tokens.get("cacheRead") or 0),
                    int(tokens.get("cacheWrite") or 0),
                    float(evt.get("cost_usd") or 0.0),
                    json.dumps(breakdown) if breakdown is not None else None,
                ),
            )
        except Exception as exc:
            # We deliberately swallow — losing a single billing row to
            # a transient DB error is preferable to dropping the user's
            # in-flight chat turn. The in-memory _spend update still
            # ran, so credit gating stays correct for the rest of the
            # request lifetime.
            import sys
            print(f"[billing] event persist failed: {exc}", file=sys.stderr)

    def _persist_monthly_spend(
        self, user_id: str, month: str, spent_usd: float, prompts: int
    ) -> None:
        """UPSERT the monthly aggregate. Caller holds `self._lock`."""
        try:
            _db().execute(
                "INSERT INTO monthly_spend (user_id, month, spent_usd, prompts) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, month) DO UPDATE SET "
                "spent_usd = excluded.spent_usd, prompts = excluded.prompts",
                (user_id, month, float(spent_usd), int(prompts)),
            )
        except Exception as exc:
            import sys
            print(f"[billing] spend persist failed: {exc}", file=sys.stderr)

    @staticmethod
    def _build_event(
        *,
        user_id: str,
        cost_usd: float,
        source: str,
        model: Optional[str],
        session_id: Optional[str],
        workspace_id: Optional[str],
        tool: Optional[str],
        usage: Optional[dict[str, Any]],
        breakdown: Optional[dict[str, float]],
    ) -> dict[str, Any]:
        # Keep the serialised event small — the SPA's table doesn't
        # need the full pi `usage` blob, just the four token classes.
        u = usage or {}

        def _i(key: str) -> int:
            try:
                return int(u.get(key) or 0)
            except (TypeError, ValueError):
                return 0

        return {
            "ts": _now_iso_utc(),
            "user_id": user_id,
            "source": source,                 # "chat" | "tool"
            "tool": tool,                      # "search_docs", "web_search", …
            "model": model,
            "session_id": session_id,
            "workspace_id": workspace_id,
            "tokens": {
                "input": _i("input"),
                "output": _i("output"),
                "cacheRead": _i("cacheRead"),
                "cacheWrite": _i("cacheWrite"),
            },
            "cost_usd": round(float(cost_usd), 6),
            "breakdown": (
                {k: round(float(v), 6) for k, v in (breakdown or {}).items()}
                if breakdown else None
            ),
        }

    # ── plan management ──────────────────────────────────────────
    def set_plan(self, user_id: str, plan_id: str) -> None:
        # Defence-in-depth: refuse unknown plan ids so a misbehaving
        # caller (Stripe webhook with a typo, dev script with a stale
        # constant) can't land us on plan "godmode" or "max" (the old
        # tier name we just renamed). The route handler in
        # routes/billing.py also pre-filters; this is the second
        # gate.
        if plan_id not in _PLANS:
            print(
                f"[ledger] refusing set_plan({user_id!r}, {plan_id!r}) "
                "— unknown plan id",
                file=__import__("sys").stderr,
            )
            return
        with self._lock:
            self._plan[user_id] = plan_id
            try:
                _db().execute(
                    "INSERT INTO user_plan (user_id, plan_id) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET plan_id = excluded.plan_id",
                    (user_id, plan_id),
                )
            except Exception as exc:
                import sys
                print(f"[billing] plan persist failed: {exc}", file=sys.stderr)

    def get_plan(self, user_id: str) -> PlanSpec:
        if _is_admin_user(user_id):
            return plan_for("enterprise")
        with self._lock:
            return plan_for(self._plan.get(user_id, self._fallback_plan_locked()))

    def get_plan_id(self, user_id: str) -> str:
        if _is_admin_user(user_id):
            return "enterprise"
        with self._lock:
            return self._plan.get(user_id, self._fallback_plan_locked())

    def _fallback_plan_locked(self) -> str:
        """Plan id used when we don't have an explicit assignment for
        the user. In production (Stripe enabled) that's always "free"
        until checkout completes. In dev (no Stripe) it's whatever
        BILLING_DEFAULT_PLAN says — defaulting to "enterprise" so
        operators get every model unlocked without Stripe first."""
        if _BILLING_ENABLED_FOR_LEDGER:
            return "free"
        return _DEV_DEFAULT_PLAN if _DEV_DEFAULT_PLAN in _PLANS else "enterprise"

    def set_stripe_customer(self, user_id: str, customer_id: str) -> None:
        with self._lock:
            if customer_id:
                self._stripe_customer[user_id] = customer_id
                try:
                    _db().execute(
                        "INSERT INTO stripe_customers (user_id, customer_id) "
                        "VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET "
                        "customer_id = excluded.customer_id",
                        (user_id, customer_id),
                    )
                except Exception as exc:
                    import sys
                    print(
                        f"[billing] stripe_customer persist failed: {exc}",
                        file=sys.stderr,
                    )

    def get_stripe_customer(self, user_id: str) -> Optional[str]:
        with self._lock:
            return self._stripe_customer.get(user_id)

    def find_user_by_stripe_customer(self, customer_id: str) -> Optional[str]:
        with self._lock:
            for uid, cid in self._stripe_customer.items():
                if cid == customer_id:
                    return uid
        return None

    # ── credit gating ────────────────────────────────────────────
    def can_spend(self, user_id: str) -> bool:
        # Admins are uncapped — see is_admin_user. We still record their
        # spend below so audit/usage stays accurate; this just removes
        # the hard "credit_exhausted" gate.
        if _is_admin_user(user_id):
            return True
        with self._lock:
            plan = plan_for(self._plan.get(user_id, self._fallback_plan_locked()))
            rec = self._bucket(user_id)
            return float(rec["spent_usd"]) < plan.monthly_credit_usd

    def note_cost(
        self,
        user_id: str,
        cost_usd: float,
        *,
        # Optional structured metadata. When the chat WS calls us it
        # passes these so the activity log can render a useful table
        # ("when, model, tokens, $cost, which session, was it the
        # main turn or a tool sub-LLM"). Older callers that omit
        # these still work — they just produce a thinner event row.
        source: str = "chat",
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        tool: Optional[str] = None,
        usage: Optional[dict[str, Any]] = None,
        breakdown: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        # We append an event even when cost_usd is 0 or negative so
        # the user sees their failed/free turns too — it makes the
        # activity log readable when debugging "why didn't anything
        # show up?". The aggregate spent_usd / prompt counter only
        # advances on positive cost.
        evt = self._build_event(
            user_id=user_id,
            cost_usd=max(0.0, float(cost_usd)),
            source=source,
            model=model,
            session_id=session_id,
            workspace_id=workspace_id,
            tool=tool,
            usage=usage,
            breakdown=breakdown,
        )
        with self._lock:
            # Persist the event row even when cost is 0 — operators
            # debugging "why didn't this cost anything?" want to see it.
            self._persist_event(user_id, evt)
            rec = self._bucket(user_id)
            if cost_usd > 0:
                rec["spent_usd"] = float(rec["spent_usd"]) + float(cost_usd)
                rec["prompts"] = int(rec.get("prompts", 0)) + 1
                # Mirror the new aggregate to disk so a restart in the
                # middle of the month doesn't re-grant the user a fresh
                # credit allowance. (We only write on positive deltas
                # to keep the I/O quiet on no-cost events.)
                self._persist_monthly_spend(
                    user_id, rec["month"], rec["spent_usd"], rec["prompts"]
                )
            return self._snapshot_locked(user_id, rec)

    def recent_events(
        self,
        user_id: str,
        *,
        limit: int = 200,
        since_iso: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return up to `limit` most-recent events for `user_id`,
        newest first. `since_iso` (ISO-8601 UTC string) clips the
        result to events strictly after that timestamp — used by the
        SPA to poll for new entries without re-shipping the full
        log.

        Reads straight from SQLite (`cost_events` table) so the
        Activity view survives backend restarts. The table is indexed
        on (user_id, ts DESC) so this is fast even with months of
        history piled up.
        """
        clamped = max(1, min(int(limit), 500))
        sql = (
            "SELECT ts, source, tool, model, session_id, workspace_id, "
            "input_tokens, output_tokens, cache_read, cache_write, "
            "cost_usd, breakdown_json FROM cost_events WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if since_iso:
            sql += " AND ts > ?"
            params.append(since_iso)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(clamped)
        try:
            rows = _db().execute(sql, params).fetchall()
        except Exception as exc:
            import sys
            print(f"[billing] event query failed: {exc}", file=sys.stderr)
            return []
        out: list[dict[str, Any]] = []
        for row in rows:
            breakdown = None
            if row["breakdown_json"]:
                try:
                    breakdown = json.loads(row["breakdown_json"])
                except (TypeError, ValueError):
                    breakdown = None
            out.append({
                "ts": row["ts"],
                "user_id": user_id,
                "source": row["source"],
                "tool": row["tool"],
                "model": row["model"],
                "session_id": row["session_id"],
                "workspace_id": row["workspace_id"],
                "tokens": {
                    "input": int(row["input_tokens"] or 0),
                    "output": int(row["output_tokens"] or 0),
                    "cacheRead": int(row["cache_read"] or 0),
                    "cacheWrite": int(row["cache_write"] or 0),
                },
                "cost_usd": round(float(row["cost_usd"] or 0.0), 6),
                "breakdown": breakdown,
            })
        return out

    def snapshot(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._bucket(user_id)
            return self._snapshot_locked(user_id, rec)

    def _snapshot_locked(self, user_id: str, rec: dict[str, Any]) -> dict[str, Any]:
        # Admin override mirrors get_plan_id so the chip + UI surface
        # the unlocked tier even though we never persisted it in _plan.
        if _is_admin_user(user_id):
            plan_id = "enterprise"
        else:
            plan_id = self._plan.get(user_id, self._fallback_plan_locked())
        plan = plan_for(plan_id)
        spent = float(rec["spent_usd"])
        remaining = max(0.0, plan.monthly_credit_usd - spent)
        return {
            "month": rec["month"],
            "plan": {
                "id": plan.id,
                "label": plan.label,
                "monthly_price_usd": plan.monthly_price_usd,
                "monthly_credit_usd": plan.monthly_credit_usd,
            },
            "spent_usd": round(spent, 4),
            "remaining_usd": round(remaining, 4),
            "remaining_pct": (
                round(100.0 * remaining / plan.monthly_credit_usd, 1)
                if plan.monthly_credit_usd > 0 else 0.0
            ),
            "prompts": int(rec.get("prompts", 0)),
            "stripe_customer_id": self._stripe_customer.get(user_id),
        }
