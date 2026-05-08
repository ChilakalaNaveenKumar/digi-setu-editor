"""
BYOK usage ledger — desktop only.

When a chat is routed through the user's own AI provider keys (BYOK),
no usage event lands in :mod:`services.billing.CreditLedger` because
nothing is being billed against a Digi Setu subscription. The Activity
page would otherwise show "0 events" forever and the user would have
no way to see what their machine has been spending against their own
quota.

This module records a tiny per-turn row in
``$DATA_ROOT/usage.sqlite`` (i.e. ``~/.digi-setu/usage.sqlite`` on
desktop). The row is purely token counts — we deliberately do NOT
record cost in USD because we don't know the user's actual price (it
depends on their tier, batch discount, region, …). The frontend
displays "0.0 / 0.0 Mtok" rollups and links the user to their AI
provider's dashboard for the real $ figure.

Schema (auto-created on first write):

    CREATE TABLE byok_events (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ts              TEXT NOT NULL,             -- ISO-8601 UTC
        session_id      TEXT NOT NULL,
        workspace_id    TEXT NOT NULL,
        provider        TEXT NOT NULL,             -- "anthropic" / "google" / …
        model_id        TEXT NOT NULL,             -- "claude-sonnet-4-6" / …
        input_tokens    INTEGER NOT NULL DEFAULT 0,
        output_tokens   INTEGER NOT NULL DEFAULT 0,
        cache_read      INTEGER NOT NULL DEFAULT 0,
        cache_write     INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX byok_events_ts ON byok_events (ts);

Why SQLite (vs JSONL or in-memory): the activity page renders
aggregates ("today / 7-day / 30-day") and per-day breakdowns. With
JSONL we'd have to re-scan + parse every page load. SQLite + an
index on `ts` keeps that O(rows-in-window) and the file is still
trivially user-readable (sqlite3 CLI ships with macOS).
"""

from __future__ import annotations

import datetime
import sqlite3
import sys
import threading
from pathlib import Path
from typing import Any, Iterable, Optional

from config import DATA_ROOT


_DB_PATH = DATA_ROOT / "usage.sqlite"
_init_lock = threading.Lock()
_initialised = False


def _conn() -> sqlite3.Connection:
    """Open a connection to the BYOK ledger. We open one per call
    (rather than a long-lived shared connection) because the writer
    is FastAPI's threadpool — sqlite3 connections are not thread
    safe and the per-call cost is negligible vs. an LLM round-trip."""
    _ensure_schema()
    conn = sqlite3.connect(_DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema() -> None:
    global _initialised
    if _initialised:
        return
    with _init_lock:
        if _initialised:
            return
        try:
            _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(_DB_PATH, isolation_level=None)
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS byok_events (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts              TEXT    NOT NULL,
                        session_id      TEXT    NOT NULL,
                        workspace_id    TEXT    NOT NULL,
                        provider        TEXT    NOT NULL,
                        model_id        TEXT    NOT NULL,
                        input_tokens    INTEGER NOT NULL DEFAULT 0,
                        output_tokens   INTEGER NOT NULL DEFAULT 0,
                        cache_read      INTEGER NOT NULL DEFAULT 0,
                        cache_write     INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS byok_events_ts "
                    "ON byok_events (ts)"
                )
            finally:
                conn.close()
            _initialised = True
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[byok_usage] WARN: schema init failed at {_DB_PATH}: {exc}",
                file=sys.stderr,
            )


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def record(
    *,
    session_id: str,
    workspace_id: str,
    provider: str,
    model_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
) -> None:
    """Persist a BYOK turn. Failures are non-fatal (logged + ignored)
    — the chat must keep working even if the local ledger is wedged
    on a read-only filesystem or out of disk."""
    if not session_id or not model_id:
        return
    if (
        input_tokens <= 0
        and output_tokens <= 0
        and cache_read <= 0
        and cache_write <= 0
    ):
        # Don't record empty rows — pi sometimes emits placeholder
        # `_bill` events with 0 tokens at session start.
        return
    try:
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO byok_events (
                    ts, session_id, workspace_id, provider, model_id,
                    input_tokens, output_tokens, cache_read, cache_write
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now_iso(),
                    session_id,
                    workspace_id,
                    provider,
                    model_id,
                    int(input_tokens),
                    int(output_tokens),
                    int(cache_read),
                    int(cache_write),
                ),
            )
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[byok_usage] WARN: record failed: {exc}", file=sys.stderr)


def recent_events(limit: int = 200, since_iso: Optional[str] = None) -> list[dict[str, Any]]:
    """Most recent rows (newest first), paginated by `limit`. `since_iso`
    is exclusive — passing the timestamp of the most recent row returns
    only newer entries (useful for incremental polling)."""
    sql = (
        "SELECT ts, session_id, workspace_id, provider, model_id, "
        "input_tokens, output_tokens, cache_read, cache_write "
        "FROM byok_events"
    )
    args: list[Any] = []
    if since_iso:
        sql += " WHERE ts > ?"
        args.append(since_iso)
    sql += " ORDER BY ts DESC LIMIT ?"
    args.append(int(limit))
    try:
        with _conn() as conn:
            rows = conn.execute(sql, args).fetchall()
    except Exception as exc:  # pragma: no cover
        print(f"[byok_usage] WARN: recent_events failed: {exc}", file=sys.stderr)
        return []
    return [dict(r) for r in rows]


def summary(*, since_iso: Optional[str] = None) -> dict[str, Any]:
    """Aggregate counts since `since_iso` (or all-time if None).
    Returns total tokens + per-model breakdown so the Activity page
    can show "you've used X tokens via your key this month"."""
    where = ""
    args: list[Any] = []
    if since_iso:
        where = "WHERE ts > ?"
        args.append(since_iso)
    try:
        with _conn() as conn:
            total = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS turns,
                    COALESCE(SUM(input_tokens), 0)  AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(cache_read), 0)    AS cache_read,
                    COALESCE(SUM(cache_write), 0)   AS cache_write
                FROM byok_events {where}
                """,
                args,
            ).fetchone()
            per_model = conn.execute(
                f"""
                SELECT
                    model_id,
                    provider,
                    COUNT(*) AS turns,
                    COALESCE(SUM(input_tokens), 0)  AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens
                FROM byok_events {where}
                GROUP BY model_id, provider
                ORDER BY turns DESC
                """,
                args,
            ).fetchall()
    except Exception as exc:  # pragma: no cover
        print(f"[byok_usage] WARN: summary failed: {exc}", file=sys.stderr)
        return {"total": {}, "per_model": []}
    return {
        "total": dict(total) if total else {},
        "per_model": [dict(r) for r in per_model],
    }


def db_path() -> Path:
    """Where the file actually lives. Useful for diagnostics."""
    return _DB_PATH
