"""
Desktop install + version telemetry.

Two questions this module exists to answer:

  1. Who downloaded the desktop app, when, and which build?
  2. Of those who installed it, who is *still running it*, and on
     which version (so we can show "an update is available" both
     in-app and on a future "Devices" page in the web account)?

Neither question is currently answerable. The web Download.vue page
links straight to a Caddy-served static .dmg/.exe — there's no
authentication, no logging, and after the user runs the installer
the cloud has no idea whether the binary on their machine is fresh
or 8 versions stale until they happen to call /api/usage and we
sniff the User-Agent.

Design
------
* **Authenticated downloads.** The Download.vue page only renders
  the "Download" button to signed-in users. On click the SPA hits
  ``POST /api/desktop/track-download`` (see routes/desktop.py),
  which records the event here and returns the static URL. Caddy
  still serves the bytes; we just gate the *intent*. Bandwidth on
  Caddy is cheap — the goal isn't to throttle, it's to know.

* **Per-install heartbeats.** When the desktop sidecar boots it
  generates (or re-uses) a ``install_id`` UUID stored under
  ``$DIGI_SETU_HOME/install_id`` and POSTs to
  ``/api/desktop/heartbeat`` with ``{install_id, version, platform}``.
  We store the latest heartbeat per ``(user_id, install_id)`` so a
  user with three machines shows up as three rows, each tagged
  with its own running version.

* **Latest-version pointer.** The cloud holds the canonical "what's
  the newest desktop release" string in ``latest_version`` (a
  one-row table). The Download.vue banner reads it from
  ``GET /api/desktop/latest-version`` so the website never lies
  about what the auto-updater will deliver. The pointer is bumped
  by ``deploy/scripts/release-desktop.sh`` (and a manual SQL upsert
  works in a pinch).

DB sizing
---------
``desktop_installs`` grows by one row per download click — small
even on a viral month. ``desktop_clients`` is keyed on
``(user_id, install_id)`` and is upserted on every heartbeat, so
its size is bounded by the number of *distinct installs*, not by
heartbeat frequency. We could co-tenant this table inside
``billing.db`` but billing.py owns its file and adding a new
schema mid-flight tends to break its `ALTER TABLE`-allergic boot
hook. Cheaper to give telemetry its own ``desktop_telemetry.db``
and let the two evolve independently.

Privacy
-------
We log:
  * user_id (Clerk sub, the same identifier billing.py keeps)
  * version, platform, install_id
  * the request IP and user-agent (truncated to 200 chars)
  * timestamps (UTC ISO-8601)

We do NOT log: file paths, workspace contents, chat messages, AI
prompts. The download endpoint is the only user-supplied input,
and the SPA only sends ``platform`` + ``version`` from the page —
no user payload reaches the telemetry tables.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# Resolve at import time. Same DATA_ROOT pattern billing.py uses; staging
# operators can override with ``DESKTOP_TELEMETRY_DB_PATH`` for one-off
# diagnostics that don't want to touch the live DB.
_OVERRIDE = os.environ.get("DESKTOP_TELEMETRY_DB_PATH", "").strip()
if _OVERRIDE:
    _DB_PATH = Path(_OVERRIDE).expanduser().resolve()
else:
    from config import DATA_ROOT
    _DB_PATH = (DATA_ROOT / "desktop_telemetry.db").resolve()


_LOCK = threading.Lock()
_INITIALISED = False


def _connect() -> sqlite3.Connection:
    """Connect + ensure schema. Idempotent — every call validates the
    schema (``IF NOT EXISTS``) so a fresh install on a new VM works
    from the first request without an explicit migration step."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(_DB_PATH),
        check_same_thread=False,
        isolation_level=None,  # autocommit; we batch via transactions ourselves
    )
    # Lock down to 0600 right away. SQLite respects the process umask
    # which is often 0022; a world-readable telemetry DB lets any
    # subprocess on the box (including the sandboxed AI uid in our
    # dual-uid model) `cat` user_ids and IPs. Same hardening pattern as
    # services/billing.py — see that module for the full rationale.
    try:
        os.chmod(_DB_PATH, 0o600)
        for sibling in (
            _DB_PATH.with_suffix(_DB_PATH.suffix + "-wal"),
            _DB_PATH.with_suffix(_DB_PATH.suffix + "-shm"),
        ):
            if sibling.exists():
                os.chmod(sibling, 0o600)
    except OSError:
        # Dev laptop without root; warn-and-continue keeps tests green.
        pass
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS desktop_installs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT    NOT NULL,
            ts           TEXT    NOT NULL,
            version      TEXT    NOT NULL,
            platform     TEXT    NOT NULL,        -- 'mac-arm' | 'mac-intel' | 'linux-deb' | 'linux-appimage' | 'windows-exe' | 'windows-msi'
            ip           TEXT,
            user_agent   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_desktop_installs_user
            ON desktop_installs(user_id, ts DESC);
        CREATE INDEX IF NOT EXISTS idx_desktop_installs_version
            ON desktop_installs(version, ts DESC);

        CREATE TABLE IF NOT EXISTS desktop_clients (
            user_id        TEXT    NOT NULL,
            install_id     TEXT    NOT NULL,
            first_seen_ts  TEXT    NOT NULL,
            last_seen_ts   TEXT    NOT NULL,
            version        TEXT    NOT NULL,
            platform       TEXT    NOT NULL,      -- 'darwin-arm64' | 'darwin-x86_64' | 'linux-x86_64' | 'win32-x86_64' …
            ip             TEXT,
            user_agent     TEXT,
            PRIMARY KEY (user_id, install_id)
        );
        CREATE INDEX IF NOT EXISTS idx_desktop_clients_last_seen
            ON desktop_clients(last_seen_ts DESC);

        -- Latest-version pointer. One row, ``key='current'`` is the
        -- canonical row the Download page reads. We use a key/value
        -- shape so future pointers (``beta``, ``rolling``) slot in
        -- without an ALTER TABLE.
        CREATE TABLE IF NOT EXISTS desktop_release_channels (
            channel        TEXT PRIMARY KEY,
            version        TEXT NOT NULL,
            published_at   TEXT NOT NULL,
            release_notes  TEXT,
            min_supported  TEXT                   -- semver below which we hard-pin "please update"
        );
        """
    )
    return conn


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    """Lock-guarded connection. SQLite handles concurrency at the
    OS level via WAL, but we hold a per-process lock so concurrent
    upserts to ``desktop_clients`` from many heartbeats don't
    interleave the read/write cycle and overwrite each other's
    ``first_seen_ts`` value."""
    global _INITIALISED
    with _LOCK:
        conn = _connect()
        if not _INITIALISED:
            # Seed an initial release channel row only if missing —
            # never clobber an operator-set pointer. Reads the version
            # from the desktop crate's published env if available so
            # local-dev backends round-trip correctly without a manual
            # SQL update.
            seed_version = os.environ.get("DESKTOP_RELEASE_SEED_VERSION", "0.1.0").strip() or "0.1.0"
            conn.execute(
                """
                INSERT OR IGNORE INTO desktop_release_channels
                    (channel, version, published_at, release_notes, min_supported)
                VALUES ('current', ?, ?, NULL, NULL)
                """,
                (seed_version, _now_iso()),
            )
            _INITIALISED = True
        try:
            yield conn
        finally:
            conn.close()


def _truncate(value: Optional[str], length: int) -> Optional[str]:
    """Trim free-form strings before storing. We're storing
    user-agent + IP — neither needs to exceed 200 chars and a
    pathological value (e.g. 4 KB UA) shouldn't bloat the DB."""
    if value is None:
        return None
    if len(value) <= length:
        return value
    return value[:length]


# ─── public API ─────────────────────────────────────────────────────


def record_download(
    *,
    user_id: str,
    version: str,
    platform: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> int:
    """Record one download intent. Returns the new row id.

    ``platform`` matches the SPA-side enum (``mac-arm`` etc.) — we
    deliberately don't normalise it to the kernel-style platform
    string the heartbeat uses, because the two questions are
    different ("which artefact did the user click?" vs "which OS
    is the running install on?") and conflating them would lose
    info during the bilingual case (e.g. an Intel Mac that
    downloaded the arm DMG runs under Rosetta).
    """
    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO desktop_installs (user_id, ts, version, platform, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                _now_iso(),
                version,
                platform,
                _truncate(ip, 64),
                _truncate(user_agent, 200),
            ),
        )
        return int(cur.lastrowid or 0)


def record_heartbeat(
    *,
    user_id: str,
    install_id: str,
    version: str,
    platform: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict[str, Any]:
    """Upsert a desktop_clients row keyed on (user_id, install_id).

    Returns a dict with ``first_seen`` (bool — True when this was
    a new client we hadn't seen before) so the route handler can
    log "new install" events distinctly from heartbeat refreshes.

    We store the version separately from desktop_installs's record
    of "what they downloaded" because users can install once and
    then auto-update many times — the heartbeat row tracks
    *currently running* version and is the input to the "do they
    need to update?" decision.
    """
    now = _now_iso()
    with _db() as conn:
        # Look up first to know if this is the first sighting. The
        # alternative — relying on UPSERT's "first_seen_ts old vs
        # excluded.first_seen_ts" — is harder to read and fails to
        # surface "new client just appeared" cleanly to the caller.
        existing = conn.execute(
            """
            SELECT first_seen_ts FROM desktop_clients
            WHERE user_id = ? AND install_id = ?
            """,
            (user_id, install_id),
        ).fetchone()
        first_seen = existing is None
        first_seen_ts = existing["first_seen_ts"] if existing else now

        conn.execute(
            """
            INSERT INTO desktop_clients
                (user_id, install_id, first_seen_ts, last_seen_ts, version, platform, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, install_id) DO UPDATE SET
                last_seen_ts = excluded.last_seen_ts,
                version      = excluded.version,
                platform     = excluded.platform,
                ip           = excluded.ip,
                user_agent   = excluded.user_agent
            """,
            (
                user_id,
                install_id,
                first_seen_ts,
                now,
                version,
                platform,
                _truncate(ip, 64),
                _truncate(user_agent, 200),
            ),
        )
    return {"first_seen": first_seen}


def list_clients(user_id: str) -> list[dict[str, Any]]:
    """Return every client this user has ever phoned home from,
    most-recently-active first. Powers the (planned) "Devices" UI
    on the web account page.
    """
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT install_id, first_seen_ts, last_seen_ts, version, platform, ip, user_agent
            FROM desktop_clients
            WHERE user_id = ?
            ORDER BY last_seen_ts DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_downloads(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Recent download events for a single user. Caps at ``limit``
    rows because a user who's been clicking the button for months
    doesn't need an unbounded list — the most-recent ones are the
    only useful signal for "did the click actually arrive?"
    """
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id, ts, version, platform, ip, user_agent
            FROM desktop_installs
            WHERE user_id = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (user_id, max(1, min(500, int(limit)))),
        ).fetchall()
    return [dict(r) for r in rows]


def get_release_channel(channel: str = "current") -> Optional[dict[str, Any]]:
    """Read the canonical pointer for a channel. ``current`` is the
    only channel populated today; ``beta`` / ``rolling`` reserve
    the shape for future use without a schema change.
    """
    with _db() as conn:
        row = conn.execute(
            """
            SELECT channel, version, published_at, release_notes, min_supported
            FROM desktop_release_channels
            WHERE channel = ?
            """,
            (channel,),
        ).fetchone()
    return dict(row) if row else None


def set_release_channel(
    *,
    version: str,
    channel: str = "current",
    release_notes: Optional[str] = None,
    min_supported: Optional[str] = None,
) -> None:
    """Bump the pointer for a channel. Called by the release script
    after a new bundle has been signed + uploaded; ``min_supported``
    is optional and only set when we explicitly want to force older
    installs to upgrade (e.g. a security fix that breaks a wire
    protocol).
    """
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO desktop_release_channels
                (channel, version, published_at, release_notes, min_supported)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(channel) DO UPDATE SET
                version       = excluded.version,
                published_at  = excluded.published_at,
                release_notes = excluded.release_notes,
                min_supported = excluded.min_supported
            """,
            (channel, version, _now_iso(), release_notes, min_supported),
        )


def db_path() -> Path:
    """Test hook — lets the test suite point at an isolated DB and
    inspect it without re-implementing the path resolution."""
    return _DB_PATH
