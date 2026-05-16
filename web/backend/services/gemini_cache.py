"""
Vertex Gemini explicit-context caching for the search_docs corpus.

Why explicit caching when implicit already works?
-------------------------------------------------
Vertex's *implicit* prefix cache is free but unpredictable: even a tiny
prefix drift (a fresh ``cwd`` interpolation, a random whitespace tweak)
busts the hit. *Explicit* caching gives us a hard guarantee of cache hit
every call (75 % off input rate, not "best-effort"), a tiny call body
(~5 KB query instead of 1-2 MB corpus inline), and easy ops levers
(``PI_TYPST_DISABLE_EXPLICIT_CACHE=1`` falls back to the implicit-cache
codepath instantly).

Cache lifecycle (DB-backed, 2026-05-16 rewrite #2)
--------------------------------------------------
The May 2026 rewrite #1 fixed the prewarm-leak ($1k/day → $8/day) but
left the registry as an in-process dict that desynced across workers.
Two parallel cold-miss workers could each create their own resource
because Vertex's ``cachedContents.list`` endpoint is eventually
consistent. This rewrite #2 moves the registry into SQLite
(``services/gemini_cache_db.py``) so all workers share a single source
of truth, and adds an active sweeper that evicts idle caches:

  1. **DB is the source of truth.** ``get_or_refresh`` first reads
     ``gemini_caches`` (PK = package). On a hit it bumps
     ``last_used_at`` and returns the cache name. No Vertex API call.
  2. **Per-package locks** still guard the create path so concurrent
     misses for the same package converge on one Vertex create. The
     locks are in-process; the DB row is the cross-process barrier.
  3. **Adopt-then-create** still works: on a miss we list Vertex
     once for an existing matching ``displayName`` and adopt it,
     writing the row to the DB. Any duplicates get queued for
     deletion (legacy-leak self-heal).
  4. **Idle eviction.** A background sweeper task scans the DB for
     rows with ``last_used_at < now - IDLE_TTL`` (default 1 h) and
     issues Vertex DELETEs for each. The Vertex resource and the DB
     row both go away. Storage stops being billed within 10 min of
     a cache going unused.
  5. **Boot reconcile.** On the first sweep cycle after boot the
     sweeper additionally lists Vertex's actual caches with our
     ``displayName`` pattern and deletes any that aren't in the DB
     (orphans from before the DB existed, or a crash that left a
     resource un-tracked).

Failure modes
-------------
* Vertex create returns 4xx (corpus below the minimum-cache-size
  threshold the platform enforces): we log, skip caching that
  package, and the calling code falls back to the inline-corpus
  request path. Search still works, just at the implicit-cache rate.
* Network hiccup mid-create: the failure is recorded in ``_neg_cache``
  for ``_NEG_CACHE_TTL_S`` so we don't hammer Vertex on every
  subsequent call.
* Process restart: the in-process locks are gone but the DB row
  persists. The next call hits the DB, returns the same cache_name,
  and traffic continues uninterrupted. Zero-cost recovery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

from services import gemini_cache_db as cache_db

logger = logging.getLogger(__name__)


# ── Tunables (env-overridable for ops without redeploying) ───────────
def _ttl_seconds() -> int:
    """Cache TTL in seconds. Default = 1 h.

    Storage on Gemini 3 Flash is ~$4.50 / M-token-hour. The corpus is
    ~265 k tokens × 7 packages = 1.85 M tokens; pinned 24 h that's
    ~$200/day even with zero queries. Pinned 1 h it's ~$8/day, which
    is the floor we want.

    The sweeper independently enforces an *idle* TTL (default 1 h)
    by deleting caches that haven't been touched in that window.
    The Vertex-side TTL is the upper bound; the sweeper is the
    lower bound. They roughly coincide today but they're separate
    knobs so an operator can tighten one without touching the other.
    """
    raw = (os.environ.get("PI_TYPST_CACHE_TTL_S") or "").strip()
    if raw and raw.isdigit():
        return max(600, int(raw))
    return 3_600


# How early before expiry we kick off a proactive refresh. 5 minutes:
# the create call usually finishes in 5-30 s, so we'll start a fresh
# cache well before the live one expires and callers never see a miss.
REFRESH_GRACE_S = 300

# How long any one cache-create call has to complete. Generous because
# Vertex sometimes takes 30+ s to finalize a write for big payloads.
_CREATE_TIMEOUT_S = 120.0
_DELETE_TIMEOUT_S = 30.0
_LIST_TIMEOUT_S = 15.0

# Per-package asyncio.Lock so a miss for `cetz` doesn't serialise
# concurrent queries for `typst`. Keyed by package name. These are
# in-process — the DB row is the cross-process barrier.
_pkg_locks: dict[str, asyncio.Lock] = {}
_pkg_locks_guard = asyncio.Lock()

# Negative cache: when create permanently fails for a package (e.g.
# its corpus is below Vertex's minimum-cache-size threshold) we sit
# out for ``_NEG_CACHE_TTL_S`` before trying again. In-process is
# fine here: the worst case is N workers each hammer Vertex once,
# get the same 4xx, and back off independently — no cost spike.
_NEG_CACHE_TTL_S = 3_600
_neg_cache: dict[str, float] = {}  # package -> monotonic time when we'll retry


# ── Public API ───────────────────────────────────────────────────────
def is_disabled() -> bool:
    """Operator kill-switch. When ``PI_TYPST_DISABLE_EXPLICIT_CACHE`` is
    set to a truthy value, every entry-point in this module short-circuits
    to "no cache available" and the calling route falls back to the
    inline-corpus codepath (and the implicit-cache discount).
    """
    raw = (os.environ.get("PI_TYPST_DISABLE_EXPLICIT_CACHE") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


async def get_or_refresh(
    *,
    package: str,
    corpus: dict[str, str],
    persona_for: Callable[[str], str],
    rules: str,
    model_id: str,
    project: str,
    location: str,
    host: str,
    token_provider: Callable[[], Optional[str]],
) -> Optional[str]:
    """Return the live ``cachedContents`` resource name for ``package``.

    DB-backed lookup order:

      1. Fast path: read the ``gemini_caches`` row for ``package``.
         If fresh (model matches, ``expires_at - REFRESH_GRACE > now``)
         bump ``last_used_at`` and return.
      2. Slow path (per-package lock): re-check the row, then list
         Vertex for an adoptable cache. Write to DB and return on adopt.
      3. Cold path: create a new Vertex cache, write the row, return.

    Returns ``None`` when:

      * the kill-switch is set, or
      * the model is not Gemini, or
      * the package has no corpus, or
      * the package is in the negative-cache window (recent create
        failed permanently), or
      * ADC token fetch returned None, or
      * the create / adopt path crashed.

    The caller is expected to fall back to the inline-corpus request
    path when ``None`` comes back — search_docs must remain functional
    even when caching is unavailable.
    """
    if is_disabled():
        return None

    # Anthropic / non-Gemini models use a different cache mechanism
    # (cache_control: ephemeral on each block). Don't even try here.
    if not _is_gemini(model_id):
        return None

    pkg_text = corpus.get(package)
    if not pkg_text or not pkg_text.strip():
        return None

    # ── Fast path: DB lookup ────────────────────────────────────────
    row = cache_db.lookup(package)
    if row is not None and _row_is_usable(row, model_id):
        cache_db.touch(package)
        return str(row["cache_name"])

    # Slow path — take the per-package lock so concurrent callers for
    # this package converge on a single create / adopt. Other packages
    # are unaffected.
    lock = await _pkg_lock(package)
    async with lock:
        # Re-check inside the lock — another coroutine in this worker
        # may have created the row while we waited.
        row = cache_db.lookup(package)
        if row is not None and _row_is_usable(row, model_id):
            cache_db.touch(package)
            return str(row["cache_name"])

        # Negative-cache check: skip if a recent create permanently
        # failed and the back-off window hasn't expired.
        now_mono = time.monotonic()
        deadline = _neg_cache.get(package)
        if deadline is not None and now_mono < deadline:
            logger.debug(
                "[gemini-cache] %s in negative-cache window (%.0fs left); skipping",
                package, deadline - now_mono,
            )
            return None

        token = token_provider()
        if not token:
            logger.warning("[gemini-cache] no ADC token; skipping %s", package)
            return None

        adopted = await _adopt_existing(
            package=package,
            model_id=model_id,
            project=project,
            location=location,
            host=host,
            token=token,
        )
        if adopted is not None:
            cache_db.record_created(
                package=package,
                cache_name=adopted.name,
                display_name=_display_name(package),
                model_id=model_id,
                expires_at_iso=adopted.expires_at_iso,
                expires_at_epoch=adopted.expires_at_epoch,
            )
            _neg_cache.pop(package, None)
            logger.info(
                "[gemini-cache] adopted existing cache %s for %s "
                "(expires in %ds)",
                adopted.name.split("/")[-1], package,
                int(adopted.expires_at_epoch - time.time())
                if adopted.expires_at_epoch else -1,
            )
            return adopted.name

        # Nothing reusable on Vertex — create exactly one.
        try:
            created = await _create_cache(
                package=package,
                corpus_text=pkg_text,
                persona=persona_for(package),
                rules=rules,
                model_id=model_id,
                project=project,
                location=location,
                host=host,
                token=token,
            )
        except Exception as exc:  # noqa: BLE001
            _neg_cache[package] = time.monotonic() + _NEG_CACHE_TTL_S
            logger.warning("[gemini-cache] %s create FAILED: %s", package, exc)
            return None

        cache_db.record_created(
            package=package,
            cache_name=created.name,
            display_name=_display_name(package),
            model_id=model_id,
            expires_at_iso=created.expires_at_iso,
            expires_at_epoch=created.expires_at_epoch,
        )
        _neg_cache.pop(package, None)
        logger.info(
            "[gemini-cache] created %s for %s (expires in %ds)",
            created.name.split("/")[-1], package,
            int(created.expires_at_epoch - time.time())
            if created.expires_at_epoch else -1,
        )
        return created.name


async def prewarm_caches(
    *,
    corpus: dict[str, str],
    persona_for: Callable[[str], str],
    rules: str,
    model_id: str,
    project: str,
    location: str,
    host: str,
    token_provider: Callable[[], Optional[str]],
) -> None:
    """Deprecated — kept as a no-op for callers in app.py's startup hook.

    The pre-2026-05 design eagerly created all 7 caches at boot. That
    multiplied storage cost by N redeploys/day because each restart
    leaked the previous boot's caches. Lazy creation in
    :func:`get_or_refresh` does the same job idempotently — and only
    pays the storage bill for packages someone actually queried. The
    DB-backed registry plus the idle sweeper now handle the cleanup
    half of the equation.
    """
    _ = (corpus, persona_for, rules, model_id, project, location, host, token_provider)
    if is_disabled():
        logger.info("[gemini-cache] explicit cache disabled; prewarm noop")
    else:
        logger.info(
            "[gemini-cache] prewarm is now a no-op — caches are created lazily "
            "on first search_docs call per package, tracked in SQLite, and "
            "evicted by the idle sweeper after %ds",
            cache_db._idle_ttl_s(),
        )


def snapshot() -> dict[str, dict[str, object]]:
    """Read-only inspection helper for the /v1/typst/_health endpoint.

    Returns one dict per known cache so operators can see TTL state at
    a glance without sniffing internals. Reads from the DB so all
    workers see the same view.
    """
    now_epoch = time.time()
    out: dict[str, dict[str, object]] = {}
    for row in cache_db.list_all():
        last_used_epoch = float(row.get("last_used_epoch") or 0.0)
        expires_epoch = row.get("expires_epoch")
        out[row["package"]] = {
            "name": (row.get("cache_name") or "").split("/")[-1] or None,
            "model": row.get("model_id"),
            "ageSeconds": int(now_epoch - last_used_epoch),
            "expiresInSeconds": (
                max(0, int(float(expires_epoch) - now_epoch))
                if expires_epoch is not None else None
            ),
            "fresh": (
                expires_epoch is not None
                and (float(expires_epoch) - now_epoch) > REFRESH_GRACE_S
            ),
        }
    return out


# ── Sweeper integration ──────────────────────────────────────────────


async def _sweeper_delete(cache_name: str) -> tuple[bool, Optional[str]]:
    """Bridge the sweeper's typed delete callback to our token-bearing
    HTTP call. Pulls the latest token + project at call time so a
    long-running sweeper doesn't pin a stale set of credentials.
    """
    project, location, host, token = _sweeper_creds()
    if not token:
        return False, "no ADC token available"
    try:
        async with httpx.AsyncClient(timeout=_DELETE_TIMEOUT_S) as client:
            resp = await client.delete(
                f"https://{host}/v1/{cache_name}",
                headers=_request_headers(token=token, project=project),
            )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if resp.status_code in (200, 204, 404):
        return True, None
    return False, f"HTTP {resp.status_code}: {resp.text[:200]}"


async def _sweeper_reconcile() -> list[dict[str, Any]]:
    """List Vertex's actual caches matching our displayName pattern.

    The sweeper compares this against the DB and deletes any caches
    we don't know about. We only return entries whose displayName
    starts with ``typst-docs-`` so we never touch caches some other
    workload on the same project happens to own.
    """
    project, location, host, token = _sweeper_creds()
    if not token:
        return []
    try:
        items = await _list_cached_contents(
            project=project, location=location, host=host, token=token,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini-cache] reconcile list failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        dn = raw.get("displayName")
        if isinstance(dn, str) and dn.startswith("typst-docs-"):
            out.append(raw)
    return out


# Module-level credential snapshot for the sweeper. Populated by
# ``configure_sweeper`` on app startup; reading this at module import
# time would pin to .env values that may be missing during tests.
_SWEEPER_CREDS: dict[str, Any] = {
    "project": None, "location": None, "host": None, "token_provider": None,
}


def _sweeper_creds() -> tuple[str, str, str, Optional[str]]:
    creds = _SWEEPER_CREDS
    project = creds.get("project") or ""
    location = creds.get("location") or ""
    host = creds.get("host") or ""
    tp = creds.get("token_provider")
    token = tp() if callable(tp) else None
    return project, location, host, token


def configure_sweeper(
    *,
    project: str,
    location: str,
    host: str,
    token_provider: Callable[[], Optional[str]],
) -> None:
    """Snapshot the Vertex creds the sweeper needs to issue DELETEs.

    Called once at app startup (from app.py's lifespan) before
    ``cache_db.start_sweeper`` is invoked. Decoupling the sweeper
    config from the get_or_refresh call site keeps the sweeper
    independent of any specific request — it owns its own auth.
    """
    _SWEEPER_CREDS["project"] = project
    _SWEEPER_CREDS["location"] = location
    _SWEEPER_CREDS["host"] = host
    _SWEEPER_CREDS["token_provider"] = token_provider


def start_sweeper() -> None:
    """Start the DB sweeper using this module's delete + reconcile
    callbacks. No-op if ``configure_sweeper`` hasn't been called.
    """
    if not _SWEEPER_CREDS.get("token_provider"):
        logger.warning(
            "[gemini-cache] sweeper not started: configure_sweeper "
            "wasn't called with a token_provider"
        )
        return
    cache_db.start_sweeper(
        delete=_sweeper_delete, reconcile=_sweeper_reconcile,
    )


async def stop_sweeper() -> None:
    """Cancel the running sweeper task (lifespan shutdown)."""
    await cache_db.stop_sweeper()


async def run_sweep_now() -> dict[str, int]:
    """Force one sweep cycle synchronously. Used by the admin
    endpoint to give operators a "kill all idle now" button without
    waiting for the next interval.
    """
    if not _SWEEPER_CREDS.get("token_provider"):
        return {"swept": 0, "deleted": 0, "errors": 0, "orphans": 0,
                "skipped_lease": 0, "error": "sweeper not configured"}
    return await cache_db.run_sweep_now(
        delete=_sweeper_delete, reconcile=_sweeper_reconcile,
    )


# ── Internals ────────────────────────────────────────────────────────


@dataclass
class _AdoptedCache:
    """Lightweight transit type between adopt/create and the DB."""

    name: str
    expires_at_iso: Optional[str]
    expires_at_epoch: Optional[float]


def _is_gemini(model_id: str) -> bool:
    return model_id.lower().startswith("gemini-")


def _display_name(package: str) -> str:
    """Stable, deterministic displayName so cross-process adoption works.

    The trailing ``-v1`` is a schema-version marker — bump it if the
    cached payload shape changes (persona/rules format change, corpus
    chunking change) so old caches with the previous shape are not
    accidentally adopted.
    """
    return f"typst-docs-{package}-v1"


def _vertex_model_resource(model_id: str, project: str, location: str) -> str:
    """Full Vertex publisher-model path used by cachedContents."""
    return (
        f"projects/{project}/locations/{location}/"
        f"publishers/google/models/{model_id}"
    )


def _request_headers(*, token: str, project: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project,
    }


async def _pkg_lock(package: str) -> asyncio.Lock:
    """Get-or-create the per-package asyncio.Lock under a tiny global
    guard. Packages don't churn at runtime so the dict stays small."""
    async with _pkg_locks_guard:
        lock = _pkg_locks.get(package)
        if lock is None:
            lock = asyncio.Lock()
            _pkg_locks[package] = lock
        return lock


def _row_is_usable(row: dict[str, Any], model_id: str) -> bool:
    """A DB row is usable if the model matches AND the Vertex-side
    expiry is past the refresh grace. We don't enforce idleness here
    — that's the sweeper's job. As long as the cache hasn't been
    swept, a stale-by-idleness row is still a hit.
    """
    if row.get("model_id") != model_id:
        return False
    expires_epoch = row.get("expires_epoch")
    if expires_epoch is None:
        return False
    return (float(expires_epoch) - time.time()) > REFRESH_GRACE_S


async def _list_cached_contents(
    *,
    project: str,
    location: str,
    host: str,
    token: str,
) -> list[dict]:
    """One-shot list call. Used only on cold-miss adopt paths and by
    the sweeper's reconcile pass — never on the request hot path
    (which goes through the DB instead).
    """
    url = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/cachedContents?pageSize=200"
    )
    try:
        async with httpx.AsyncClient(timeout=_LIST_TIMEOUT_S) as client:
            resp = await client.get(
                url,
                headers=_request_headers(token=token, project=project),
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("[gemini-cache] list cachedContents network error: %s", exc)
        return []
    if resp.status_code != 200:
        logger.debug(
            "[gemini-cache] list cachedContents HTTP %d: %s",
            resp.status_code, resp.text[:200],
        )
        return []
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.debug("[gemini-cache] list cachedContents non-JSON: %s", exc)
        return []
    fresh = data.get("cachedContents") or []
    if not isinstance(fresh, list):
        return []
    return list(fresh)


def _parse_iso_to_epoch(raw: Optional[str]) -> Optional[float]:
    """Translate Vertex's RFC-3339 timestamp to a wall-clock epoch.

    Returns ``None`` if the field is missing or malformed.
    """
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    return dt.timestamp()


async def _adopt_existing(
    *,
    package: str,
    model_id: str,
    project: str,
    location: str,
    host: str,
    token: str,
) -> Optional[_AdoptedCache]:
    """Find a still-fresh cache on Vertex with our displayName and
    return it. Side effect: any *extra* alive caches with the same
    displayName (the legacy-leak signature) are queued for background
    deletion so the project self-heals.
    """
    items = await _list_cached_contents(
        project=project, location=location, host=host, token=token,
    )
    if not items:
        return None

    target = _display_name(package)
    candidates: list[_AdoptedCache] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        if raw.get("displayName") != target:
            continue
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            continue
        expires_iso = raw.get("expireTime") if isinstance(raw.get("expireTime"), str) else None
        expires_epoch = _parse_iso_to_epoch(expires_iso)
        if expires_epoch is None:
            continue
        candidates.append(_AdoptedCache(
            name=name, expires_at_iso=expires_iso, expires_at_epoch=expires_epoch,
        ))

    if not candidates:
        return None

    # Prefer the one that expires LAST (most recently created).
    candidates.sort(key=lambda c: c.expires_at_epoch or 0.0, reverse=True)
    best = candidates[0]

    # Even the freshest is past the refresh grace?  Skip — the caller
    # creates a brand-new one. The stale resource is left for the
    # sweeper's reconcile pass to clean up.
    if best.expires_at_epoch is None:
        return None
    if (best.expires_at_epoch - time.time()) <= REFRESH_GRACE_S:
        return None

    # Schedule deletion of the runners-up so we stop paying storage
    # for the orphaned duplicates from the leaky era.
    for stale in candidates[1:]:
        asyncio.create_task(
            _delete_cache_quietly(
                name=stale.name, project=project, host=host, token=token,
                reason="duplicate",
            )
        )

    return best


async def _create_cache(
    *,
    package: str,
    corpus_text: str,
    persona: str,
    rules: str,
    model_id: str,
    project: str,
    location: str,
    host: str,
    token: str,
) -> _AdoptedCache:
    """POST /v1/projects/{p}/locations/{l}/cachedContents.

    The cached body contains everything that's invariant per call —
    persona + rules + the package's corpus block. The actual user
    query is sent fresh on each :generateContent call alongside the
    ``cachedContent`` reference, so context drift is impossible.
    """
    url = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/cachedContents"
    )
    cached_text = (
        f"{persona}\n\n{rules}\n\n"
        f"The full {package} corpus follows. Read what you need, ignore the rest.\n\n"
        f"{corpus_text}"
    )
    body = {
        "model": _vertex_model_resource(model_id, project, location),
        "contents": [
            {"role": "user", "parts": [{"text": cached_text}]},
        ],
        "ttl": f"{_ttl_seconds()}s",
        "displayName": _display_name(package),
    }
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=_CREATE_TIMEOUT_S) as client:
        resp = await client.post(
            url,
            headers=_request_headers(token=token, project=project),
            content=json.dumps(body),
        )
    elapsed = time.monotonic() - started

    if resp.status_code != 200:
        raise RuntimeError(
            f"Vertex cachedContents create returned {resp.status_code}: "
            f"{resp.text[:300]}"
        )

    data = resp.json()
    name = data.get("name")
    if not isinstance(name, str) or not name:
        raise RuntimeError(
            f"Vertex cachedContents response missing 'name': {data}"
        )

    expires_iso = data.get("expireTime") if isinstance(data.get("expireTime"), str) else None
    expires_epoch = _parse_iso_to_epoch(expires_iso)
    if expires_epoch is None:
        # Vertex didn't echo the TTL? Approximate from the request value
        # so the DB row still has a reasonable expiry.
        expires_epoch = time.time() + _ttl_seconds()
        # Fabricate an ISO string for symmetry; this is informational only.
        expires_iso = (
            datetime.fromtimestamp(expires_epoch, tz=timezone.utc)
            .isoformat(timespec="seconds")
        )

    logger.debug(
        "[gemini-cache] created %s in %.2fs (cached %d chars)",
        name.split("/")[-1], elapsed, len(cached_text),
    )
    return _AdoptedCache(
        name=name, expires_at_iso=expires_iso, expires_at_epoch=expires_epoch,
    )


async def _delete_cache_quietly(
    *,
    name: str,
    project: str,
    host: str,
    token: str,
    reason: str = "manual",
) -> None:
    """Best-effort cleanup. Errors are swallowed because Vertex-side
    cleanup is just a cost optimisation, never a correctness issue.
    Records the attempt in the eviction audit log either way."""
    ok = False
    err: Optional[str] = None
    try:
        async with httpx.AsyncClient(timeout=_DELETE_TIMEOUT_S) as client:
            resp = await client.delete(
                f"https://{host}/v1/{name}",
                headers=_request_headers(token=token, project=project),
            )
        if resp.status_code in (200, 204, 404):
            ok = True
        else:
            err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            logger.debug(
                "[gemini-cache] delete %s returned %d: %s",
                name.split("/")[-1], resp.status_code, resp.text[:200],
            )
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        logger.debug("[gemini-cache] delete %s failed: %s", name, exc)

    cache_db.record_eviction(
        package=None, cache_name=name, reason=reason, ok=ok, error=err,
    )


# ── Stale-cache recovery ─────────────────────────────────────────────
#
# Vertex's ``cachedContents`` resources can disappear out from under us
# even when our DB swears they're still alive:
#
#   * The resource hit its server-side TTL and Vertex GC'd it before
#     our sweeper got there (eventual-consistency clock skew).
#   * Another tenant on the same project ran a manual purge.
#   * The cache was created in a different region than the
#     ``:generateContent`` call we're about to make (region drift after
#     a model-routing change).
#   * A previous backend instance crashed mid-create and the resource
#     ended up in a zombie state Vertex returns 400 for.
#
# In every case the symptom is a non-2xx from ``:generateContent``
# whose body mentions ``cachedContent`` plus a "missing / expired /
# not_found" word. The fix is the same: invalidate our DB row, delete
# the Vertex resource (best-effort), force-recreate, retry the original
# call exactly once. We DON'T retry more than once — if the second
# attempt also says "cached content not found" something else is wrong
# (auth, region, quota) and the calling route should surface the
# upstream error rather than loop on it.


# Substrings that, in combination, identify a stale-cache 4xx response.
# We require BOTH a "cache" word AND a "missing/expired" word so a
# generic "not found" 404 (e.g. wrong project, model name typo) doesn't
# trigger a recreate loop. Substrings are case-insensitive — Vertex
# sometimes capitalizes the gRPC code name.
_CACHE_TOKENS = ("cachedcontent", "cached content")
_STALE_TOKENS = (
    "not found", "not_found",
    "does not exist", "doesn't exist",
    "expired",
    "failed_precondition",
    "invalidated",
    "no longer exists",
    "is not available",
)


def is_stale_cache_error(*, status: int, body: str) -> bool:
    """Return True iff a non-2xx ``:generateContent`` response looks
    like Vertex saying our ``cachedContent`` reference is invalid.

    Why detect via response body instead of relying on a stable error
    code: Vertex's REST surface returns the gRPC status name in the
    JSON ``error.status`` field (``NOT_FOUND``, ``FAILED_PRECONDITION``)
    but the http status itself can be 400 OR 404 OR 500 depending on
    the failure mode. The body text is the thing that's stable across
    those.

    We deliberately scope this to 400 / 404. Anything else (401/403
    auth, 429 quota, 5xx upstream) is NOT a stale-cache failure even
    if the body happens to mention the word "cache" — we don't want
    to thrash the registry on a 429 retry storm.
    """
    if status not in (400, 404):
        return False
    b = (body or "").lower()
    if not any(tok in b for tok in _CACHE_TOKENS):
        return False
    return any(tok in b for tok in _STALE_TOKENS)


async def invalidate(
    *,
    package: str,
    project: str,
    host: str,
    token_provider: Callable[[], Optional[str]],
) -> None:
    """Drop the DB row for ``package`` and best-effort delete the
    Vertex resource. After this call returns, the next
    ``get_or_refresh(package=...)`` is guaranteed to take the create
    path (or adopt path, if some other worker raced ahead).

    This function is the "the cache is bad, kill it" half of the
    stale-cache recovery flow. The "make a fresh one" half is just
    calling ``get_or_refresh`` again after this returns.
    """
    row = cache_db.remove(package)
    if row is None:
        # Already gone — nothing to do server-side either, since
        # by definition we wouldn't have a name to call DELETE with.
        logger.info(
            "[gemini-cache] invalidate(%s): row already absent", package,
        )
        return
    cache_name = row.get("cache_name")
    if not isinstance(cache_name, str) or not cache_name:
        return
    token = token_provider()
    if not token:
        # Without a token we can't talk to Vertex. The DB row is
        # already gone so the next call will create afresh; the
        # orphaned Vertex resource will be picked up by the sweeper's
        # reconcile pass.
        cache_db.record_eviction(
            package=package, cache_name=cache_name,
            reason="invalidate-no-token", ok=False,
            error="no ADC token at invalidate time",
        )
        return
    await _delete_cache_quietly(
        name=cache_name, project=project, host=host, token=token,
        reason="stale-on-use",
    )


# Test hook — let unit tests reset state between cases without
# touching private globals.
def _reset_for_tests() -> None:
    _neg_cache.clear()
    _pkg_locks.clear()
    cache_db._reset_for_tests()
