"""
Unit tests for ``services/gemini_cache``.

We never hit the real Vertex API — every test monkey-patches
``httpx.AsyncClient`` so we can drive the lifecycle (create, adopt,
parallel hits, kill-switch, partial failure) deterministically.

What this layer guarantees (rewritten 2026-05-16; see the module
docstring for the postmortem on why the previous design leaked $1k/day):

  * Kill-switch (``PI_TYPST_DISABLE_EXPLICIT_CACHE=1``) short-circuits
    everything before any network I/O.
  * Lookup is **lazy and per-package** — a search_docs call for
    ``cetz`` only ever creates / adopts the cache for ``cetz``.
  * On a cold miss we **list** the project's existing
    ``cachedContents`` and adopt one whose ``displayName`` matches
    ``typst-docs-{package}-v1``, instead of creating a duplicate.
  * Concurrent miss-callers for the SAME package collapse onto one
    create under a per-package lock; concurrent callers for DIFFERENT
    packages run in parallel.
  * Create failures negative-cache the package for ``_NEG_CACHE_TTL_S``
    so we don't hammer Vertex on every subsequent call.
  * ``snapshot()`` reflects live state for the health probe.
"""
from __future__ import annotations

import asyncio
import json

import pytest


@pytest.fixture(autouse=True)
def _reset_state():
    """Each test starts with an empty cache map."""
    from services import gemini_cache

    gemini_cache._reset_for_tests()
    yield
    gemini_cache._reset_for_tests()


@pytest.fixture
def fake_corpus():
    return {
        "typst": "TYPST CORPUS BODY " * 100,
        "cetz": "CETZ CORPUS BODY " * 100,
        "fletcher": "FLETCHER CORPUS BODY " * 100,
        "empty_pkg": "",
    }


def _fake_persona(_pkg: str) -> str:
    return "PERSONA"


_FAKE_RULES = "RULES BLOCK"


# ── Test double for httpx.AsyncClient ────────────────────────────────
class _FakeResponse:
    def __init__(self, *, status_code: int, payload: dict | str = "") -> None:
        self.status_code = status_code
        if isinstance(payload, dict):
            self._payload = payload
            self.text = json.dumps(payload)
        else:
            self._payload = {}
            self.text = payload

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """One instance is created per ``async with httpx.AsyncClient(...)``
    block. We replay a queue of responses keyed by HTTP method so a
    test can simulate "post succeeds, delete is fire-and-forget".
    """

    def __init__(self, responder, calls: list[dict]) -> None:
        self._responder = responder
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, *, headers=None) -> _FakeResponse:
        self._calls.append({"method": "GET", "url": url})
        return self._responder("GET", url, None)

    async def post(self, url, *, headers=None, content=None) -> _FakeResponse:
        body = json.loads(content) if isinstance(content, (str, bytes)) else content
        self._calls.append({"method": "POST", "url": url, "body": body})
        return self._responder("POST", url, body)

    async def delete(self, url, *, headers=None) -> _FakeResponse:
        self._calls.append({"method": "DELETE", "url": url})
        return self._responder("DELETE", url, None)


def _install_fake_client(monkeypatch, responder):
    """Patch ``httpx.AsyncClient`` to ours; return the call log list."""
    calls: list[dict] = []

    def _factory(*args, **kwargs):
        return _FakeClient(responder, calls)

    import services.gemini_cache as gc

    monkeypatch.setattr(gc.httpx, "AsyncClient", _factory)
    return calls


def _empty_list_response() -> _FakeResponse:
    """Default: project has no existing caches — every miss must create."""
    return _FakeResponse(status_code=200, payload={"cachedContents": []})


def _ok_create_response(body: dict) -> _FakeResponse:
    """Default: every POST creates a successful cache.

    Cache id is derived from the displayName so concurrent callers for
    the same package see the same name and we can spot duplicate
    creates in the assertion.
    """
    cache_id = "cache-" + (body.get("displayName") or "x").replace("/", "-")
    return _FakeResponse(
        status_code=200,
        payload={
            "name": f"projects/p/locations/us-central1/cachedContents/{cache_id}",
            "model": body["model"],
            "ttl": body["ttl"],
            "displayName": body["displayName"],
        },
    )


def _empty_list_then_create_responder(method, url, body):
    if method == "GET":
        return _empty_list_response()
    if method == "POST":
        return _ok_create_response(body or {})
    if method == "DELETE":
        return _FakeResponse(status_code=204)
    raise AssertionError(f"unexpected method {method}")


# ── Tests ────────────────────────────────────────────────────────────
def test_kill_switch_short_circuits(monkeypatch, fake_corpus):
    monkeypatch.setenv("PI_TYPST_DISABLE_EXPLICIT_CACHE", "1")
    from services import gemini_cache

    assert gemini_cache.is_disabled() is True

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="us-central1-aiplatform.googleapis.com",
        token_provider=lambda: "tok",
    ))
    assert name is None
    assert calls == []  # nothing should have hit the wire


def test_non_gemini_model_short_circuits(monkeypatch, fake_corpus):
    """Anthropic-on-Vertex uses a different cache mechanism; this layer
    must stay out of the way."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="claude-haiku-4-5",
        project="p",
        location="us-east5",
        host="us-east5-aiplatform.googleapis.com",
        token_provider=lambda: "tok",
    ))
    assert name is None
    assert calls == []


def test_empty_corpus_skips(monkeypatch, fake_corpus):
    """A package with empty corpus text is filtered before any I/O —
    the route falls back to inline (which is a no-op for empty too)."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="empty_pkg",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert name is None
    assert calls == []


def test_first_call_creates_only_the_requested_package(monkeypatch, fake_corpus):
    """Lazy per-package: a call for ``typst`` MUST NOT create caches for
    ``cetz`` / ``fletcher``. That was the bug burning the storage bill."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="us-central1-aiplatform.googleapis.com",
        token_provider=lambda: "tok",
    ))
    assert name is not None
    assert name.startswith("projects/p/locations/us-central1/cachedContents/")

    posts = [c for c in calls if c["method"] == "POST"]
    assert len(posts) == 1, f"expected 1 create for typst, got {len(posts)}"
    assert posts[0]["body"]["displayName"] == "typst-docs-typst-v1"

    snap = gemini_cache.snapshot()
    assert set(snap.keys()) == {"typst"}  # cetz / fletcher untouched


def test_second_call_uses_in_memory_cache(monkeypatch, fake_corpus):
    """Once warm, subsequent lookups don't hit Vertex."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    name1 = asyncio.run(gemini_cache.get_or_refresh(
        package="cetz",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    posts_after_warmup = sum(1 for c in calls if c["method"] == "POST")
    assert posts_after_warmup == 1

    calls.clear()
    name2 = asyncio.run(gemini_cache.get_or_refresh(
        package="cetz",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert name1 == name2
    # No I/O at all on the warm path — not even the LIST.
    assert calls == []


def test_concurrent_same_package_callers_collapse(monkeypatch, fake_corpus):
    """Five concurrent first-callers for the same package must produce
    EXACTLY ONE create (the per-package lock is doing its job)."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    async def _go():
        return await asyncio.gather(*[
            gemini_cache.get_or_refresh(
                package="typst",
                corpus=fake_corpus,
                persona_for=_fake_persona,
                rules=_FAKE_RULES,
                model_id="gemini-2.5-flash",
                project="p",
                location="us-central1",
                host="x",
                token_provider=lambda: "tok",
            )
            for _ in range(5)
        ])

    results = asyncio.run(_go())
    assert len(set(results)) == 1
    posts = [c for c in calls if c["method"] == "POST"]
    assert len(posts) == 1, f"expected 1 create, got {len(posts)}"


def test_concurrent_different_packages_run_in_parallel(monkeypatch, fake_corpus):
    """Misses for different packages do NOT serialise — each gets its
    own lock so cetz doesn't wait on typst."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    async def _go():
        return await asyncio.gather(*[
            gemini_cache.get_or_refresh(
                package=pkg,
                corpus=fake_corpus,
                persona_for=_fake_persona,
                rules=_FAKE_RULES,
                model_id="gemini-2.5-flash",
                project="p",
                location="us-central1",
                host="x",
                token_provider=lambda: "tok",
            )
            for pkg in ("typst", "cetz", "fletcher")
        ])

    results = asyncio.run(_go())
    assert all(r is not None for r in results)
    # All three distinct names — no accidental sharing.
    assert len(set(results)) == 3
    posts = [c for c in calls if c["method"] == "POST"]
    assert {p["body"]["displayName"] for p in posts} == {
        "typst-docs-typst-v1",
        "typst-docs-cetz-v1",
        "typst-docs-fletcher-v1",
    }


def test_adopts_existing_cache_with_matching_display_name(monkeypatch, fake_corpus):
    """If Vertex already has a fresh cache with our displayName (e.g.
    survived a process restart), we adopt it instead of creating a
    duplicate. THIS is what kills the leak."""
    from services import gemini_cache
    from datetime import datetime, timedelta, timezone

    far_future = (datetime.now(tz=timezone.utc) + timedelta(minutes=45)).isoformat()
    near_past = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).isoformat()
    existing_name = "projects/p/locations/global/cachedContents/legacy-1"

    def _responder(method, url, body):
        if method == "GET":
            return _FakeResponse(status_code=200, payload={
                "cachedContents": [
                    {
                        "name": existing_name,
                        "displayName": "typst-docs-typst-v1",
                        "model": "projects/p/locations/global/publishers/google/models/gemini-2.5-flash",
                        "createTime": near_past,
                        "expireTime": far_future,
                    },
                ]
            })
        if method == "POST":
            raise AssertionError("must NOT create when an existing cache is adoptable")
        if method == "DELETE":
            return _FakeResponse(status_code=204)
        raise AssertionError(method)

    calls = _install_fake_client(monkeypatch, _responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="global",
        host="aiplatform.googleapis.com",
        token_provider=lambda: "tok",
    ))
    assert name == existing_name
    posts = [c for c in calls if c["method"] == "POST"]
    assert posts == []


def test_adoption_keeps_freshest_and_deletes_duplicates(monkeypatch, fake_corpus):
    """When the legacy leak left several alive caches with the same
    displayName, we adopt the freshest and queue the rest for delete.
    THIS is the self-heal path."""
    from services import gemini_cache
    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone.utc)

    def _at(minutes: int) -> str:
        return (now + timedelta(minutes=minutes)).isoformat()

    duplicates = [
        ("projects/p/locations/global/cachedContents/oldest", _at(10)),
        ("projects/p/locations/global/cachedContents/middle", _at(30)),
        ("projects/p/locations/global/cachedContents/newest", _at(50)),
    ]

    def _responder(method, url, body):
        if method == "GET":
            return _FakeResponse(status_code=200, payload={
                "cachedContents": [
                    {
                        "name": n,
                        "displayName": "typst-docs-typst-v1",
                        "model": "projects/p/locations/global/publishers/google/models/gemini-2.5-flash",
                        "createTime": _at(-5),
                        "expireTime": exp,
                    } for n, exp in duplicates
                ]
            })
        if method == "POST":
            raise AssertionError("must adopt, not create")
        if method == "DELETE":
            return _FakeResponse(status_code=204)
        raise AssertionError(method)

    calls = _install_fake_client(monkeypatch, _responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="global",
        host="aiplatform.googleapis.com",
        token_provider=lambda: "tok",
    ))
    # Adopted the one expiring LATEST (created most recently).
    assert name.endswith("/newest")
    # The two older duplicates are scheduled for cleanup.
    asyncio.run(asyncio.sleep(0))  # let the fire-and-forget tasks run
    deletes = [c for c in calls if c["method"] == "DELETE"]
    deleted_names = {c["url"].rsplit("/", 1)[-1] for c in deletes}
    assert deleted_names == {"oldest", "middle"}


def test_create_failure_sets_negative_cache(monkeypatch, fake_corpus):
    """If Vertex 400s on create, we negative-cache the package so a
    subsequent call doesn't bill Vertex's reject path again."""
    from services import gemini_cache

    def _responder(method, url, body):
        if method == "GET":
            return _empty_list_response()
        if method == "POST":
            return _FakeResponse(
                status_code=400,
                payload="cached content too small (minimum 32768 tokens)",
            )
        return _FakeResponse(status_code=204)

    calls = _install_fake_client(monkeypatch, _responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="cetz",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert name is None

    posts_first = sum(1 for c in calls if c["method"] == "POST")
    assert posts_first == 1

    # Second call — negative cache must short-circuit, no new POST.
    name2 = asyncio.run(gemini_cache.get_or_refresh(
        package="cetz",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert name2 is None
    assert sum(1 for c in calls if c["method"] == "POST") == posts_first


def test_no_token_skips_gracefully(monkeypatch, fake_corpus):
    """token_provider returning None must not crash — the route falls
    back to inline-corpus path on its own."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: None,
    ))
    assert name is None
    # We shouldn't even have hit the LIST when there's no token.
    assert calls == []


def test_default_ttl_is_one_hour(monkeypatch):
    """The whole reason for this rewrite — keep the default cheap."""
    monkeypatch.delenv("PI_TYPST_CACHE_TTL_S", raising=False)
    import services.gemini_cache as gc
    assert gc._ttl_seconds() == 3600


def test_ttl_floor_is_600s(monkeypatch):
    """Operators can lengthen the TTL but anything shorter than the
    create-overhead window erases the input-discount savings."""
    monkeypatch.setenv("PI_TYPST_CACHE_TTL_S", "30")
    import services.gemini_cache as gc
    assert gc._ttl_seconds() == 600


def test_prewarm_caches_is_a_noop(monkeypatch, fake_corpus):
    """prewarm_caches stayed in the public API for backwards-compat
    with app.py's lifespan hook, but it must not create anything."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)

    asyncio.run(gemini_cache.prewarm_caches(
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert calls == []
    assert gemini_cache.snapshot() == {}


# ── Stale-cache detection ───────────────────────────────────────────


@pytest.mark.parametrize(
    "status,body,expected",
    [
        # Real shapes Vertex returns when the cachedContent reference is bad.
        (404, '{"error":{"code":404,"status":"NOT_FOUND","message":"Cached content with name '
              '\'projects/p/locations/global/cachedContents/x\' was not found."}}', True),
        (400, '{"error":{"code":400,"status":"FAILED_PRECONDITION",'
              '"message":"The cachedContent has expired."}}', True),
        (400, "INVALID_ARGUMENT: cachedContent does not exist", True),
        (400, "cached content not found", True),
        # Negative cases — these are NOT stale-cache failures.
        (404, '{"error":{"code":404,"message":"Model not found"}}', False),
        (401, "cached content not found", False),  # auth, not cache
        (429, "cachedContent missing", False),     # quota, retry-storm guard
        (500, "internal error", False),
        (200, "ok", False),
    ],
)
def test_is_stale_cache_error_classification(status, body, expected):
    """The classifier must light up on the real shapes Vertex returns
    AND must NOT trigger on auth / quota / generic 5xx errors that
    happen to mention 'cache'."""
    from services import gemini_cache

    assert gemini_cache.is_stale_cache_error(status=status, body=body) is expected


def test_invalidate_drops_db_row_and_calls_delete(monkeypatch, fake_corpus):
    """When the route detects a stale-cache 4xx it calls invalidate().
    That MUST drop the DB row AND fire a Vertex DELETE (best-effort).
    Otherwise the next get_or_refresh would just hand back the same
    bad cache_name."""
    from services import gemini_cache, gemini_cache_db

    # Phase 1: create a cache so there's a row to invalidate.
    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)
    name = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert name is not None
    assert gemini_cache_db.lookup("typst") is not None

    # Phase 2: invalidate.
    calls.clear()
    asyncio.run(gemini_cache.invalidate(
        package="typst",
        project="p",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert gemini_cache_db.lookup("typst") is None
    deletes = [c for c in calls if c["method"] == "DELETE"]
    assert len(deletes) == 1
    assert name and deletes[0]["url"].endswith(name)

    evictions = gemini_cache_db.list_evictions()
    assert any(e["reason"] == "stale-on-use" and e["ok"] == 1 for e in evictions)


def test_invalidate_then_get_creates_fresh(monkeypatch, fake_corpus):
    """After invalidation the next get_or_refresh call MUST create a
    fresh cache rather than returning the dead one. End-to-end of the
    stale-cache recovery flow the route relies on."""
    from services import gemini_cache, gemini_cache_db

    create_count = 0

    def _responder(method, url, body):
        nonlocal create_count
        if method == "GET":
            return _empty_list_response()
        if method == "POST":
            create_count += 1
            return _ok_create_response(body or {})
        if method == "DELETE":
            return _FakeResponse(status_code=204)
        raise AssertionError(method)

    _install_fake_client(monkeypatch, _responder)

    name1 = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert create_count == 1

    asyncio.run(gemini_cache.invalidate(
        package="typst", project="p", host="x", token_provider=lambda: "tok",
    ))

    name2 = asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    # A second create — the dead row was purged so the registry was
    # forced to rebuild rather than returning the old name.
    assert create_count == 2
    # And the registry now points at the new resource.
    row = gemini_cache_db.lookup("typst")
    assert row is not None
    assert row["cache_name"] == name2


# ── Sweeper / idle eviction ─────────────────────────────────────────


def test_sweeper_kills_idle_caches(monkeypatch, fake_corpus):
    """A row whose last_used_epoch is older than IDLE_TTL must get
    deleted by the sweeper, AND the corresponding Vertex DELETE must
    have been issued."""
    import time as _time
    from services import gemini_cache, gemini_cache_db

    # Phase 1: create one cache.
    calls = _install_fake_client(monkeypatch, _empty_list_then_create_responder)
    asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    assert gemini_cache_db.lookup("typst") is not None

    # Phase 2: rewind the row's last_used_epoch into the past so the
    # sweeper sees it as idle. We do this directly in SQL because
    # waiting an actual hour is obviously a no-go.
    with gemini_cache_db._db() as conn:
        conn.execute(
            "UPDATE gemini_caches SET last_used_epoch = ? WHERE package = ?",
            (_time.time() - (gemini_cache_db._idle_ttl_s() + 60), "typst"),
        )

    # Phase 3: run one sweep cycle. The DELETE callback talks via the
    # patched httpx, so we can assert the Vertex DELETE went out.
    calls.clear()
    gemini_cache.configure_sweeper(
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    )
    counters = asyncio.run(gemini_cache.run_sweep_now())

    assert counters["deleted"] == 1
    assert counters["errors"] == 0
    assert gemini_cache_db.lookup("typst") is None
    deletes = [c for c in calls if c["method"] == "DELETE"]
    assert len(deletes) == 1


def test_sweeper_lease_prevents_thundering_herd(monkeypatch):
    """Two near-simultaneous sweep claims must not both win — the
    second has to defer until the interval elapses. Without this, N
    Uvicorn workers would each issue list+delete on every interval."""
    from services import gemini_cache_db

    # First claim wins.
    assert gemini_cache_db.claim_sweeper_lease() is True
    # Second claim immediately after must lose (no time elapsed).
    assert gemini_cache_db.claim_sweeper_lease() is False


def test_run_sweep_now_bypasses_lease(monkeypatch, fake_corpus):
    """The admin "force a sweep now" entry-point ignores the lease so
    operators get an immediate cycle. (Otherwise hitting the button
    twice in a minute would be a no-op the second time.)"""
    from services import gemini_cache, gemini_cache_db

    _install_fake_client(monkeypatch, _empty_list_then_create_responder)
    gemini_cache.configure_sweeper(
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    )
    # Claim the lease first so a normal cycle would defer.
    assert gemini_cache_db.claim_sweeper_lease() is True
    counters = asyncio.run(gemini_cache.run_sweep_now())
    # Either deleted/swept or simply ran — the key invariant is that
    # the call was NOT skipped due to the lease.
    assert counters.get("skipped_lease", 0) == 0


def test_idle_ttl_floor_is_600s(monkeypatch):
    """Aggressively short idle TTLs would erase cache savings — clamp
    the same way the per-cache TTL is clamped."""
    monkeypatch.setenv("PI_TYPST_CACHE_IDLE_TTL_S", "30")
    from services import gemini_cache_db
    assert gemini_cache_db._idle_ttl_s() == 600


def test_default_idle_ttl_is_one_hour(monkeypatch):
    """The user's stated requirement: "if cache 1 isn't touched for an
    hour, delete it". Default idle TTL is the floor for that guarantee."""
    monkeypatch.delenv("PI_TYPST_CACHE_IDLE_TTL_S", raising=False)
    from services import gemini_cache_db
    assert gemini_cache_db._idle_ttl_s() == 3600


def test_touch_on_hit_resets_idle_clock(monkeypatch, fake_corpus):
    """A get_or_refresh hit on a warm row MUST bump last_used_at — that
    bump is the entire signal the sweeper uses to decide "still in use,
    keep alive"."""
    import time as _time
    from services import gemini_cache, gemini_cache_db

    _install_fake_client(monkeypatch, _empty_list_then_create_responder)
    asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    row1 = gemini_cache_db.lookup("typst")
    assert row1 is not None
    t1 = float(row1["last_used_epoch"])

    # Sleep a hair so the second touch can observably advance the clock.
    _time.sleep(0.05)

    asyncio.run(gemini_cache.get_or_refresh(
        package="typst",
        corpus=fake_corpus,
        persona_for=_fake_persona,
        rules=_FAKE_RULES,
        model_id="gemini-2.5-flash",
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    ))
    row2 = gemini_cache_db.lookup("typst")
    assert row2 is not None
    assert float(row2["last_used_epoch"]) > t1


def test_reconcile_kills_orphans(monkeypatch, fake_corpus):
    """If Vertex has a cache matching our displayName pattern that we
    DON'T know about (orphan from a crashed previous boot, or a
    pre-DB-era leak), the reconcile pass must delete it."""
    from services import gemini_cache, gemini_cache_db

    orphan = "projects/p/locations/us-central1/cachedContents/orphan-1"

    def _responder(method, url, body):
        if method == "GET":
            return _FakeResponse(status_code=200, payload={
                "cachedContents": [
                    {
                        "name": orphan,
                        "displayName": "typst-docs-typst-v1",
                        "model": "...",
                        "createTime": "2026-05-01T00:00:00Z",
                        "expireTime": "2099-01-01T00:00:00Z",
                    }
                ]
            })
        if method == "DELETE":
            return _FakeResponse(status_code=204)
        if method == "POST":
            return _ok_create_response(body or {})
        raise AssertionError(method)

    calls = _install_fake_client(monkeypatch, _responder)

    # No DB row for typst → orphan present on Vertex → reconcile kills.
    gemini_cache.configure_sweeper(
        project="p",
        location="us-central1",
        host="x",
        token_provider=lambda: "tok",
    )
    counters = asyncio.run(gemini_cache.run_sweep_now())

    assert counters["orphans"] == 1
    assert counters["deleted"] >= 1
    deleted_names = {
        c["url"].rsplit("/v1/", 1)[-1]
        for c in calls if c["method"] == "DELETE"
    }
    assert orphan in deleted_names
    evictions = gemini_cache_db.list_evictions()
    assert any(
        e["reason"] == "reconcile-orphan" and e["cache_name"] == orphan
        for e in evictions
    )
