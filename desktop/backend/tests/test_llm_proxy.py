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
    """Build a FastAPI app with just the llm_proxy router.

    NOTE: we set PI_RELAY_HTTP_BASE (the new HTTP base for /v1/relay/*
    and /v1/typst/* on api.digi-setu.com) — NOT PI_CLOUD_API_BASE
    (apex, used for /api/usage etc.). The proxy forwards to the
    api host because that's where the relay lives. See llm_proxy.py
    docstring for why.
    """
    monkeypatch.setenv("PI_MODE", "desktop")
    monkeypatch.setenv("PI_RELAY_HTTP_BASE", "https://api.digi-setu.test")
    # Also set the WS base so any code path that derives the HTTP
    # base from the WS base stays consistent. The two should ALWAYS
    # point at the same host in tests; production keeps them in sync
    # via _ws_to_http_scheme().
    monkeypatch.setenv("PI_RELAY_BASE", "wss://api.digi-setu.test")

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
    forwards to ${PI_RELAY_HTTP_BASE}/v1/relay/vertex/{rest} verbatim,
    no path translation. The relay host MUST be the api subdomain
    (PI_RELAY_HTTP_BASE), NOT the apex (PI_CLOUD_API_BASE) — the apex
    apex serves SPA HTML and 405s POSTs to unknown paths."""
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
        "https://api.digi-setu.test/v1/relay/vertex/v1/projects/my-proj/locations/global"
        "/publishers/anthropic/models/claude-sonnet-4-6:rawPredict"
    )
    assert captured["url"] == expected, (
        f"path passthrough broke; sent {captured['url']!r}"
    )


def test_typst_search_docs_forwards_to_cloud(app, monkeypatch):
    """Local extension POSTs {package, query} → proxy injects the JWT
    and forwards to ${PI_CLOUD_API_BASE}/v1/typst/search_docs verbatim."""
    import routes.llm_proxy as _proxy
    captured: dict = {}

    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "REAL-JWT")

    class _StubResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = "{}"

        def json(self):
            return {
                "answer": "use canvas + draw.line",
                "cited": ["guides/cetz/canvas.md"],
                "elapsedMs": 1234,
                "model": "gemini-3-flash-preview",
                "usage": {"input": 1000, "output": 100, "cacheRead": 199000, "cacheWrite": 0},
            }

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
            captured["content"] = content
            return _StubResp()

    monkeypatch.setattr(_proxy.httpx, "AsyncClient", _StubClient)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/typst/search_docs",
        headers={"Authorization": "Bearer SMUGGLED"},
        json={"package": "cetz", "query": "draw a curve"},
    )
    assert resp.status_code == 200
    assert captured["url"] == "https://api.digi-setu.test/v1/typst/search_docs"
    assert captured["headers"].get("authorization") == "Bearer REAL-JWT"
    body = resp.json()
    assert body["answer"] == "use canvas + draw.line"
    assert body["cited"] == ["guides/cetz/canvas.md"]


def test_typst_search_docs_401_when_signed_out(app, monkeypatch):
    import routes.llm_proxy as _proxy
    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: None)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/typst/search_docs",
        json={"package": "cetz", "query": "x"},
    )
    assert resp.status_code == 401
    assert resp.json().get("detail", {}).get("code") == "desktop_signin_required"


def test_relay_spawn_sets_typst_remote_url(monkeypatch):
    """relay_spawn must set PI_TYPST_DOCS_REMOTE_URL alongside the
    Vertex base URL so the extension knows to use the server-side
    search_docs path. Both providers should see this env var (gemini
    user might still call search_docs even if their main model is
    Anthropic, etc.)."""
    monkeypatch.setenv("PORT", "8788")
    from services.relay_spawn import cloud_relay_subprocess_env
    from services.models_registry import ModelCost, ModelSpec

    for provider in ("anthropic-vertex", "google-vertex"):
        spec = ModelSpec(
            id="m", name="m", provider=provider, pi_provider=provider,
            family="anthropic" if "anthropic" in provider else "google",
            cost=ModelCost(input=1.0, output=1.0, cache_read=0.0, cache_write=0.0),
            context_window=200_000, reasoning=False, min_plan="free",
            blurb="", hidden=False,
        )
        out = cloud_relay_subprocess_env(spec, {})
        assert (
            out["PI_TYPST_DOCS_REMOTE_URL"]
            == "http://127.0.0.1:8788/llm-proxy/typst/search_docs"
        ), f"missing or wrong PI_TYPST_DOCS_REMOTE_URL for {provider}"


def test_proxy_health_reports_signin_state(app, monkeypatch):
    import routes.llm_proxy as _proxy

    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "real-jwt")
    client = TestClient(app)
    resp = client.get("/llm-proxy/_health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signed_in"] is True
    assert body["cloud"]
    # The health probe must surface the RELAY HTTP base (api host),
    # not the apex (PI_CLOUD_API_BASE). If somebody refactors and
    # accidentally points it at the apex again we want this test to
    # catch the regression — the original bug took ~3 hours to find
    # because the symptom (chat hangs) is way downstream of the
    # misconfigured upstream.
    assert "api.digi-setu.test" in body["cloud"], (
        f"health must report PI_RELAY_HTTP_BASE (api host), got {body['cloud']!r}"
    )


def test_relay_http_base_derives_from_relay_ws_base(monkeypatch):
    """When only PI_RELAY_BASE is set (the canonical knob), the HTTP
    base must auto-derive by swapping the scheme. This is the
    contract that lets a single env var control both transports."""
    monkeypatch.setenv("PI_MODE", "desktop")
    monkeypatch.setenv("PI_RELAY_BASE", "wss://api.example.test")
    # Explicitly leave PI_RELAY_HTTP_BASE unset.
    monkeypatch.delenv("PI_RELAY_HTTP_BASE", raising=False)
    import importlib
    import config as _config
    importlib.reload(_config)
    assert _config.PI_RELAY_HTTP_BASE == "https://api.example.test"


def test_relay_http_base_strips_trailing_slash(monkeypatch):
    """A trailing slash in either env var would double up as
    `//v1/relay/...` upstream and silently 404 / 308 the request.
    Strip on parse so callers don't have to remember."""
    monkeypatch.setenv("PI_MODE", "desktop")
    monkeypatch.setenv("PI_RELAY_HTTP_BASE", "https://api.example.test/")
    import importlib
    import config as _config
    importlib.reload(_config)
    assert _config.PI_RELAY_HTTP_BASE == "https://api.example.test"


# ── _proxy_base_url() — Tauri↔sidecar PORT propagation ─────────────
# These tests pin the contract that broke in production: the Tauri
# shell launches the sidecar with `--port <free>` (a CLI flag, NOT
# the PORT env var), so unless the sidecar entry point exports PORT
# itself, the spawned pi runtime inherits an unset PORT and our
# helper used to silently fall back to `8000`. On a developer machine
# with a stale `uvicorn --reload` on :8000, pi's first prompt got
# `404 {"detail":"Not Found"}` from the WRONG server with no entry in
# our log. The fix lives in two places:
#   1. desktop/sidecar/sidecar_main.py — exports PORT after argparse.
#   2. relay_spawn._proxy_base_url() — raises on the bundled-app
#      branch when PORT is missing rather than returning the 8000
#      default. The dev-loop branch (no PI_DESKTOP_PI_DIR) keeps the
#      legacy default so `uvicorn main:app --port 8000` still works.
def test_proxy_base_url_uses_port_env(monkeypatch):
    """When PORT is set, the proxy base must point at the actual
    bound port. This is the only path the desktop app should ever
    take in production."""
    monkeypatch.setenv("PORT", "19299")
    monkeypatch.delenv("PI_DESKTOP_PI_DIR", raising=False)
    from services.relay_spawn import _proxy_base_url

    assert _proxy_base_url() == "http://127.0.0.1:19299/llm-proxy"


def test_proxy_base_url_raises_in_bundled_app_when_port_missing(monkeypatch):
    """In the bundled desktop app (PI_DESKTOP_PI_DIR is set by the
    Tauri shell), an unset PORT is a wiring bug, not a fallback
    case. Raising surfaces a real error in the sidecar log instead
    of silently routing pi's LLM calls to whatever stale FastAPI
    happens to be on :8000.
    """
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("PI_DESKTOP_PI_DIR", "/Applications/Digi Setu.app/Contents/Resources/pi-runtime/vendor/pi")
    from services.relay_spawn import _proxy_base_url

    with pytest.raises(RuntimeError, match="PORT env var is not exported"):
        _proxy_base_url()


def test_proxy_base_url_falls_back_to_8000_in_dev_loop(monkeypatch):
    """The legacy operator dev loop runs `uvicorn main:app --port 8000`
    directly with no Tauri shell, so PI_DESKTOP_PI_DIR is unset. In
    that case keeping the 8000 default preserves the existing dev UX
    — only the bundled-app branch is opinionated."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("PI_DESKTOP_PI_DIR", raising=False)
    from services.relay_spawn import _proxy_base_url

    assert _proxy_base_url() == "http://127.0.0.1:8000/llm-proxy"


def test_cloud_relay_env_uses_actual_port_not_default_8000(monkeypatch):
    """End-to-end: when the sidecar exports the bound port the spawn
    env hands pi a base URL that points at THIS sidecar (not a
    stale :8000 server). This is the regression test for the
    ``404 {"detail":"Not Found"}`` mystery — see the docstring on
    ``relay_spawn._proxy_base_url`` for the full forensic story."""
    monkeypatch.setenv("PORT", "19299")
    monkeypatch.delenv("PI_DESKTOP_PI_DIR", raising=False)
    from services.relay_spawn import cloud_relay_subprocess_env

    out = cloud_relay_subprocess_env(_spec("anthropic-vertex"), {})
    assert out["ANTHROPIC_VERTEX_BASE_URL"] == "http://127.0.0.1:19299/llm-proxy/vertex/v1"
    assert out["PI_TYPST_DOCS_REMOTE_URL"] == "http://127.0.0.1:19299/llm-proxy/typst/search_docs"


# ── streaming SSE + gzip handling ──────────────────────────────────
# The cloud relay's ``vertex_passthrough`` propagates upstream bytes
# verbatim via httpx ``aiter_raw`` but only echoes ``Content-Type``
# downstream — so gzipped SSE arrives at the desktop with NO
# ``Content-Encoding: gzip`` header. Pi's SDK can't auto-decompress
# without the header, parses the gzip magic bytes as garbage SSE
# frames, and records 0 text + 0 tokens. The user sees their prompt
# vanish into an empty assistant turn.
#
# We can't patch the cloud relay from a desktop unit test, so the
# desktop-side fix sniffs the first chunk; if it starts with
# ``1f 8b 08`` (gzip magic) we decompress on the way through and
# emit plain-bytes SSE downstream — exactly what pi's SDK expects.
def _make_streaming_response_stub(body_bytes: bytes, content_encoding: str | None,
                                   content_type: str = "text/event-stream"):
    """Build httpx-shape stubs the streaming branch expects.

    Returns (StubClient, captured_state) — tests assert on captured
    state to verify auth + decompression + header propagation.
    """
    captured: dict = {}

    class _Headers(dict):
        def get(self, key, default=None):
            return super().get(key.lower(), default)

    headers = _Headers()
    headers["content-type"] = content_type
    if content_encoding:
        headers["content-encoding"] = content_encoding

    class _StubResp:
        status_code = 200

        def __init__(self):
            self.headers = headers

        async def aiter_raw(self):
            # Mimic chunked SSE-style delivery so the proxy's gzip
            # detector has to commit on chunk #1 like real life.
            for offset in range(0, len(body_bytes), 64):
                yield body_bytes[offset : offset + 64]

        async def aclose(self):
            captured["resp_closed"] = True

    class _StubClient:
        def __init__(self, *args, **kwargs):
            pass

        def build_request(self, method, url, content=None, headers=None):
            captured["method"] = method
            captured["url"] = url
            captured["body"] = content
            captured["headers"] = dict(headers or {})
            return ("REQ", method, url)

        async def send(self, req, stream=True):
            captured["stream_flag"] = stream
            return _StubResp()

        async def aclose(self):
            captured["client_closed"] = True

    return _StubClient, captured


def test_streaming_proxy_decompresses_gzip_when_upstream_strips_header(app, monkeypatch):
    """Reproduces the silent-empty-response bug: cloud relay forwards
    gzipped Vertex SSE but drops Content-Encoding. The desktop proxy
    MUST detect the gzip magic bytes and decompress before pi sees
    the body. Without the fix, pi receives gzipped junk labeled
    text/event-stream and records 0 tokens / empty content.
    """
    import routes.llm_proxy as _proxy
    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "REAL-JWT")

    plain_sse = (
        b"event: message_start\n"
        b"data: {\"type\":\"message_start\"}\n\n"
        b"event: content_block_delta\n"
        b"data: {\"type\":\"content_block_delta\",\"delta\":{\"text\":\"Hi\"}}\n\n"
    )
    import gzip
    gzipped = gzip.compress(plain_sse)
    StubClient, captured = _make_streaming_response_stub(
        body_bytes=gzipped,
        content_encoding=None,  # cloud relay's bug: header stripped
    )
    monkeypatch.setattr(_proxy.httpx, "AsyncClient", StubClient)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/vertex/v1/projects/p/locations/global/publishers/anthropic"
        "/models/claude-sonnet-4-6:streamRawPredict",
        json={"stream": True, "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    # Body MUST be the decompressed SSE stream (pi can parse this).
    assert resp.content == plain_sse, (
        "proxy did not decompress gzip-on-the-wire body — pi's SDK "
        "would record empty content. See routes/llm_proxy.py docstring "
        "for the full forensic story."
    )
    # Since we decompressed, we MUST NOT advertise gzip downstream.
    assert "content-encoding" not in {k.lower() for k in resp.headers.keys()}
    assert resp.headers.get("content-type", "").startswith("text/event-stream")


def test_streaming_proxy_propagates_upstream_content_encoding_when_present(app, monkeypatch):
    """Once the cloud relay propagates Content-Encoding (transparent
    proxy mode), the desktop proxy should forward the header AND
    yield the body verbatim — pi's SDK will auto-decompress."""
    import routes.llm_proxy as _proxy
    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "REAL-JWT")

    import gzip
    plain_sse = b"event: ping\ndata: {\"type\":\"ping\"}\n\n"
    gzipped = gzip.compress(plain_sse)
    StubClient, captured = _make_streaming_response_stub(
        body_bytes=gzipped,
        content_encoding="gzip",  # cloud relay propagates header
    )
    monkeypatch.setattr(_proxy.httpx, "AsyncClient", StubClient)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/vertex/v1/projects/p/locations/global/publishers/anthropic"
        "/models/claude-sonnet-4-6:streamRawPredict",
        json={"stream": True, "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    # When upstream advertised gzip, we forwarded raw bytes + the
    # encoding header. TestClient + httpx handle the decompress for
    # us; we just check the header reached the client.
    assert resp.headers.get("content-encoding") == "gzip"


def test_streaming_proxy_passes_plain_body_through(app, monkeypatch):
    """Defensive: when upstream sends plain (non-gzipped) SSE, the
    sniffer must NOT corrupt it — neither decompress nor add a stale
    Content-Encoding header."""
    import routes.llm_proxy as _proxy
    monkeypatch.setattr(_proxy, "_fresh_bearer", lambda: "REAL-JWT")

    plain_sse = b"event: hello\ndata: {\"x\":1}\n\n"
    StubClient, captured = _make_streaming_response_stub(
        body_bytes=plain_sse,
        content_encoding=None,
    )
    monkeypatch.setattr(_proxy.httpx, "AsyncClient", StubClient)

    client = TestClient(app)
    resp = client.post(
        "/llm-proxy/vertex/v1/projects/p/locations/global/publishers/anthropic"
        "/models/claude-sonnet-4-6:streamRawPredict",
        json={"stream": True, "messages": []},
    )
    assert resp.status_code == 200
    assert resp.content == plain_sse
    assert "content-encoding" not in {k.lower() for k in resp.headers.keys()}
