"""
Smoke tests for the desktop LLM proxy + cloud-relay spawn helpers.

Coverage:
  * `relay_spawn.cloud_relay_provider_for` returns the SAME provider
    name (passthrough flavour — we don't swap providers any more) for
    Vertex-routed models, and None for everything else.
  * `relay_spawn.cloud_relay_subprocess_env` injects the right
    Vertex-base-URL env var and scrubs ADC hints from the spawn env
    (but KEEPS GOOGLE_CLOUD_PROJECT / LOCATION — the SDK needs them
    to build the request path).
  * `routes.llm_proxy` returns 401 with a structured detail when no
    desktop session is cached.
  * `routes.llm_proxy` strips client auth headers and replaces them
    with the cached bearer before forwarding to the cloud relay.

What's NOT covered (manual via end-to-end run):
  * The cloud relay actually accepting our forwarded JWT.
  * Streaming bytes flowing through both hops.
  * Pi-coding-agent honouring ``GOOGLE_VERTEX_BASE_URL`` — that's a
    pi-side patch that lands via patches/apply-edits.mjs §11.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── relay_spawn ────────────────────────────────────────────────────────
def _spec(pi_provider: str, model_id: str = "claude-sonnet-4-6"):
    """Build the smallest fake ModelSpec our helpers care about."""
    from services.models_registry import ModelCost, ModelSpec

    return ModelSpec(
        id=model_id,
        name=model_id,
        provider=pi_provider,
        pi_provider=pi_provider,
        family="anthropic" if "anthropic" in pi_provider else "google",
        cost=ModelCost(input=1.0, output=1.0, cache_read=0.0, cache_write=0.0),
        context_window=200_000,
        reasoning=False,
        min_plan="free",
        blurb="",
        hidden=False,
    )


def test_cloud_relay_provider_keeps_anthropic_vertex():
    """Passthrough flavour — provider name doesn't change. We just
    redirect the SDK base URL."""
    from services.relay_spawn import cloud_relay_provider_for

    assert cloud_relay_provider_for(_spec("anthropic-vertex")) == "anthropic-vertex"


def test_cloud_relay_provider_keeps_google_vertex():
    from services.relay_spawn import cloud_relay_provider_for

    assert cloud_relay_provider_for(_spec("google-vertex")) == "google-vertex"


def test_cloud_relay_provider_returns_none_for_byok_only_providers():
    """OpenAI-style providers and direct anthropic-without-vertex
    don't have a relay route — we don't relay raw OpenAI today, and
    direct Anthropic is BYOK-only. Both must return None so the
    dispatcher falls through to the WS-relay fallback (or refuses)."""
    from services.relay_spawn import cloud_relay_provider_for

    assert cloud_relay_provider_for(_spec("openai")) is None
    assert cloud_relay_provider_for(_spec("anthropic")) is None
    assert cloud_relay_provider_for(_spec("google")) is None


def test_cloud_relay_env_sets_anthropic_vertex_base_url(monkeypatch):
    monkeypatch.setenv("PORT", "8788")
    from services.relay_spawn import cloud_relay_subprocess_env

    out = cloud_relay_subprocess_env(_spec("anthropic-vertex"), {})
    assert out["ANTHROPIC_VERTEX_BASE_URL"] == "http://127.0.0.1:8788/llm-proxy/vertex/v1"
    # Google base URL must NOT leak onto an Anthropic spawn.
    assert "GOOGLE_VERTEX_BASE_URL" not in out


def test_cloud_relay_env_sets_google_vertex_base_url(monkeypatch):
    monkeypatch.setenv("PORT", "8788")
    from services.relay_spawn import cloud_relay_subprocess_env

    out = cloud_relay_subprocess_env(_spec("google-vertex"), {})
    assert out["GOOGLE_VERTEX_BASE_URL"] == "http://127.0.0.1:8788/llm-proxy/vertex/"
    assert "ANTHROPIC_VERTEX_BASE_URL" not in out


def test_cloud_relay_env_strips_adc_hints(monkeypatch):
    """The whole point of this branch is to keep ADC off the laptop —
    if any of these survive, the local pi could try to walk the ADC
    chain (and either fail loudly or, much worse, succeed using the
    operator's dev creds)."""
    monkeypatch.setenv("PORT", "8788")
    from services.relay_spawn import cloud_relay_subprocess_env

    src = {
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/key.json",
        "PI_TRUST_GCE_METADATA": "1",
        "GCE_METADATA_HOST": "metadata.google.internal",
        "GCE_METADATA_IP": "169.254.169.254",
        "METADATA_SERVER_DETECTION": "1",
    }
    out = cloud_relay_subprocess_env(_spec("anthropic-vertex"), src)
    for stripped in (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "PI_TRUST_GCE_METADATA",
        "GCE_METADATA_HOST",
        "GCE_METADATA_IP",
        "METADATA_SERVER_DETECTION",
    ):
        assert stripped not in out, f"{stripped} must be stripped from cloud-relay env"


def test_cloud_relay_env_keeps_vertex_topology(monkeypatch):
    """We must NOT strip GOOGLE_CLOUD_PROJECT / LOCATION — the SDK
    uses them to build the URL path. The cloud-side passthrough
    re-derives the upstream project from its own env, so what the
    laptop encodes is purely cosmetic. Stripping them would crash the
    SDK with "Vertex AI requires a project ID"."""
    monkeypatch.setenv("PORT", "8788")
    from services.relay_spawn import cloud_relay_subprocess_env

    src = {
        "GOOGLE_CLOUD_PROJECT": "my-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "PI_VERTEX_ANTHROPIC_LOCATION": "global",
    }
    out = cloud_relay_subprocess_env(_spec("anthropic-vertex"), src)
    assert out["GOOGLE_CLOUD_PROJECT"] == "my-project"
    assert out["GOOGLE_CLOUD_LOCATION"] == "us-central1"
    assert out["PI_VERTEX_ANTHROPIC_LOCATION"] == "global"


def test_cloud_relay_env_does_not_mutate_input():
    """Defensive: the helper should return a new dict so callers can
    keep the original env unchanged for fallback paths."""
    from services.relay_spawn import cloud_relay_subprocess_env

    src = {"GOOGLE_APPLICATION_CREDENTIALS": "/tmp/key.json"}
    snapshot = dict(src)
    cloud_relay_subprocess_env(_spec("anthropic-vertex"), src)
    assert src == snapshot


# ── llm_proxy route ────────────────────────────────────────────────────
@pytest.fixture
def app(monkeypatch):
    """Build a FastAPI app with just the llm_proxy router."""
    monkeypatch.setenv("PI_MODE", "desktop")
    monkeypatch.setenv("PI_CLOUD_API_BASE", "https://digi-setu.test")

    import importlib

    import config as _config
    import routes.llm_proxy as _proxy

    importlib.reload(_config)
    importlib.reload(_proxy)

    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(_proxy.router)
    return app


def test_proxy_returns_401_when_signed_out(app, monkeypatch):
    """No cached desktop session → 401 with a sign-in code the SPA
    can render. We do NOT 503 here — sign-out is a normal user state,
    not a server fault."""
    import routes.llm_proxy as _proxy
    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: None)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/vertex/v1/projects/p/locations/global/publishers/anthropic"
        "/models/claude-sonnet-4-6:rawPredict",
        json={"messages": []},
    )
    assert resp.status_code == 401
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "desktop_signin_required"


def test_proxy_strips_incoming_authorization(app, monkeypatch):
    """A malicious / buggy local pi process MUST NOT be able to
    smuggle its own Authorization header through us — only the cached
    desktop bearer reaches the cloud relay."""
    import routes.llm_proxy as _proxy
    captured: dict[str, str] = {}

    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "REAL-CACHED-JWT")

    class _StubResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = "{}"

        def json(self):
            return {"ok": True}

    class _StubClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def post(self, url, content=None, headers=None):
            captured["url"] = url
            captured["headers"] = dict(headers or {})
            return _StubResp()

    monkeypatch.setattr(_proxy.httpx, "AsyncClient", _StubClient)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/vertex/v1/projects/p/locations/global/publishers/anthropic"
        "/models/claude-sonnet-4-6:rawPredict",
        headers={
            "Authorization": "Bearer SMUGGLED-FROM-LOCAL-PROCESS",
            "x-api-key": "smuggled-anthropic-key",
            "x-goog-user-project": "smuggled-project",
        },
        json={"messages": []},
    )
    assert resp.status_code == 200
    sent_auth = captured["headers"].get("authorization", "")
    assert sent_auth == "Bearer REAL-CACHED-JWT", (
        f"expected the cached JWT, not the smuggled one; got {sent_auth!r}"
    )
    lowered = {k.lower() for k in captured["headers"].keys()}
    assert "x-api-key" not in lowered
    assert "x-goog-user-project" not in lowered, (
        "x-goog-user-project must be stripped — caller could otherwise "
        "redirect billing to a project they shouldn't be able to spend on"
    )


def test_proxy_forwards_to_cloud_relay_vertex_path(app, monkeypatch):
    """Verify the URL transform: incoming /llm-proxy/vertex/{rest}
    forwards to ${PI_CLOUD_API_BASE}/v1/relay/vertex/{rest} verbatim,
    no path translation."""
    import routes.llm_proxy as _proxy
    captured: dict[str, str] = {}

    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "real-jwt")

    class _StubResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = "{}"

        def json(self):
            return {"ok": True}

    class _StubClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def post(self, url, content=None, headers=None):
            captured["url"] = url
            return _StubResp()

    monkeypatch.setattr(_proxy.httpx, "AsyncClient", _StubClient)

    client = TestClient(app)
    inbound = (
        "/llm-proxy/vertex/v1/projects/my-proj/locations/global"
        "/publishers/anthropic/models/claude-sonnet-4-6:rawPredict"
    )
    resp = client.post(inbound, json={})
    assert resp.status_code == 200
    expected = (
        "https://digi-setu.test/v1/relay/vertex/v1/projects/my-proj/locations/global"
        "/publishers/anthropic/models/claude-sonnet-4-6:rawPredict"
    )
    assert captured["url"] == expected, (
        f"path passthrough broke; sent {captured['url']!r}"
    )


def test_proxy_health_reports_signin_state(app, monkeypatch):
    import routes.llm_proxy as _proxy

    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "real-jwt")
    client = TestClient(app)
    resp = client.get("/llm-proxy/_health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signed_in"] is True
    assert body["cloud"]
