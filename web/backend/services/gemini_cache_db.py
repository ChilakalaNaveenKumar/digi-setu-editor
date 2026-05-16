"""
SQLite-backed registry + idle-eviction sweeper for Vertex Gemini
``cachedContents`` resources.

Why a DB layer at all?
----------------------
The May 2026 cost spike came from a process-local registry: each
backend worker held its own ``_caches`` dict, looked up ``displayName``
matches against ``cachedContents.list``, and adopted-or-created.
That worked AS LONG AS the list response was correct — but Vertex's
list endpoint is eventually consistent (a freshly-created cache
takes 5–30 s to show up), so two parallel cold-miss workers would
each create their own resource, both win the race, both think they
adopted, and storage got billed for both. Times 14 redeploys/day,
times 7 packages, times the 24 h TTL the old code used. Hello $1k/day.

This module makes the **DB the single source of truth** for which
caches we own, when they were last touched, and when they should
die. Every worker reads/writes through the same SQLite file — so
two parallel cold-miss workers see the same row and converge on
one cache. The Vertex ``list`` endpoint is now only consulted on
boot reconciliation, not on the hot path.

Lifecycle:

  1. **Hot path** (``get`` / ``touch``): the lookup is a SQLite
     primary-key read. ``last_used_at`` is bumped on every hit so
     the sweeper knows what's still in active use.
  2. **Create path** (``record_created``): when ``gemini_cache``
     successfully creates a new Vertex cache it inserts a row with
     ``cache_name`` (the full Vertex resource path), the wall-clock
     ``expires_at`` from the API response, and ``last_used_at = now``.
  3. **Sweeper** (background asyncio task): every
     ``SWEEPER_INTERVAL_S`` seconds it scans the DB for rows with
     ``last_used_at < now - IDLE_TTL_S`` OR ``expires_at < now``,
     issues a Vertex ``DELETE`` for each, and removes the row.
  4. **Reconcile** (boot-time once): list Vertex's actual cache
     resources matching our ``displayName`` pattern, and add any
     we don't know about (so the steady-state DB never lies about
     which caches are billable).

Multi-worker safety
-------------------
Multiple Uvicorn workers can each schedule the sweeper. We avoid
duplicate work by storing a coarse "sweeper lease" row: a worker
only runs a sweep cycle if the last sweep is older than 80 % of
the interval. SQLite's atomic ``ON CONFLICT`` makes this race-free
without any cross-process locking.

Privacy / cost
--------------
The DB stores the cache *resource name* (a Vertex-internal id),
the package, and timestamps. No corpus content, no user query,
no token. Storage is dominated by the Vertex side; this table is
~7 rows in steady state.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterator, Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_epoch() -> float:
    """Wall-clock seconds since epoch. We use wall time (not monotonic)
    because every worker process maintains its own monotonic baseline
    and they have to compare timestamps across processes."""
    return time.time()


# ── Tunables (env-overridable) ───────────────────────────────────────
def _idle_ttl_s() -> int:
    """How long a cache may sit unused before the sweeper kills it.

    Default: 1 hour. The user's stated requirement is "if cache 1
    isn't touched for an hour, delete it" — this is the floor.
    Setting this too aggressive (< 600 s) makes the create-overhead
    of a fresh cache eat the input-discount savings; we clamp to a
    sane minimum.
    """
    raw = (os.environ.get("PI_TYPST_CACHE_IDLE_TTL_S") or "").strip()
    if raw and raw.isdigit():
        return max(600, int(raw))
    return 3_600


def _sweeper_interval_s() -> int:
    """How often the background sweeper runs.

    Default: 600 s (10 min). Frequent enough that a cache idle for
    1 h gets killed within ~10 min of the deadline (so worst-case
    storage waste is ~10 min of post-idle billing per cache).
    """
    raw = (os.environ.get("PI_TYPST_CACHE_SWEEP_INTERVAL_S") or "").strip()
    if raw and raw.isdigit():
        return max(60, int(raw))
    return 600


# ── DB path ──────────────────────────────────────────────────────────
_OVERRIDE = os.environ.get("GEMINI_CACHE_DB_PATH", "").strip()
if _OVERRIDE:
    _DB_PATH = Path(_OVERRIDE).expanduser().resolve()
else:
    from config import DATA_ROOT
    _DB_PATH = (DATA_ROOT / "gemini_cache.db").resolve()


_LOCK = threading.Lock()
_INITIALISED = False


def _connect() -> sqlite3.Connection:
    """Open + ensure schema. Idempotent — every call validates the
    schema (``IF NOT EXISTS``) so a fresh install on a new VM works
    from the first request without an explicit migration step."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(_DB_PATH),
        check_same_thread=False,
        isolation_level=None,  # autocommit; we batch via transactions ourselves
    )
    try:
        os.chmod(_DB_PATH, 0o600)
        for sibling in (
            _DB_PATH.with_suffix(_DB_PATH.suffix + "-wal"),
            _DB_PATH.with_suffix(_DB_PATH.suffix + "-shm"),
        ):
            if sibling.exists():
                os.chmod(sibling, 0o600)
    except OSError:
        pass
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gemini_caches (
            package         TEXT    PRIMARY KEY,
            cache_name      TEXT    NOT NULL,         -- projects/.../cachedContents/{id}
            display_name    TEXT    NOT NULL,         -- typst-docs-{package}-v1
            model_id        TEXT    NOT NULL,
            created_at      TEXT    NOT NULL,         -- ISO-8601 UTC
            last_used_at    TEXT    NOT NULL,         -- bumped on every hit
            last_used_epoch REAL    NOT NULL,         -- duplicate epoch for cheap ORDER BY / WHERE
            expires_at      TEXT,                     -- Vertex-side TTL, ISO-8601 UTC
            expires_epoch   REAL,                     -- duplicate epoch for cheap WHERE
            created_pid     INTEGER NOT NULL          -- worker PID that minted the row, debug aid
        );
        CREATE INDEX IF NOT EXISTS idx_gemini_caches_last_used
            ON gemini_caches(last_used_epoch);
        CREATE INDEX IF NOT EXISTS idx_gemini_caches_expires
            ON gemini_caches(expires_epoch);

        -- Audit log of evictions (sweeper actions, manual purges,
        -- replacements). One row per delete attempt, kept indefinitely
        -- so an operator can reconstruct "why did this cache go away?"
        -- months later. Tiny — bounded by eviction rate, not by query
        -- volume.
        CREATE TABLE IF NOT EXISTS gemini_cache_evictions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT    NOT NULL,
            package      TEXT,
            cache_name   TEXT    NOT NULL,
            reason       TEXT    NOT NULL,           -- 'idle' | 'expired' | 'manual' | 'reconcile-orphan' | 'duplicate'
            ok           INTEGER NOT NULL DEFAULT 1, -- 0 if Vertex DELETE failed
            error        TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_gemini_cache_evictions_ts
            ON gemini_cache_evictions(ts DESC);

        -- Sweeper lease — single row, key='sweeper'. Tracks the last
        -- time SOME worker successfully ran a sweep cycle so other
        -- workers can defer instead of stampeding Vertex's API.
        CREATE TABLE IF NOT EXISTS gemini_cache_runtime (
            key          TEXT    PRIMARY KEY,
            value        TEXT    NOT NULL,
            updated_at   TEXT    NOT NULL,
            updated_epoch REAL   NOT NULL
        );
        """
    )
    return conn


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    global _INITIALISED
    with _LOCK:
        conn = _connect()
        _INITIALISED = True
        try:
            yield conn
        finally:
            conn.close()


# ── Hot-path lookups ─────────────────────────────────────────────────


def lookup(package: str) -> Optional[dict[str, Any]]:
    """Return the live row for ``package`` or ``None``.

    This is THE hot-path call: every search_docs request issues
    one of these. SQLite indexed-PK reads run in ~30 µs on the
    persistent volume, so this is effectively free compared to
    the network round-trips it replaces.
    """
    with _db() as conn:
        row = conn.execute(
            """
            SELECT package, cache_name, display_name, model_id, created_at,
                   last_used_at, last_used_epoch, expires_at, expires_epoch,
                   created_pid
            FROM gemini_caches
            WHERE package = ?
            """,
            (package,),
        ).fetchone()
    return dict(row) if row else None


def touch(package: str) -> None:
    """Record a usage hit. Bumps ``last_used_at`` so the sweeper
    treats this cache as still in active use. Cheap (one indexed
    UPDATE) — call this on every successful cache hit.

    No-ops if the row is missing, so a race between the sweeper
    deleting a row and the caller touching it is benign — the
    next call falls through to create a fresh cache, which is the
    correct behaviour.
    """
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    with _db() as conn:
        conn.execute(
            """
            UPDATE gemini_caches
            SET last_used_at = ?, last_used_epoch = ?
            WHERE package = ?
            """,
            (now_iso, now_epoch, package),
        )


def record_created(
    *,
    package: str,
    cache_name: str,
    display_name: str,
    model_id: str,
    expires_at_iso: Optional[str],
    expires_at_epoch: Optional[float],
) -> None:
    """Insert (or replace) a row after a successful Vertex create.

    REPLACE semantics rather than INSERT-OR-IGNORE because if the
    row exists with a stale ``cache_name`` (pointing at a Vertex
    resource we couldn't reach) we want the new ``cache_name`` to
    win. The old resource is leaked for at most one sweep cycle —
    the next sweep's reconcile pass will find it as an orphan and
    delete it.
    """
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO gemini_caches (
                package, cache_name, display_name, model_id,
                created_at, last_used_at, last_used_epoch,
                expires_at, expires_epoch, created_pid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(package) DO UPDATE SET
                cache_name      = excluded.cache_name,
                display_name    = excluded.display_name,
                model_id        = excluded.model_id,
                created_at      = excluded.created_at,
                last_used_at    = excluded.last_used_at,
                last_used_epoch = excluded.last_used_epoch,
                expires_at      = excluded.expires_at,
                expires_epoch   = excluded.expires_epoch,
                created_pid     = excluded.created_pid
            """,
            (
                package, cache_name, display_name, model_id,
                now_iso, now_iso, now_epoch,
                expires_at_iso, expires_at_epoch,
                int(os.getpid()),
            ),
        )


def remove(package: str) -> Optional[dict[str, Any]]:
    """Drop the row for ``package`` from the registry and return
    its previous state (or None). Caller is responsible for the
    Vertex-side DELETE — this only touches local state.
    """
    with _db() as conn:
        row = conn.execute(
            "SELECT package, cache_name FROM gemini_caches WHERE package = ?",
            (package,),
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM gemini_caches WHERE package = ?", (package,))
    return dict(row)


def list_all() -> list[dict[str, Any]]:
    """Snapshot every row in the registry, most-recently-used first.
    Used by the admin endpoint and the sweeper's "what should I
    look at" pass."""
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT package, cache_name, display_name, model_id,
                   created_at, last_used_at, last_used_epoch,
                   expires_at, expires_epoch, created_pid
            FROM gemini_caches
            ORDER BY last_used_epoch DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def find_idle(idle_ttl_s: Optional[int] = None) -> list[dict[str, Any]]:
    """Return rows that have not been touched within ``idle_ttl_s``
    seconds OR whose Vertex-side TTL has expired. These are the
    sweeper's eviction candidates.
    """
    now = _now_epoch()
    cutoff = now - (idle_ttl_s if idle_ttl_s is not None else _idle_ttl_s())
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT package, cache_name, display_name, model_id,
                   created_at, last_used_at, last_used_epoch,
                   expires_at, expires_epoch, created_pid
            FROM gemini_caches
            WHERE last_used_epoch < ?
               OR (expires_epoch IS NOT NULL AND expires_epoch < ?)
            ORDER BY last_used_epoch ASC
            """,
            (cutoff, now),
        ).fetchall()
    return [dict(r) for r in rows]


def record_eviction(
    *,
    package: Optional[str],
    cache_name: str,
    reason: str,
    ok: bool,
    error: Optional[str] = None,
) -> None:
    """Append one row to the eviction audit log."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO gemini_cache_evictions
                (ts, package, cache_name, reason, ok, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (_now_iso(), package, cache_name, reason, 1 if ok else 0, error),
        )


def list_evictions(limit: int = 100) -> list[dict[str, Any]]:
    """Tail the eviction log for the admin UI / debugging."""
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id, ts, package, cache_name, reason, ok, error
            FROM gemini_cache_evictions
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(1000, int(limit))),),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Sweeper lease ────────────────────────────────────────────────────


def claim_sweeper_lease(now_epoch: Optional[float] = None) -> bool:
    """Atomically claim the sweeper lease. Returns ``True`` if this
    caller is allowed to run a sweep cycle (i.e. no other worker
    has run one within ``80 % * SWEEPER_INTERVAL_S``).

    Implementation: the ``gemini_cache_runtime`` row stores the
    epoch of the last successful sweep. We do an UPDATE...WHERE
    (epoch + threshold < new_epoch) which SQLite makes atomic on
    a single connection. ``rowcount > 0`` means we won the race.

    Workers that lose the race no-op; they don't queue or retry.
    The next interval tick gives someone else a fair shot.
    """
    if now_epoch is None:
        now_epoch = _now_epoch()
    threshold = _sweeper_interval_s() * 0.8
    cutoff = now_epoch - threshold
    now_iso = _now_iso()
    with _db() as conn:
        # Ensure the row exists. INSERT-OR-IGNORE so concurrent first
        # boots don't 422 each other.
        conn.execute(
            """
            INSERT OR IGNORE INTO gemini_cache_runtime
                (key, value, updated_at, updated_epoch)
            VALUES ('sweeper', '0', '1970-01-01T00:00:00+00:00', 0)
            """
        )
        cur = conn.execute(
            """
            UPDATE gemini_cache_runtime
            SET value = ?, updated_at = ?, updated_epoch = ?
            WHERE key = 'sweeper' AND updated_epoch < ?
            """,
            (str(int(now_epoch)), now_iso, now_epoch, cutoff),
        )
        return (cur.rowcount or 0) > 0


def last_sweep_at() -> Optional[float]:
    """Read the last sweep timestamp without claiming the lease.
    Used by health checks ("is the sweeper running?") and tests.
    """
    with _db() as conn:
        row = conn.execute(
            "SELECT updated_epoch FROM gemini_cache_runtime WHERE key = 'sweeper'"
        ).fetchone()
    if row is None:
        return None
    val = row["updated_epoch"]
    return float(val) if val is not None else None


# ── Sweeper task ─────────────────────────────────────────────────────

# Type alias: a coroutine that, given a Vertex resource name, deletes
# it and returns (ok, optional_error_message). The sweeper module
# itself has no httpx dependency — gemini_cache.py owns that surface
# and injects this callback at start time.
DeleteCallback = Callable[[str], Awaitable[tuple[bool, Optional[str]]]]
ReconcileCallback = Callable[[], Awaitable[list[dict[str, Any]]]]


_SWEEPER_TASK: Optional[asyncio.Task[None]] = None


def is_sweeper_running() -> bool:
    return _SWEEPER_TASK is not None and not _SWEEPER_TASK.done()


async def _run_sweep_once(
    *, delete: DeleteCallback, reconcile: Optional[ReconcileCallback] = None,
) -> dict[str, int]:
    """Run one sweep cycle.

    Steps:
      1. Try to claim the lease. If another worker swept recently,
         no-op and return zero counters.
      2. Look up idle / expired rows from the DB.
      3. For each, call ``delete(cache_name)``. On success, drop
         the row + audit-log it. On failure, leave the row alone so
         the next cycle retries (and audit-log the failure).
      4. If a ``reconcile`` callback was provided, ask it for the
         project's actual Vertex caches matching our displayName
         pattern and delete any that aren't in the DB (orphans
         from before the DB existed, or caches another tenant left
         behind).

    Returns a counters dict for the admin endpoint.
    """
    if not claim_sweeper_lease():
        return {"swept": 0, "deleted": 0, "errors": 0, "orphans": 0, "skipped_lease": 1}

    counters = {"swept": 0, "deleted": 0, "errors": 0, "orphans": 0, "skipped_lease": 0}

    candidates = find_idle()
    counters["swept"] = len(candidates)
    for row in candidates:
        cache_name = row["cache_name"]
        package = row["package"]
        # Reason picked from the data: idle vs expired vs both.
        now = _now_epoch()
        reasons = []
        if row.get("last_used_epoch") is not None:
            if (now - float(row["last_used_epoch"])) >= _idle_ttl_s():
                reasons.append("idle")
        if row.get("expires_epoch") is not None and float(row["expires_epoch"]) < now:
            reasons.append("expired")
        reason = "+".join(reasons) or "idle"

        try:
            ok, err = await delete(cache_name)
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            ok, err = False, str(exc)

        if ok:
            counters["deleted"] += 1
            remove(package)
            record_eviction(
                package=package, cache_name=cache_name,
                reason=reason, ok=True,
            )
            logger.info(
                "[gemini-cache-sweeper] evicted %s for %s (%s)",
                cache_name.split("/")[-1], package, reason,
            )
        else:
            counters["errors"] += 1
            record_eviction(
                package=package, cache_name=cache_name,
                reason=reason, ok=False, error=err,
            )
            logger.warning(
                "[gemini-cache-sweeper] eviction FAILED for %s (%s): %s",
                package, cache_name.split("/")[-1], err,
            )

    # Reconcile pass — find Vertex-side caches we don't know about
    # and delete them. Skipped if no callback provided (tests, or
    # ops mode where reconcile is intentionally disabled).
    if reconcile is not None:
        try:
            vertex_caches = await reconcile()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[gemini-cache-sweeper] reconcile failed: %s", exc)
            vertex_caches = []

        known = {row["cache_name"] for row in list_all()}
        for raw in vertex_caches:
            name = raw.get("name") if isinstance(raw, dict) else None
            if not name or not isinstance(name, str):
                continue
            if name in known:
                continue
            counters["orphans"] += 1
            try:
                ok, err = await delete(name)
            except Exception as exc:  # noqa: BLE001
                ok, err = False, str(exc)
            record_eviction(
                package=None, cache_name=name,
                reason="reconcile-orphan", ok=ok, error=err,
            )
            if ok:
                counters["deleted"] += 1
                logger.info(
                    "[gemini-cache-sweeper] reconcile killed orphan %s",
                    name.split("/")[-1],
                )
            else:
                counters["errors"] += 1
                logger.warning(
                    "[gemini-cache-sweeper] orphan delete FAILED %s: %s", name, err,
                )

    return counters


async def _sweeper_loop(
    *, delete: DeleteCallback, reconcile: Optional[ReconcileCallback],
) -> None:
    """Forever-running sweeper. Sleeps ``SWEEPER_INTERVAL_S`` between
    cycles. Cancellation propagates cleanly via ``asyncio.CancelledError``.
    """
    interval = _sweeper_interval_s()
    logger.info(
        "[gemini-cache-sweeper] starting (interval=%ds, idle_ttl=%ds)",
        interval, _idle_ttl_s(),
    )
    # Stagger initial wait so multi-worker boots don't all hit at t=0.
    try:
        await asyncio.sleep(min(30.0, interval / 4))
    except asyncio.CancelledError:
        return
    while True:
        try:
            await _run_sweep_once(delete=delete, reconcile=reconcile)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Sweeper bugs must not take down the lifespan. Log + retry.
            logger.exception("[gemini-cache-sweeper] cycle crashed: %s", exc)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return


def start_sweeper(
    *, delete: DeleteCallback, reconcile: Optional[ReconcileCallback] = None,
) -> None:
    """Schedule the sweeper as a long-running asyncio task. Idempotent
    — calling twice in the same loop is a no-op.

    The caller injects ``delete`` (and optionally ``reconcile``) so
    the sweeper module stays free of the httpx / Vertex dependency
    chain — testable in isolation, and the production module
    (``gemini_cache``) stays the only thing that knows the auth token.
    """
    global _SWEEPER_TASK
    if is_sweeper_running():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "[gemini-cache-sweeper] no running loop; sweeper not started"
        )
        return
    _SWEEPER_TASK = loop.create_task(_sweeper_loop(delete=delete, reconcile=reconcile))


async def stop_sweeper() -> None:
    """Cancel the running sweeper task. Awaitable so callers can
    block on cleanup if they want a clean shutdown."""
    global _SWEEPER_TASK
    if _SWEEPER_TASK is None:
        return
    task = _SWEEPER_TASK
    _SWEEPER_TASK = None
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):  # noqa: BLE001
        pass


# ── Test hooks ───────────────────────────────────────────────────────


def db_path() -> Path:
    """Where does the registry live? Used by tests to point at a
    scratch path and verify the sweeper end-to-end."""
    return _DB_PATH


def _reset_for_tests() -> None:
    """Wipe state. Tests call this between cases."""
    global _SWEEPER_TASK
    _SWEEPER_TASK = None
    with _db() as conn:
        conn.execute("DELETE FROM gemini_caches")
        conn.execute("DELETE FROM gemini_cache_evictions")
        conn.execute("DELETE FROM gemini_cache_runtime")


# Public sweeper hook for the synchronous "run one cycle now" admin
# endpoint — useful when an operator wants to force-evict idle
# caches without waiting for the next interval.
async def run_sweep_now(
    *, delete: DeleteCallback, reconcile: Optional[ReconcileCallback] = None,
) -> dict[str, int]:
    """Run exactly one sweep cycle without scheduling the loop.
    Bypasses the lease check by clearing it first — admin POST
    to ``/api/admin/gemini-caches/sweep`` calls this when an
    operator wants an immediate pass.
    """
    # Reset the lease so this synchronous call always wins. The
    # underlying ``_run_sweep_once`` then re-claims it cleanly.
    with _db() as conn:
        conn.execute(
            """
            UPDATE gemini_cache_runtime
            SET updated_epoch = 0
            WHERE key = 'sweeper'
            """
        )
    return await _run_sweep_once(delete=delete, reconcile=reconcile)
