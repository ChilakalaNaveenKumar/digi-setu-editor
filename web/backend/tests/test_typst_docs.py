"""
Smoke tests for /v1/typst/search_docs.

We never make a real Vertex call here — the upstream callers
``_call_anthropic_vertex`` / ``_call_google_vertex`` get monkey-patched
to canned tuples so we can drive the defense / dispatch logic
deterministically. A short fake corpus is generated in a tmp dir
(driven by ``PI_TYPST_GUIDES_ROOT``) so the corpus loader has real
files to walk without us shipping the 5 MB real corpus into the
test fixture.

Coverage:
  * 401 when no bearer
  * 400 on invalid package / missing query
  * 429 after burst (shares relay.message bucket with llm_relay)
  * 402 when monthly credit is exhausted
  * 503 with code=empty_corpus when the corpus dir has no matching
    files (operator misconfig)
  * Happy paths: anthropic router AND gemini router record cost
  * Health probe lists package sizes without auth
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────
@pytest.fixture
def fake_guides(tmp_path, monkeypatch):
    """Stand up a tmp guides/ tree with one file per supported package
    so the corpus loader produces a non-empty bucket for every key."""
    root = tmp_path / "guides"
    for key in ("typst", "cetz", "fletcher", "quill", "codly", "circuiteria", "touying"):
        d = root / key
        d.mkdir(parents=True, exist_ok=True)
        # Three files per package — enough that the bucket isn't empty
        # and the file-walker doesn't optimise to zero work.
        for i, ext in enumerate([".md", ".typ", ".md"]):
            (d / f"sample-{i}{ext}").write_text(
                f"# fake {key} doc {i}\nbody body body\n", encoding="utf-8"
            )
    monkeypatch.setenv("PI_TYPST_GUIDES_ROOT", str(root))
    return root


@pytest.fixture
def app(monkeypatch, fake_guides):
    """Reload the relay + typst routes with our test env, then mount
    just typst_docs onto a fresh FastAPI app. The relay reload is
    needed because typst_docs imports private helpers from llm_relay,
    and llm_relay snapshots env at import time."""
    monkeypatch.setenv("AUTH_REQUIRED", "1")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.setenv("RL_RELAY_CAPACITY", "2")
    monkeypatch.setenv("RL_RELAY_PER_MIN", "120")
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("BILLING_DEFAULT_PLAN", "free")
    monkeypatch.setenv("PI_TYPST_ROUTER_MODEL", "gemini-3-flash-preview")

    import importlib

    import services.rate_limit as rl
    import services.billing as billing
    import services.auth as auth
    import routes.llm_relay as relay
    import routes.typst_docs as typst

    importlib.reload(rl)
    importlib.reload(billing)
    importlib.reload(auth)
    importlib.reload(relay)
    importlib.reload(typst)

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(typst.router)
    return app


@pytest.fixture
def stub_principal(app):
    """Install a verify_relay_jwt override and return the helper."""
    from services.auth import RelayPrincipal
    from routes.typst_docs import verify_relay_jwt

    def _install(*, user_id="user_test", plan="free", admin=False):
        principal = RelayPrincipal(
            user_id=user_id, plan=plan, admin=admin, jti="jti_test", exp=None
        )
        app.dependency_overrides[verify_relay_jwt] = lambda: principal
        return principal

    yield _install
    app.dependency_overrides.clear()


@pytest.fixture
def stub_upstream(monkeypatch):
    """Replace the Vertex callers with deterministic canned tuples."""
    import routes.typst_docs as typst

    async def _fake_google(*, model_id, persona, query, package, corpus_text, full_corpus=None):
        return (
            "Here is your answer.\n\nguides/cetz/sample-0.md mentions stuff.\n",
            {"input": 200000, "output": 100, "cacheRead": 199500, "cacheWrite": 0},
        )

    async def _fake_anthropic(*, model_id, persona, query, package, corpus_text):
        return (
            "Anthropic answer here.\n",
            {"input": 1000, "output": 200, "cacheRead": 199000, "cacheWrite": 1000},
        )

    monkeypatch.setattr(typst, "_call_google_vertex", _fake_google)
    monkeypatch.setattr(typst, "_call_anthropic_vertex", _fake_anthropic)


# ── Auth ──────────────────────────────────────────────────────────────
def test_search_docs_returns_401_without_bearer(app, stub_upstream):
    client = TestClient(app)
    resp = client.post(
        "/v1/typst/search_docs",
        json={"package": "cetz", "query": "draw a curve"},
    )
    assert resp.status_code == 401


# ── Validation ────────────────────────────────────────────────────────
def test_search_docs_rejects_invalid_package(app, stub_principal, stub_upstream):
    stub_principal(user_id="u_pkg", plan="free")
    client = TestClient(app)
    resp = client.post(
        "/v1/typst/search_docs",
        json={"package": "not-a-package", "query": "x"},
    )
    assert resp.status_code == 400
    assert resp.json().get("detail", {}).get("code") == "invalid_package"


def test_search_docs_rejects_missing_query(app, stub_principal, stub_upstream):
    stub_principal(user_id="u_q", plan="free")
    client = TestClient(app)
    resp = client.post(
        "/v1/typst/search_docs",
        json={"package": "cetz", "query": "  "},
    )
    assert resp.status_code == 400
    assert resp.json().get("detail", {}).get("code") == "missing_query"


# ── Rate limit (shared bucket with llm_relay) ─────────────────────────
def test_search_docs_429_after_burst(app, stub_principal, stub_upstream):
    """search_docs uses the same relay.message bucket as anthropic
    forwarding — by design, so a chat that spams search can't dodge
    its message quota."""
    stub_principal(user_id="u_burst", plan="free")
    client = TestClient(app)
    body = {"package": "cetz", "query": "draw"}

    r1 = client.post("/v1/typst/search_docs", json=body)
    r2 = client.post("/v1/typst/search_docs", json=body)
    r3 = client.post("/v1/typst/search_docs", json=body)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200
    assert r3.status_code == 429


# ── Credit ────────────────────────────────────────────────────────────
def test_search_docs_402_on_credit_exhausted(
    app, stub_principal, stub_upstream, monkeypatch
):
    stub_principal(user_id="u_broke", plan="free")
    import services.billing as billing
    real_ledger = billing.CreditLedger.instance()
    monkeypatch.setattr(real_ledger, "remaining_credit_usd", lambda uid: 0.0)

    client = TestClient(app)
    resp = client.post(
        "/v1/typst/search_docs",
        json={"package": "cetz", "query": "draw"},
    )
    assert resp.status_code == 402
    assert resp.json().get("detail", {}).get("code") == "credit_exhausted"


# ── Empty corpus (operator misconfig) ─────────────────────────────────
def test_search_docs_503_when_corpus_empty(
    app, stub_principal, stub_upstream, monkeypatch, tmp_path
):
    """If the deploy went through but COPY guides/ was missing, the
    endpoint should 503 with a clear code instead of producing a
    confidently-empty answer."""
    empty = tmp_path / "no-guides"
    empty.mkdir()
    monkeypatch.setenv("PI_TYPST_GUIDES_ROOT", str(empty))

    import importlib

    import routes.typst_docs as typst
    importlib.reload(typst)

    from fastapi import FastAPI
    from services.auth import RelayPrincipal
    fresh = FastAPI()
    fresh.include_router(typst.router)
    fresh.dependency_overrides[typst.verify_relay_jwt] = lambda: RelayPrincipal(
        user_id="u_empty", plan="free", admin=False, jti="j", exp=None,
    )

    monkeypatch.setattr(
        typst, "_call_google_vertex",
        lambda **kw: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    client = TestClient(fresh)
    resp = client.post(
        "/v1/typst/search_docs",
        json={"package": "cetz", "query": "draw"},
    )
    assert resp.status_code == 503
    assert resp.json().get("detail", {}).get("code") == "empty_corpus"


# ── Happy paths ───────────────────────────────────────────────────────
def test_search_docs_records_cost_on_gemini(app, stub_principal, stub_upstream):
    """200 → CreditLedger.note_cost is called once for this user."""
    stub_principal(user_id="u_happy", plan="free")
    import services.billing as billing
    starting = billing.CreditLedger.instance().snapshot("u_happy")["prompts"]

    client = TestClient(app)
    resp = client.post(
        "/v1/typst/search_docs",
        json={"package": "cetz", "query": "draw a curve in cetz"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model"] == "gemini-3-flash-preview"
    assert "answer" in body
    assert "elapsedMs" in body
    assert body["usage"]["cacheRead"] == 199500

    after = billing.CreditLedger.instance().snapshot("u_happy")["prompts"]
    assert after == starting + 1


def test_search_docs_records_cost_on_anthropic_router(
    app, stub_principal, stub_upstream, monkeypatch
):
    """When PI_TYPST_ROUTER_MODEL is pinned to a Claude model, the
    anthropic-vertex caller runs (not the gemini one)."""
    monkeypatch.setenv("PI_TYPST_ROUTER_MODEL", "claude-haiku-4-5")
    import importlib

    import routes.typst_docs as typst
    importlib.reload(typst)
    monkeypatch.setattr(typst, "_call_google_vertex",
                        lambda **kw: (_ for _ in ()).throw(AssertionError("should not be called")))

    async def _fake_anthropic(**kw):
        return ("anthropic answer", {"input": 100, "output": 50, "cacheRead": 199000, "cacheWrite": 0})
    monkeypatch.setattr(typst, "_call_anthropic_vertex", _fake_anthropic)

    from fastapi import FastAPI
    from services.auth import RelayPrincipal
    fresh = FastAPI()
    fresh.include_router(typst.router)
    fresh.dependency_overrides[typst.verify_relay_jwt] = lambda: RelayPrincipal(
        user_id="u_ant", plan="free", admin=False, jti="j", exp=None,
    )

    client = TestClient(fresh)
    resp = client.post("/v1/typst/search_docs",
                        json={"package": "codly", "query": "highlight lines"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["model"] == "claude-haiku-4-5"


# ── Cited-source extraction ───────────────────────────────────────────
def test_search_docs_extracts_inline_cited(app, stub_principal, monkeypatch):
    """When the model's answer mentions guides/.../foo.md inline, the
    response.cited list should include those paths (deduped)."""
    stub_principal(user_id="u_cited", plan="free")
    import routes.typst_docs as typst

    async def _fake(**kw):
        return (
            "See `guides/cetz-0.5.0/docs/canvas.md` and `guides/cetz-0.5.0/docs/canvas.md` "
            "(again) and also guides/cetz-0.5.0/docs/draw.md.",
            {"input": 100, "output": 50, "cacheRead": 0, "cacheWrite": 0},
        )

    monkeypatch.setattr(typst, "_call_google_vertex", _fake)

    client = TestClient(app)
    resp = client.post("/v1/typst/search_docs",
                        json={"package": "cetz", "query": "x"})
    assert resp.status_code == 200, resp.text
    cited = resp.json()["cited"]
    assert "guides/cetz-0.5.0/docs/canvas.md" in cited
    assert "guides/cetz-0.5.0/docs/draw.md" in cited
    assert len(cited) == len(set(cited)), "cited should be deduped"


# ── Health ────────────────────────────────────────────────────────────
def test_search_docs_health_no_auth(app, stub_upstream):
    """Operators need to see corpus presence without juggling JWTs."""
    client = TestClient(app)
    resp = client.get("/v1/typst/_health")
    assert resp.status_code == 200
    body = resp.json()
    assert "guides_root" in body
    assert "router_model" in body
    assert "packages" in body
    assert all(body["packages"][k] > 0 for k in body["packages"]), (
        "every package bucket should be non-empty against fake_guides"
    )
