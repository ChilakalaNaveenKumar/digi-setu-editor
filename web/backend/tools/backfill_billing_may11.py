"""
One-shot backfill: synthesise cost_events rows for chat turns that ran
between 2026-05-11 and the moment we ported the SSE billing hook.

Why this exists
---------------
The WS→SSE migration that shipped 2026-05-11 ported the transport,
fanout, watchdog, and title-gen — but lost the `_maybe_charge_usage`
+ `_maybe_charge_tool_sub_llm` hooks that lived in chat_ws.py. From
2026-05-11 to the deploy that fixes this regression, every assistant
turn was free: cost_events stopped being written, monthly_spend
stopped advancing, and rate-limit token buckets never billed
against the daily fairness cap.

Pi writes its own session JSONL with full `usage` (input / output /
cacheRead / cacheWrite, plus a `cost.total` from pi-mono's
calculateCost) on every assistant message. That gives us
everything we need to reconstruct the missing cost_events rows.

Self-contained on purpose
-------------------------
The script does NOT import from `services/`. It runs on the host VM
against the bind-mounted /srv/pi/data with pure stdlib Python so we
don't have to wedge it inside the read-only backend container. The
cost formula below is the same one services/billing.py uses (model
table is read from the container's tagged model registry payload,
which gets dumped into a JSON the script can read separately — but
for the backfill we use pi-mono's `usage.cost.total` field that
pi-coding-agent itself writes alongside every message, so we don't
actually need our per-model price table here).

What this does
--------------
1. For every session JSONL under `<chats_root>`, resolve the
   owning `user_id` + `workspace_id` via the same `registry.json`
   the live backend reads.
2. For every line where `type="message"` AND `message.role="assistant"`
   AND `timestamp >= --since` AND `message.usage` is present, compute
   the all-in cost (LLM × infra markup + VM amortisation when wall-
   seconds are available) and INSERT a row into `cost_events`
   carrying the HISTORICAL timestamp (not "now") so the per-day
   breakdown matches reality.
3. Skip rows where a matching `(session_id, ts)` already exists, so
   the script is safe to re-run.
4. Re-derive `monthly_spend` from the now-correct `cost_events` so
   the credit gate uses an accurate aggregate.

Usage
-----
Dry-run first (this just prints what it would do):

    sudo python3 /tmp/backfill_billing_may11.py \\
        --data-root /srv/pi/data --since 2026-05-11

Apply for real:

    sudo python3 /tmp/backfill_billing_may11.py \\
        --data-root /srv/pi/data --since 2026-05-11 --apply

Idempotent: a second `--apply` is a no-op.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional


# Infrastructure markup mirrors services/billing.py defaults. We don't
# need per-model token prices here because pi-mono populates
# `message.usage.cost.total` on every assistant turn — that's what the
# live `_maybe_charge_usage` trusts when present, and it's present
# 100% of the time in real chats. Treat-as-zero is a fail-closed
# fallback so a malformed usage payload never bills $infinity.
_VM_HOURLY_USD = float(os.environ.get("BILLING_VM_HOURLY_USD", "0.0168"))
_VM_USERS_AT_ONCE = max(1.0, float(os.environ.get("BILLING_VM_USERS_AT_ONCE", "10.0")))
_INFRA_MARKUP = max(1.0, float(os.environ.get("BILLING_INFRA_MARKUP", "1.5")))


@dataclass
class SessionMeta:
    session_id: str
    workspace_id: str
    user_id: str


@dataclass
class CostBreakdown:
    model_id: str
    llm_usd: float
    vm_usd: float
    margin_usd: float
    total_usd: float


def _estimate_cost(
    usage: dict[str, Any], *, model_id: str, wall_seconds: float = 0.0
) -> CostBreakdown:
    """Mirror of services/billing.estimate_prompt_cost limited to the
    backfill case: trust pi-mono's `usage.cost.total` (always present
    for backfilled turns), then add VM amortisation × infra markup."""
    cost_subtree = usage.get("cost") if isinstance(usage.get("cost"), dict) else {}
    llm = float((cost_subtree or {}).get("total") or 0)
    vm = (_VM_HOURLY_USD * max(0.0, wall_seconds) / 3600.0) / _VM_USERS_AT_ONCE
    base = llm + vm
    total = base * _INFRA_MARKUP
    return CostBreakdown(
        model_id=model_id,
        llm_usd=round(llm, 6),
        vm_usd=round(vm, 6),
        margin_usd=round(total - base, 6),
        total_usd=round(total, 6),
    )


def _load_registry(registry_path: Path) -> dict[str, Any]:
    if not registry_path.exists():
        raise SystemExit(f"registry.json not found at {registry_path}")
    return json.loads(registry_path.read_text())


def _resolve_session_meta(
    session_dir: Path, registry: dict[str, Any]
) -> Optional[SessionMeta]:
    """Map a session JSONL folder to (session_id, workspace_id, user_id).

    The directory name IS the session id (registry stores it that way).
    """
    sid = session_dir.name
    sess = registry.get("sessions", {}).get(sid)
    if not isinstance(sess, dict):
        return None
    wsid = sess.get("workspace_id")
    if not isinstance(wsid, str):
        return None
    ws = registry.get("workspaces", {}).get(wsid)
    if not isinstance(ws, dict):
        return None
    uid = ws.get("owner_user_id")
    if not isinstance(uid, str):
        return None
    return SessionMeta(session_id=sid, workspace_id=wsid, user_id=uid)


def _iter_assistant_turns(
    jsonl_path: Path, since_iso: str
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield (timestamp, model, usage) for every assistant turn in
    `jsonl_path` whose timestamp is >= `since_iso`.

    `since_iso` is compared lexically — works because pi writes
    zero-padded ISO-8601 UTC, which sorts the same as chronologically.
    """
    try:
        fh = jsonl_path.open("r", encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  [skip] cannot open {jsonl_path}: {exc}", file=sys.stderr)
        return
    with fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") != "message":
                continue
            msg = evt.get("message")
            if not isinstance(msg, dict):
                continue
            if msg.get("role") != "assistant":
                continue
            ts = evt.get("timestamp")
            if not isinstance(ts, str) or ts < since_iso:
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            # Skip "empty" usage payloads (some early assistant turns
            # carry an empty {} so there's nothing to charge).
            total = (
                int(usage.get("input") or 0)
                + int(usage.get("output") or 0)
                + int(usage.get("cacheRead") or 0)
                + int(usage.get("cacheWrite") or 0)
            )
            if total <= 0:
                continue
            model = str(msg.get("model") or "")
            yield ts, model, usage


def _open_db(db_path: Path) -> sqlite3.Connection:
    """Open the billing SQLite with the same pragmas the live backend uses."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _already_recorded(
    conn: sqlite3.Connection, session_id: str, ts: str
) -> bool:
    """A row with the same (session_id, ts) means we've already
    backfilled (or live-billed) this turn. Idempotency guard."""
    row = conn.execute(
        "SELECT 1 FROM cost_events WHERE session_id = ? AND ts = ? LIMIT 1",
        (session_id, ts),
    ).fetchone()
    return row is not None


def _insert_event(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    ts: str,
    source: str,
    tool: Optional[str],
    model: str,
    session_id: str,
    workspace_id: str,
    usage: dict[str, Any],
    cost_usd: float,
    breakdown: dict[str, float],
) -> None:
    """Mirror of CreditLedger._persist_event but with caller-supplied ts."""
    conn.execute(
        "INSERT INTO cost_events (user_id, ts, source, tool, model, "
        "session_id, workspace_id, input_tokens, output_tokens, "
        "cache_read, cache_write, cost_usd, breakdown_json) VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            user_id,
            ts,
            source,
            tool,
            model,
            session_id,
            workspace_id,
            int(usage.get("input") or 0),
            int(usage.get("output") or 0),
            int(usage.get("cacheRead") or 0),
            int(usage.get("cacheWrite") or 0),
            float(cost_usd),
            json.dumps(breakdown),
        ),
    )


def _recompute_monthly_spend(conn: sqlite3.Connection) -> int:
    """Rebuild monthly_spend from the (now-correct) cost_events table.

    Returns the number of (user_id, month) buckets updated. Safe to run
    against a partially-correct ledger: it just replaces the aggregate
    with whatever cost_events says, which is the source of truth.
    """
    rows = conn.execute(
        """
        SELECT user_id, substr(ts, 1, 7) AS month,
               SUM(cost_usd) AS spent_usd,
               COUNT(*)      AS prompts
        FROM cost_events
        GROUP BY user_id, month
        """
    ).fetchall()
    for user_id, month, spent_usd, prompts in rows:
        conn.execute(
            "INSERT INTO monthly_spend (user_id, month, spent_usd, prompts) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, month) DO UPDATE SET "
            "spent_usd = excluded.spent_usd, prompts = excluded.prompts",
            (user_id, month, float(spent_usd or 0.0), int(prompts or 0)),
        )
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--since",
        default="2026-05-11",
        help="Only backfill turns with timestamp >= this ISO date "
        "(default: 2026-05-11, the day the regression shipped).",
    )
    grp = ap.add_mutually_exclusive_group(required=False)
    grp.add_argument(
        "--dry-run",
        action="store_true",
        help="Default. Print what would happen, don't write to the DB.",
    )
    grp.add_argument(
        "--apply",
        action="store_true",
        help="Actually INSERT rows + recompute monthly_spend.",
    )
    ap.add_argument(
        "--data-root",
        default=None,
        help="Path to PI_DATA_ROOT (e.g. /srv/pi/data). Defaults to "
        "$PI_DATA_ROOT or ../data relative to this script.",
    )
    args = ap.parse_args()

    apply = bool(args.apply)
    since_iso = args.since.strip()
    if "T" not in since_iso:
        since_iso = f"{since_iso}T00:00:00.000Z"

    if args.data_root:
        data_root = Path(args.data_root)
    elif os.environ.get("PI_DATA_ROOT", "").strip():
        data_root = Path(os.environ["PI_DATA_ROOT"].strip())
    else:
        data_root = Path(__file__).resolve().parents[2] / "data"

    chats_root = data_root / "chats"
    registry_path = data_root / "registry.json"
    db_path = data_root / "billing.db"

    print(f"data_root  : {data_root}")
    print(f"chats_root : {chats_root}")
    print(f"registry   : {registry_path}")
    print(f"billing.db : {db_path}")
    print(f"since      : {since_iso}")
    print(f"mode       : {'APPLY' if apply else 'DRY-RUN'}")
    print()

    if not chats_root.exists():
        raise SystemExit(f"chats_root does not exist: {chats_root}")
    if not db_path.exists():
        raise SystemExit(f"billing.db does not exist: {db_path}")

    registry = _load_registry(registry_path)
    conn = _open_db(db_path)

    sessions = sorted(p for p in chats_root.iterdir() if p.is_dir())
    print(f"scanning {len(sessions)} session dirs...")

    total_eligible = 0
    total_inserted = 0
    total_skipped_dup = 0
    total_unresolved = 0
    per_user: dict[str, dict[str, float]] = {}

    for sdir in sessions:
        meta = _resolve_session_meta(sdir, registry)
        if meta is None:
            total_unresolved += 1
            continue
        for jsonl in sorted(sdir.glob("*.jsonl")):
            for ts, model, usage in _iter_assistant_turns(jsonl, since_iso):
                total_eligible += 1
                if _already_recorded(conn, meta.session_id, ts):
                    total_skipped_dup += 1
                    continue
                # Wall-seconds=0: we don't have a reliable wall-clock
                # for backfilled turns, so VM amortisation is 0. The
                # LLM cost (which dominates) is correct.
                cost = _estimate_cost(
                    usage, model_id=model, wall_seconds=0.0
                )
                if apply:
                    _insert_event(
                        conn,
                        user_id=meta.user_id,
                        ts=ts,
                        source="chat",
                        tool=None,
                        model=cost.model_id,
                        session_id=meta.session_id,
                        workspace_id=meta.workspace_id,
                        usage=usage,
                        cost_usd=cost.total_usd,
                        breakdown={
                            "llm_usd": cost.llm_usd,
                            "vm_usd": cost.vm_usd,
                            "margin_usd": cost.margin_usd,
                            "total_usd": cost.total_usd,
                            "backfilled": 1.0,
                        },
                    )
                total_inserted += 1
                bucket = per_user.setdefault(
                    meta.user_id,
                    {"events": 0.0, "cost_usd": 0.0},
                )
                bucket["events"] += 1
                bucket["cost_usd"] += cost.total_usd

    if apply:
        conn.commit()
        buckets = _recompute_monthly_spend(conn)
        conn.commit()
        print(f"\nrecomputed monthly_spend buckets: {buckets}")

    print()
    print(f"eligible events scanned  : {total_eligible}")
    print(f"already-recorded skipped : {total_skipped_dup}")
    print(f"unresolved session dirs  : {total_unresolved}")
    print(f"rows {'inserted' if apply else 'WOULD insert'} : {total_inserted}")
    print()
    if per_user:
        print(f"per-user{' (proposed)' if not apply else ''}:")
        for uid, b in sorted(per_user.items(), key=lambda x: -x[1]['cost_usd']):
            print(f"  {uid}  {int(b['events']):6d} events  ${b['cost_usd']:>10.4f}")
    if not apply:
        print("\nDry-run only. Re-run with --apply to actually write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
