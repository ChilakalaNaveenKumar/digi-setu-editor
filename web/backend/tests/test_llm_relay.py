"""
Smoke tests for the LLM relay defenses.

These tests are fast: they never touch the network. The relay's
upstream forwarder (`_stream_upstream` and the non-stream `httpx.post`
fallback) is patched so we can assert each defense independently —
401 (auth), 429 (rate-limit), 403 (plan), 402 (credit) — without
needing real ADC, GCP, or a Vertex endpoint.

What's NOT covered here (run end-to-end via `pytest -m integration`
once we wire that target up):

  - Actual ADC token broker (`google.auth.default`)
  - Live Vertex streaming
  - Cost capture from real upstream SSE bytes
    (parsers ARE unit-tested below against canned bytes)

Run with:
    cd web/backend && source .venv/bin/activate && pytest tests/test_llm_relay.py -v
"""

from __future__ import annotations

import json
import os
from typing import Optional

import pytest
from fastapi.testclient import TestClient


# ── shared fixtures ────────────────────────────────────────────────────
@pytest.fixture
def app(monkeypatch):
    """Build a FastAPI app with auth + ADC mocked.

    We monkey-patch `verify_relay_jwt` to a stub principal so the test
    suite doesn't need a real Clerk SDK or JWT. Each test that wants to
    flex auth itself overrides the dep before issuing the call.
    """
    monkeypatch.setenv("AUTH_REQUIRED", "1")  # exercise prod paths
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    # Turn rate limits down so we can hit them deterministically in
    # one or two calls instead of 60. The relay bucket starts full at
    # capacity and refills at per-min/60, so capacity=2 + per_min=120
    # means two free calls then 429 until the next half-second tick.
    monkeypatch.setenv("RL_RELAY_CAPACITY", "2")
    monkeypatch.setenv("RL_RELAY_PER_MIN", "120")
    # Force a non-admin default so plan-gating isn't auto-bypassed.
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("BILLING_DEFAULT_PLAN", "free")

    # Reload services that snapshot env at import time so the new env
    # vars take effect.
    import importlib

    import services.rate_limit as rl
    import services.billing as billing
    import services.auth as auth
    import routes.llm_relay as relay

    importlib.reload(rl)
    importlib.reload(billing)
    importlib.reload(auth)
    importlib.reload(relay)

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(relay.router)
    return app


@pytest.fixture
def stub_principal(app):
    """Return a helper that installs a verify_relay_jwt override and
    yields the matching principal."""
    from services.auth import RelayPrincipal
    from routes.llm_relay import verify_relay_jwt

    def _install(*, user_id: str = "user_test", plan: str = "free", admin: bool = False):
        principal = RelayPrincipal(
            user_id=user_id, plan=plan, admin=admin, jti="jti_test", exp=None
        )
        app.dependency_overrides[verify_relay_jwt] = lambda: principal
        return principal

    yield _install
    app.dependency_overrides.clear()


@pytest.fixture
def mock_adc(monkeypatch):
    """Make `_adc_token` always return a fake bearer so we never try
    to load real ADC."""
    import routes.llm_relay as relay
    monkeypatch.setattr(relay, "_adc_token", lambda: "fake-bearer-token")


@pytest.fixture
def mock_upstream_ok(monkeypatch):
    """Replace the upstream call paths with no-op stubs that return
    a 200 + plausible Anthropic / Gemini response shape.

    Both the streaming `_stream_upstream` and the non-streaming
    `httpx.AsyncClient.post` fallback are stubbed because either
    branch may run depending on `stream=True/False`.
    """
    import routes.llm_relay as relay

    async def _stub_stream(**kwargs):
        async def _gen():
            yield b'event: message_delta\ndata: {"usage": {"input_tokens": 100, "output_tokens": 50}}\n\n'

        return 200, {"content-type": "text/event-stream"}, _gen()

    monkeypatch.setattr(relay, "_stream_upstream", _stub_stream)

    class _StubResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = ""

        def json(self):
            return {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }

    class _StubClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def post(self, *a, **kw):
            return _StubResp()

    monkeypatch.setattr(relay.httpx, "AsyncClient", _StubClient)


# ── auth ────────────────────────────────────────────────────────────────
def test_anthropic_returns_401_without_bearer(app, mock_adc):
    """No `Authorization: Bearer ...` → 401 with WWW-Authenticate hint."""
    client = TestClient(app)
    resp = client.post(
        "/v1/relay/anthropic/v1/messages",
        json={"model": "claude-sonnet-4-6", "messages": [], "stream": False},
    )
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("www-authenticate", "")


def test_anthropic_returns_401_on_invalid_jwt(app, mock_adc, monkeypatch):
    """Bearer token present but Clerk rejects it → 401."""
    import services.auth as auth

    monkeypatch.setattr(auth, "_verify_clerk_payload", lambda req: None)
    client = TestClient(app)
    resp = client.post(
        "/v1/relay/anthropic/v1/messages",
        headers={"Authorization": "Bearer not-a-real-jwt"},
        json={"model": "claude-sonnet-4-6", "messages": [], "stream": False},
    )
    assert resp.status_code == 401


# ── rate limit ─────────────────────────────────────────────────────────
def test_anthropic_returns_429_after_burst(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """Bucket starts at capacity=2 (env override). Two calls succeed,
    third hits 429 with Retry-After."""
    stub_principal(user_id="user_burst", plan="free")
    client = TestClient(app)
    body = {"model": "claude-sonnet-4-6", "messages": [], "stream": False}

    r1 = client.post("/v1/relay/anthropic/v1/messages", json=body)
    r2 = client.post("/v1/relay/anthropic/v1/messages", json=body)
    r3 = client.post("/v1/relay/anthropic/v1/messages", json=body)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert "retry-after" in {k.lower() for k in r3.headers.keys()}


# ── plan gating ────────────────────────────────────────────────────────
def test_anthropic_returns_403_when_model_above_plan(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """`gemini-2.5-flash` is `min_plan=enterprise` (hidden internal). A
    free-plan user asking for it should be refused at the relay edge."""
    stub_principal(user_id="user_planlow", plan="free")
    client = TestClient(app)

    resp = client.post(
        "/v1/relay/google/v1beta/models/gemini-2.5-flash:generateContent",
        json={"contents": []},
    )
    assert resp.status_code == 403
    body = resp.json()
    detail = body.get("detail", {})
    assert detail.get("code") == "plan_too_low"
    assert detail.get("min_plan") == "enterprise"
    assert detail.get("your_plan") == "free"


def test_anthropic_returns_403_on_unknown_model(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """Defense-in-depth: an unknown model id must NOT be forwarded — even
    if we have ADC for it on the GCP side. Forces clients to use
    catalogued ids only."""
    stub_principal(user_id="user_badmodel", plan="enterprise", admin=False)
    client = TestClient(app)

    resp = client.post(
        "/v1/relay/anthropic/v1/messages",
        json={"model": "not-a-real-model", "messages": [], "stream": False},
    )
    assert resp.status_code == 403
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "model_not_found"


# ── credit gating ──────────────────────────────────────────────────────
def test_anthropic_returns_402_on_credit_exhausted(
    app, stub_principal, mock_adc, mock_upstream_ok, monkeypatch
):
    """When the user's monthly credit is gone, the relay MUST refuse the
    call before any upstream bytes are spent. Asserts the 402 carries a
    structured detail the desktop client can render."""
    stub_principal(user_id="user_broke", plan="free")

    # Force the ledger to report zero remaining for this user. We patch
    # the helper directly because mutating the in-memory ledger state
    # would also affect the snapshot/note_cost paths (out of scope).
    import services.billing as billing

    real_ledger = billing.CreditLedger.instance()
    monkeypatch.setattr(real_ledger, "remaining_credit_usd", lambda uid: 0.0)

    client = TestClient(app)
    resp = client.post(
        "/v1/relay/anthropic/v1/messages",
        json={"model": "claude-sonnet-4-6", "messages": [], "stream": False},
    )
    assert resp.status_code == 402
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "credit_exhausted"
    assert detail.get("plan") == "free"


# ── happy paths ────────────────────────────────────────────────────────
def test_anthropic_non_streaming_records_cost(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """200 response → CreditLedger.note_cost is called. We don't snoop
    its internals (test_billing.py covers cost math); we just verify
    the relay didn't 5xx and that one cost event landed."""
    stub_principal(user_id="user_happy", plan="free")
    import services.billing as billing

    starting = billing.CreditLedger.instance().snapshot("user_happy")["prompts"]

    client = TestClient(app)
    resp = client.post(
        "/v1/relay/anthropic/v1/messages",
        json={"model": "claude-sonnet-4-6", "messages": [], "stream": False},
    )
    assert resp.status_code == 200, resp.text

    after = billing.CreditLedger.instance().snapshot("user_happy")["prompts"]
    assert after == starting + 1, "expected note_cost to bump the prompt counter"


# ── ADC error path ─────────────────────────────────────────────────────
def test_anthropic_returns_503_when_adc_unavailable(
    app, stub_principal, monkeypatch
):
    """Defense for misconfigured deploys: relay should 503 (not crash)
    when ADC isn't available, with a clear `code` for ops to grep on."""
    stub_principal(user_id="user_adc", plan="free")
    import routes.llm_relay as relay
    monkeypatch.setattr(relay, "_adc_token", lambda: None)

    client = TestClient(app)
    resp = client.post(
        "/v1/relay/anthropic/v1/messages",
        json={"model": "claude-sonnet-4-6", "messages": [], "stream": False},
    )
    assert resp.status_code == 503
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "adc_unavailable"


# ── cost-parser unit tests ─────────────────────────────────────────────
def test_anthropic_sse_usage_parser_pulls_message_delta():
    """Final message_delta SSE frame is the source of truth for usage."""
    from routes.llm_relay import _parse_anthropic_usage_from_sse

    sse = (
        b"event: message_start\ndata: {\"type\":\"message_start\"}\n\n"
        b"event: content_block_delta\ndata: {\"delta\":{\"text\":\"hi\"}}\n\n"
        b"event: message_delta\ndata: {\"usage\":{\"input_tokens\":42,\"output_tokens\":17,\"cache_read_input_tokens\":3,\"cache_creation_input_tokens\":2}}\n\n"
        b"event: message_stop\ndata: {}\n\n"
    )
    usage = _parse_anthropic_usage_from_sse(sse)
    assert usage == {
        "input": 42,
        "output": 17,
        "cacheRead": 3,
        "cacheWrite": 2,
    }


def test_anthropic_sse_usage_parser_returns_none_on_garbage():
    """No message_delta in the buffer → None (we'd rather under-bill
    than crash on a truncated stream)."""
    from routes.llm_relay import _parse_anthropic_usage_from_sse

    assert _parse_anthropic_usage_from_sse(b"") is None
    assert _parse_anthropic_usage_from_sse(b"event: ping\ndata: {}\n\n") is None


def test_gemini_sse_usage_parser_pulls_usage_metadata():
    """Gemini puts the usageMetadata on the final SSE chunk."""
    from routes.llm_relay import _parse_gemini_usage_from_sse

    sse = (
        b"data: {\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"ok\"}]}}]}\n\n"
        b"data: {\"usageMetadata\":{\"promptTokenCount\":120,\"candidatesTokenCount\":80,\"cachedContentTokenCount\":30}}\n\n"
    )
    usage = _parse_gemini_usage_from_sse(sse)
    assert usage == {
        "input": 120,
        "output": 80,
        "cacheRead": 30,
        "cacheWrite": 0,
    }


# ── health probe ───────────────────────────────────────────────────────
def test_relay_health_does_not_require_auth(app, mock_adc):
    """Operators need to probe the relay without juggling JWTs. Health
    must be unauthenticated and report ADC + project visibility."""
    client = TestClient(app)
    resp = client.get("/v1/relay/_health")
    assert resp.status_code == 200
    body = resp.json()
    assert "adc" in body
    assert body.get("project") == "test-project"


# ── Vertex passthrough (used by desktop local-pi-via-relay) ───────────
def _vertex_url(model_id: str = "claude-sonnet-4-6", action: str = "rawPredict",
                publisher: str = "anthropic", project: str = "their-proj",
                location: str = "global") -> str:
    return (
        f"/v1/relay/vertex/v1/projects/{project}/locations/{location}"
        f"/publishers/{publisher}/models/{model_id}:{action}"
    )


def test_vertex_passthrough_rejects_bad_path_shape(app, stub_principal, mock_adc):
    """Defense-in-depth: only the well-known
    ``v1/projects/.../locations/.../publishers/.../models/{m}:action``
    layout is allowed. Anything else gets a structured 400 — we never
    forward arbitrary paths to Vertex (could be billed for ops we
    didn't price)."""
    stub_principal(user_id="u_path", plan="free")
    client = TestClient(app)

    resp = client.post("/v1/relay/vertex/some/random/path", json={})
    assert resp.status_code == 400
    assert resp.json().get("detail", {}).get("code") == "bad_relay_path"


def test_vertex_passthrough_rejects_unknown_publisher(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """`mistral` etc. aren't in our priced catalogue. Refuse — even
    if Vertex itself would happily serve the request."""
    stub_principal(user_id="u_pub", plan="free")
    client = TestClient(app)

    resp = client.post(
        _vertex_url(publisher="mistral", model_id="mistral-large"),
        json={},
    )
    assert resp.status_code == 403
    assert resp.json().get("detail", {}).get("code") == "publisher_not_allowed"


def test_vertex_passthrough_rejects_unknown_action(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """`:export` / `:tune` / `:batchPredict` aren't relayed. Only the
    four streaming + non-streaming generation actions are."""
    stub_principal(user_id="u_act", plan="free")
    client = TestClient(app)

    resp = client.post(_vertex_url(action="export"), json={})
    assert resp.status_code == 403
    assert resp.json().get("detail", {}).get("code") == "action_not_allowed"


def test_vertex_passthrough_rejects_bad_plan(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """Plan gating fires here too — the desktop path can't smuggle in
    an enterprise-only model by going through passthrough."""
    stub_principal(user_id="u_plan", plan="free")
    client = TestClient(app)

    resp = client.post(_vertex_url(model_id="gemini-2.5-flash",
                                    publisher="google"), json={})
    assert resp.status_code == 403
    assert resp.json().get("detail", {}).get("code") == "plan_too_low"


def test_vertex_passthrough_rate_limited_with_anthropic(
    app, stub_principal, mock_adc, mock_upstream_ok
):
    """Confirms the same `relay.message` bucket gates passthrough as
    /anthropic/v1/messages — i.e. a desktop user can't dodge limits by
    using one path over the other."""
    stub_principal(user_id="u_burst_v", plan="free")
    client = TestClient(app)
    body: dict = {}

    r1 = client.post(_vertex_url(), json=body)
    r2 = client.post(_vertex_url(), json=body)
    r3 = client.post(_vertex_url(), json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429


def test_vertex_passthrough_forwards_to_relay_owned_project(
    app, stub_principal, mock_adc, monkeypatch
):
    """Critical: even if the laptop encodes someone else's project in
    the URL, we MUST rewrite it to the relay's own GOOGLE_CLOUD_PROJECT
    before forwarding upstream. Otherwise a malicious / misconfigured
    desktop could bill arbitrary projects."""
    stub_principal(user_id="u_proj", plan="free")
    captured: dict = {}

    import routes.llm_relay as relay

    async def _capture_stream(method, url, headers, body, on_chunk=None):
        captured["url"] = url
        captured["body"] = body

        async def _gen():
            yield b'event: message_delta\ndata: {"usage": {"input_tokens": 1, "output_tokens": 1}}\n\n'

        return 200, {"content-type": "text/event-stream"}, _gen()

    monkeypatch.setattr(relay, "_stream_upstream", _capture_stream)

    client = TestClient(app)
    resp = client.post(
        _vertex_url(action="streamRawPredict", project="hacker-project",
                    location="us-central1"),
        json={"messages": []},
    )
    assert resp.status_code == 200, resp.text
    # The forwarded URL must say "test-project" (relay's own
    # GOOGLE_CLOUD_PROJECT from the fixture), not "hacker-project".
    assert "/projects/test-project/" in captured["url"], captured["url"]
    assert "hacker-project" not in captured["url"]
