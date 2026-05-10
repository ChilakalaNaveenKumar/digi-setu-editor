"""
Unit tests for ``services/gemini_cache``.

We never hit the real Vertex API — every test monkey-patches
``httpx.AsyncClient`` so we can drive the lifecycle (create, refresh,
parallel hits, kill-switch, partial failure) deterministically.

Things we verify:
  * Kill-switch short-circuits everything.
  * First call lockstep-creates ALL eligible packages.
  * Second call within TTL hits the in-memory map without re-creating.
  * Concurrent calls collapse onto one refresh under the lock.
  * Cache create failure for one package does NOT poison the others
    (and that package goes into the negative-cache window).
  * ``snapshot()`` reflects live state for the health probe.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

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
        "empty_pkg": "",  # filtered out by the eligibility check
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


def _ok_responder(_method, _url, _body) -> _FakeResponse:
    """Default responder: every POST creates a successful cache."""
    cache_id = "cache-" + str(abs(hash(json.dumps(_body, sort_keys=True))))[:8]
    return _FakeResponse(
        status_code=200,
        payload={
            "name": f"projects/p/locations/us-central1/cachedContents/{cache_id}",
            "model": _body["model"],
            "ttl": _body["ttl"],
        },
    )


# ── Tests ────────────────────────────────────────────────────────────
def test_kill_switch_short_circuits(monkeypatch, fake_corpus):
    monkeypatch.setenv("PI_TYPST_DISABLE_EXPLICIT_CACHE", "1")
    from services import gemini_cache

    assert gemini_cache.is_disabled() is True

    calls = _install_fake_client(monkeypatch, _ok_responder)

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

    calls = _install_fake_client(monkeypatch, _ok_responder)

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


def test_first_call_creates_all_eligible(monkeypatch, fake_corpus):
    """First miss triggers a lockstep refresh of every non-empty package."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _ok_responder)

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

    # 3 POSTs (typst, cetz, fletcher) — empty_pkg filtered out
    posts = [c for c in calls if c["method"] == "POST"]
    assert len(posts) == 3
    assert {c["body"]["displayName"] for c in posts} == {
        "typst-docs-typst-v1",
        "typst-docs-cetz-v1",
        "typst-docs-fletcher-v1",
    }

    # Snapshot reflects the new state.
    snap = gemini_cache.snapshot()
    assert set(snap.keys()) == {"typst", "cetz", "fletcher"}
    for entry in snap.values():
        assert entry["fresh"] is True
        assert entry["expiresInSeconds"] > 0


def test_second_call_uses_in_memory_cache(monkeypatch, fake_corpus):
    """Once warm, subsequent lookups don't hit Vertex."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _ok_responder)

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
    assert posts_after_warmup == 3

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
    # No new POSTs after warm-up.
    assert sum(1 for c in calls if c["method"] == "POST") == posts_after_warmup


def test_concurrent_callers_collapse_to_one_refresh(monkeypatch, fake_corpus):
    """Five concurrent first-callers must produce exactly one create
    storm, not five (the lock is doing its job)."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _ok_responder)

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
    # All five callers got the same resource name.
    assert len(set(results)) == 1
    # Three creates total (one per eligible package), NOT 5×3 = 15.
    posts = [c for c in calls if c["method"] == "POST"]
    assert len(posts) == 3


def test_partial_failure_does_not_poison_the_others(monkeypatch, fake_corpus):
    """If Vertex 400s on one package (e.g. corpus below min size), the
    others still get cached and the failed package goes into the
    negative-cache window."""
    from services import gemini_cache

    def _picky_responder(_method, _url, body) -> _FakeResponse:
        if body and body.get("displayName") == "typst-docs-cetz-v1":
            return _FakeResponse(
                status_code=400,
                payload="cached content too small (minimum 32768 tokens)",
            )
        return _ok_responder(_method, _url, body)

    calls = _install_fake_client(monkeypatch, _picky_responder)

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
    snap = gemini_cache.snapshot()
    assert set(snap.keys()) == {"typst", "fletcher"}  # cetz failed
    # Direct call for cetz returns None (negative-cache active).
    cetz_name = asyncio.run(gemini_cache.get_or_refresh(
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
    assert cetz_name is None
    # And the negative-cache window prevents another create attempt.
    posts_total = sum(1 for c in calls if c["method"] == "POST")
    # First refresh created 3 (1 failure), second call should NOT have
    # tried again because cetz is in neg-cache (0 new posts).
    assert posts_total == 3


def test_no_token_skips_gracefully(monkeypatch, fake_corpus):
    """token_provider returning None must not crash — the route falls
    back to inline-corpus path on its own."""
    from services import gemini_cache

    calls = _install_fake_client(monkeypatch, _ok_responder)

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
    assert calls == []
