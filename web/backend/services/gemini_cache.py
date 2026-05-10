"""
Vertex Gemini explicit-context caching for the search_docs corpus.

Why explicit caching when implicit already works?
-------------------------------------------------
Vertex's *implicit* prefix cache is free but unpredictable: even a tiny
prefix drift (a fresh ``cwd`` interpolation, a random whitespace tweak)
busts the hit. We've been getting ~90 % off after warm-up — but the
"warm-up" caveat means the first user every backend boot pays full
price (~30 s wall-time on the cold call), and ops cannot quote a
ceiling cost to the business.

*Explicit* caching costs more in the steady state (~$190/mo storage
for the 265 k-token corpus pinned 24 h × 30 d) but gives us:

  * a hard guarantee of cache hit every call (75 % off input rate,
    not "best-effort"),
  * predictable monthly cost — one variable: TTL × token count,
  * tiny call body (~5 KB query instead of 1-2 MB corpus inline) →
    lower wire-time per request,
  * easy ops levers: ``PI_TYPST_DISABLE_EXPLICIT_CACHE=1`` falls back
    to the implicit-cache codepath instantly.

Refresh policy (per product directive):
---------------------------------------
**One package's cache going stale forces a refresh of ALL seven.** No
state where typst is cached but cetz isn't. The lockstep simplifies
ops mental-modelling ("either the search_docs cache layer is warm or
it isn't") and avoids a class of bugs where a half-warmed cache
silently turns one query expensive.

The TTL is 24 h (Vertex's max for the standard tier). We start a
proactive refresh ``REFRESH_GRACE_S`` before expiry so a slow refresh
never causes a brief miss-window during a cycle change.

Cache lifecycle
---------------
On startup we know nothing about Vertex-side caches. The FastAPI
startup hook in ``app.py`` schedules :func:`prewarm_caches` as a
background task — it loads the corpus, creates all 7 caches in
parallel, and stores their resource names in the in-process map.

On every search_docs call, :func:`get_or_refresh` checks the local
map. If everything is fresh, it returns the resource name. If
*anything* is missing or in the grace window, the entire layer is
re-created in lockstep (under a single asyncio lock so concurrent
callers wait on one refresh, not N parallel refreshes).

Failure modes
-------------
* Vertex create returns 4xx (e.g. corpus below the minimum-cache-size
  threshold the platform enforces): we log, skip caching that
  package, and the calling code falls back to the inline-corpus
  request path. Search still works, just at the implicit-cache rate.
* Network hiccup mid-refresh: the half-failed refresh leaves the
  map in a consistent state (we only commit successes), so the next
  call retries the failed packages.
* Process restart: in-memory map is empty; the next call (or
  startup prewarm) re-creates everything. Vertex-side leftover caches
  from the previous process expire on their own 24h TTL; we do NOT
  try to discover and reuse them — too cheap to bother.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import httpx

logger = logging.getLogger(__name__)


# ── Tunables (env-overridable for ops without redeploying) ───────────
def _ttl_seconds() -> int:
    """Cache TTL in seconds. Default = 24 h (Vertex standard-tier max).

    Operators can shorten this for cost-sensitive deploys via
    ``PI_TYPST_CACHE_TTL_S``. Note that going below ~3 h erases most
    of the cost advantage over implicit caching for low-volume usage.
    """
    raw = (os.environ.get("PI_TYPST_CACHE_TTL_S") or "").strip()
    if raw and raw.isdigit():
        return max(60, int(raw))
    return 86_400


# How early before expiry we kick off a proactive refresh. 10 minutes
# is comfortable: even a slow Vertex create (~30 s) finishes well before
# the existing cache actually expires, so callers never see a miss.
REFRESH_GRACE_S = 600

# How long any one cache-create call has to complete. Generous because
# Vertex sometimes takes 30+ s to finalize a write for big payloads.
_CREATE_TIMEOUT_S = 120.0
_DELETE_TIMEOUT_S = 30.0


# ── State ────────────────────────────────────────────────────────────
@dataclass
class _CacheEntry:
    """One package's live Vertex cachedContents resource."""

    name: str            # full resource: projects/.../cachedContents/{id}
    package: str
    model_id: str
    created_at: float    # monotonic
    expires_at: float    # monotonic; we treat as stale ``REFRESH_GRACE_S`` early

    def is_fresh(self, now: float) -> bool:
        return now + REFRESH_GRACE_S < self.expires_at


# Per-package map; mutated only while ``_state_lock`` is held.
_caches: dict[str, _CacheEntry] = {}
_state_lock = asyncio.Lock()

# Per-package "last failure" so we don't hammer Vertex when the corpus
# is permanently below the minimum-cache-size threshold (some packages
# in our corpus are ~5-10 k tokens; Vertex's standard-tier minimum is
# 32 k tokens for Gemini Flash). Once a create has failed, we sit out
# for at least this many seconds before trying again.
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

    If anything is missing or about to expire, refresh ALL packages in
    lockstep before returning. Returns ``None`` when:

      * the kill-switch is set, or
      * the package's corpus is below the platform minimum (negative-
        cached so we don't hammer Vertex on every call), or
      * the Vertex API rejected the create.

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

    now = time.monotonic()
    entry = _caches.get(package)
    if (
        entry
        and entry.model_id == model_id
        and entry.is_fresh(now)
    ):
        return entry.name

    # Slow path — refresh under lock.
    async with _state_lock:
        # Re-check inside the lock; another waiter may have done it.
        now = time.monotonic()
        entry = _caches.get(package)
        if (
            entry
            and entry.model_id == model_id
            and entry.is_fresh(now)
        ):
            return entry.name

        await _refresh_all_locked(
            corpus=corpus,
            persona_for=persona_for,
            rules=rules,
            model_id=model_id,
            project=project,
            location=location,
            host=host,
            token_provider=token_provider,
        )

    return _caches.get(package).name if package in _caches else None  # type: ignore[union-attr]


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
    """Build all caches eagerly. Called from FastAPI's startup hook so
    the first real user request finds everything warm.

    Failures are logged, never raised — startup must never block on a
    transient Vertex hiccup.
    """
    if is_disabled():
        logger.info("[gemini-cache] explicit cache disabled; skipping prewarm")
        return
    if not _is_gemini(model_id):
        logger.info(
            "[gemini-cache] router model %s is not Gemini; skipping prewarm "
            "(Anthropic models use cache_control: ephemeral instead)",
            model_id,
        )
        return
    try:
        async with _state_lock:
            await _refresh_all_locked(
                corpus=corpus,
                persona_for=persona_for,
                rules=rules,
                model_id=model_id,
                project=project,
                location=location,
                host=host,
                token_provider=token_provider,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini-cache] prewarm failed: %s", exc)


def snapshot() -> dict[str, dict[str, object]]:
    """Read-only inspection helper for the /v1/typst/_health endpoint.

    Returns one dict per known cache so operators can see TTL state at
    a glance without sniffing internals.
    """
    now = time.monotonic()
    out: dict[str, dict[str, object]] = {}
    for pkg, ent in _caches.items():
        out[pkg] = {
            "name": ent.name.split("/")[-1] if ent.name else None,
            "model": ent.model_id,
            "ageSeconds": int(now - ent.created_at),
            "expiresInSeconds": max(0, int(ent.expires_at - now)),
            "fresh": ent.is_fresh(now),
        }
    return out


# ── Internals ────────────────────────────────────────────────────────
def _is_gemini(model_id: str) -> bool:
    return model_id.lower().startswith("gemini-")


def _vertex_model_resource(model_id: str, project: str, location: str) -> str:
    """Full Vertex publisher-model path used by cachedContents.

    Vertex's cachedContents API rejects bare ``publishers/google/...``
    paths — it requires the full project-scoped resource name.
    """
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


async def _refresh_all_locked(
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
    """Refresh every package's cache in parallel. Caller holds ``_state_lock``.

    Old caches that we successfully replace are deleted in a
    fire-and-forget pass at the end (best-effort; a leaked Vertex-side
    cache costs a few cents until its TTL expires).
    """
    token = token_provider()
    if not token:
        logger.warning("[gemini-cache] no ADC token available; skipping refresh")
        return

    now = time.monotonic()
    old_entries = [
        ent for ent in _caches.values()
        if ent.model_id != model_id or not ent.is_fresh(now)
    ]

    # Pick the packages that genuinely need a (re-)create:
    #   * skip those whose last create failed inside the negative-cache
    #     window (likely a permanent below-minimum-size error),
    #   * skip those already fresh in the in-memory map (the caller
    #     hit the slow path for SOME package, but its siblings might
    #     still be warm — no point re-billing storage on those).
    eligible: list[str] = []
    for pkg, text in corpus.items():
        if not text.strip():
            continue
        deadline = _neg_cache.get(pkg)
        if deadline is not None and now < deadline:
            logger.debug(
                "[gemini-cache] %s in negative-cache window (%.0fs left); skipping",
                pkg, deadline - now,
            )
            continue
        existing = _caches.get(pkg)
        if (
            existing is not None
            and existing.model_id == model_id
            and existing.is_fresh(now)
        ):
            logger.debug(
                "[gemini-cache] %s still fresh (expires in %.0fs); skipping",
                pkg, existing.expires_at - now,
            )
            continue
        eligible.append(pkg)

    if not eligible:
        logger.info("[gemini-cache] nothing eligible to refresh")
        return

    logger.info(
        "[gemini-cache] refreshing %d package(s) in lockstep: %s",
        len(eligible), ",".join(eligible),
    )

    tasks = [
        _create_cache(
            package=pkg,
            corpus_text=corpus[pkg],
            persona=persona_for(pkg),
            rules=rules,
            model_id=model_id,
            project=project,
            location=location,
            host=host,
            token=token,
        )
        for pkg in eligible
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for pkg, res in zip(eligible, results):
        if isinstance(res, _CacheEntry):
            _caches[pkg] = res
            _neg_cache.pop(pkg, None)
            logger.info(
                "[gemini-cache] %s cached as %s (expires in %ds)",
                pkg, res.name.split("/")[-1], int(res.expires_at - time.monotonic()),
            )
        else:
            _neg_cache[pkg] = time.monotonic() + _NEG_CACHE_TTL_S
            logger.warning("[gemini-cache] %s create FAILED: %s", pkg, res)

    # Fire-and-forget cleanup of the entries we just superseded. We
    # don't await — Vertex-side leftover caches expire on their own
    # 24 h TTL; deleting is just a politeness/cost optimisation.
    for old in old_entries:
        # If the new entry has the same name (unlikely but possible if
        # Vertex returned a deterministic ID), skip the delete.
        new = _caches.get(old.package)
        if new is not None and new.name == old.name:
            continue
        asyncio.create_task(
            _delete_cache_quietly(
                name=old.name, project=project, host=host, token=token,
            )
        )


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
) -> _CacheEntry:
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
        "displayName": f"typst-docs-{package}-v1",
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

    now = time.monotonic()
    logger.debug(
        "[gemini-cache] created %s in %.2fs (cached %d chars)",
        name.split("/")[-1], elapsed, len(cached_text),
    )
    return _CacheEntry(
        name=name,
        package=package,
        model_id=model_id,
        created_at=now,
        expires_at=now + _ttl_seconds(),
    )


async def _delete_cache_quietly(
    *, name: str, project: str, host: str, token: str,
) -> None:
    """Best-effort cleanup. Errors are swallowed because Vertex-side
    cleanup is just a cost optimisation, never a correctness issue."""
    try:
        async with httpx.AsyncClient(timeout=_DELETE_TIMEOUT_S) as client:
            resp = await client.delete(
                f"https://{host}/v1/{name}",
                headers=_request_headers(token=token, project=project),
            )
        if resp.status_code not in (200, 204, 404):
            logger.debug(
                "[gemini-cache] delete %s returned %d: %s",
                name.split("/")[-1], resp.status_code, resp.text[:200],
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("[gemini-cache] delete %s failed: %s", name, exc)


# Test hook — let unit tests reset state between cases without
# touching private globals.
def _reset_for_tests() -> None:
    _caches.clear()
    _neg_cache.clear()
