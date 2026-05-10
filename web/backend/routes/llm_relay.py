"""
LLM relay — cloud edge for the desktop "local pi, cloud auth" path.

Why this exists
---------------
Two product constraints collide:

  1. Files the AI creates on the user's behalf must persist in the
     user's actual chosen folder, even after the desktop app restarts.
     That can only happen if `pi-coding-agent` runs **on the laptop**,
     so file ops touch the local filesystem directly.

  2. Vertex AI calls require Google Application Default Credentials.
     We absolutely cannot ship those credentials to user laptops — they
     unlock our entire GCP project, including data we host for OTHER
     users. The credential perimeter must stay on the VM.

This module is the bridge. The desktop sidecar runs pi locally, but
configures it to send Anthropic / Vertex API traffic to these endpoints
(via a small JWT-injecting localhost forwarder — see
``desktop/backend/routes/llm_proxy.py``). We verify the user's Clerk
JWT, charge their plan, and forward to the real Vertex endpoint with
ADC injected.

Why not the existing /v1/ws/desktop-relay
-----------------------------------------
That WebSocket carries entire chat sessions: pi runs on the VM and
streams tool calls + results over the WS. File operations therefore
target the VM's container disk and disappear when the container
recycles. The WS path stays as a fallback (e.g. for users on locked-
down corporate laptops where running pi locally is blocked) but the
default for desktop-with-cloud-auth users is now this HTTP relay.

Endpoints
---------
- POST /v1/relay/anthropic/v1/messages
    Anthropic Messages API surface. The desktop pi runs with the
    standard ``anthropic`` provider pointed at this URL; we translate
    to Vertex's ``:rawPredict`` shape (which is itself Anthropic-
    compatible — Vertex just adds an ``anthropic_version`` field and
    moves the model id to the URL).

- POST /v1/relay/google/v1beta/models/{model}:streamGenerateContent
- POST /v1/relay/google/v1beta/models/{model}:generateContent
    Google Gen AI surface. Forwarded to the equivalent Vertex publisher
    endpoint with ADC injected. Body is forwarded verbatim — the schema
    is the same.

Defenses (applied in order)
---------------------------
  1. ``verify_relay_jwt``        — 401 on missing / invalid bearer.
  2. ``consume_user_quota``      — 429 on RL bucket overflow.
  3. ``assert_model_allowed_for_plan`` — 403 when the plan is too low.
  4. ``check_relay_budget``      — 402 when monthly credit is exhausted.
  5. forward to Vertex with ADC.
  6. on stream end → ``CreditLedger.note_cost`` deducts the actual cost.

Streaming
---------
Anthropic streaming uses Server-Sent Events; Vertex's ``:streamRawPredict``
emits the same SSE byte-for-byte. We use ``httpx.AsyncClient.stream`` and
pass chunks through ``StreamingResponse``. To bill accurately we tee the
``message_delta`` SSE event (which carries final ``usage``) into a
post-hook before the connection closes.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from typing import Any, AsyncIterator, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from services.auth import RelayPrincipal, verify_relay_jwt
from services.billing import (
    CreditLedger,
    check_relay_budget,
    estimate_prompt_cost,
)
from services.models_registry import (
    DEFAULT_MODEL_ID,
    assert_model_allowed_for_plan,
    get_model,
)
from services.rate_limit import consume_user_quota


router = APIRouter(prefix="/v1/relay", tags=["llm-relay"])


# ── ADC token broker (shared instance per process) ───────────────────
#
# We deliberately mirror services/egress_proxy.py's pattern (one
# `google.auth.default()` call cached at module load, refreshed in-place
# when the cached token nears expiry). The egress proxy already has its
# own broker but we don't want to depend on it being initialised — the
# relay needs to work even on backends where the egress proxy is
# disabled (e.g. local dev with PI_DISABLE_EGRESS_PROXY=1).
_CREDS = None  # type: ignore[var-annotated]
_CREDS_LOCK = threading.Lock()
_CREDS_INIT_DONE = False


def _ensure_creds() -> Optional[Any]:
    """Lazy-init google.auth ADC. Returns the credentials object or None.

    Init is one-shot (`_CREDS_INIT_DONE`) so we don't re-attempt the
    expensive `google.auth.default()` on every relay call when ADC is
    plain unavailable (dev laptops without `gcloud auth …` set up).
    """
    global _CREDS, _CREDS_INIT_DONE
    if _CREDS_INIT_DONE:
        return _CREDS
    with _CREDS_LOCK:
        if _CREDS_INIT_DONE:
            return _CREDS
        try:
            import google.auth  # type: ignore

            creds, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            _CREDS = creds
        except Exception as exc:
            # Loud log but no crash — the relay simply 503s every call
            # until ADC is configured.
            print(
                f"[llm_relay] ADC unavailable; relay will 503 every call "
                f"until configured: {exc}",
                file=sys.stderr,
            )
            _CREDS = None
        _CREDS_INIT_DONE = True
        return _CREDS


def _adc_token() -> Optional[str]:
    """Return a fresh Vertex bearer token, or None if ADC is unavailable."""
    creds = _ensure_creds()
    if creds is None:
        return None
    with _CREDS_LOCK:
        try:
            from google.auth.transport.requests import Request as GAuthRequest  # type: ignore

            if not getattr(creds, "valid", False):
                creds.refresh(GAuthRequest())
            return creds.token
        except Exception as exc:
            print(f"[llm_relay] ADC token refresh failed: {exc}", file=sys.stderr)
            return None


# ── Vertex topology helpers ──────────────────────────────────────────
def _gcp_project() -> str:
    """Resolve the Vertex project id from the same env var pi uses."""
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or ""
    )


def _vertex_host(location: str) -> str:
    """Vertex's regional split: ``global`` is a separate hostname; every
    other location uses the ``{loc}-aiplatform.googleapis.com`` form."""
    return (
        "aiplatform.googleapis.com"
        if location == "global"
        else f"{location}-aiplatform.googleapis.com"
    )


def _resolve_anthropic_location(model_id: str) -> str:
    """Region for an Anthropic-on-Vertex model id.

    Today Anthropic Vertex models live in `global` only; left as a
    helper so when Anthropic ships regional capacity we don't have to
    chase the change through three call sites.
    """
    return os.environ.get("PI_VERTEX_ANTHROPIC_LOCATION") or "global"


def _resolve_google_location(model_id: str) -> str:
    """Region for a Google Gen AI model. Defaults to the env-var value
    set in stack.env (`global` in production)."""
    return os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"


# ── Streaming forwarder ──────────────────────────────────────────────
#
# httpx + FastAPI's StreamingResponse interop note: we must keep the
# httpx client AND the response open for the entire generator
# lifetime. The cleanest way is to enter the async-context-manager
# inside the generator function itself.
async def _stream_upstream(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    on_chunk: Optional[Any] = None,
) -> tuple[int, dict[str, str], AsyncIterator[bytes]]:
    """Open an httpx streaming request and return (status, headers, gen).

    The generator yields raw upstream bytes. `on_chunk(bytes)` is called
    for every chunk before it's emitted downstream — used by the cost
    capture path to peek at SSE frames.
    """
    # 5-min total timeout: Anthropic and Gemini both occasionally hang
    # for tens of seconds on the first byte of a long reasoning trace.
    # Connect timeout is short so a network blip surfaces fast.
    timeout = httpx.Timeout(connect=15.0, read=300.0, write=60.0, pool=15.0)
    client = httpx.AsyncClient(timeout=timeout)
    req = client.build_request(method, url, headers=headers, content=body)
    response = await client.send(req, stream=True)

    async def _gen() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_raw():
                if chunk and on_chunk is not None:
                    try:
                        on_chunk(chunk)
                    except Exception as exc:
                        # Tap failures must NOT abort the user's stream.
                        print(
                            f"[llm_relay] cost-tap raised: {exc}", file=sys.stderr
                        )
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return response.status_code, dict(response.headers), _gen()


# ── SSE / JSON usage parsers (cost capture) ──────────────────────────
def _parse_anthropic_usage_from_sse(buffer: bytes) -> Optional[dict[str, int]]:
    """Pull the final usage payload out of a buffered Anthropic SSE stream.

    Anthropic emits ``event: message_delta`` with a ``usage`` field at the
    end of every response (input_tokens are repeated for convenience;
    output_tokens reflects the cumulative count). We scan from the END
    because the message_delta is always the last frame — cheaper than
    parsing every event when we only need one.
    """
    if not buffer:
        return None
    text = buffer.decode("utf-8", errors="replace")
    # SSE frames are `data: {...}\n\n`. Scan latest-first.
    for frame in reversed(text.split("\n\n")):
        if "message_delta" not in frame and "message_stop" not in frame:
            continue
        for line in frame.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                evt = json.loads(payload)
            except (TypeError, ValueError):
                continue
            usage = evt.get("usage")
            if isinstance(usage, dict):
                return {
                    "input": int(usage.get("input_tokens") or 0),
                    "output": int(usage.get("output_tokens") or 0),
                    "cacheRead": int(usage.get("cache_read_input_tokens") or 0),
                    "cacheWrite": int(usage.get("cache_creation_input_tokens") or 0),
                }
    return None


def _parse_anthropic_usage_from_json(payload: dict[str, Any]) -> Optional[dict[str, int]]:
    """Non-streaming Anthropic response: usage is a top-level field."""
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    return {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cacheRead": int(usage.get("cache_read_input_tokens") or 0),
        "cacheWrite": int(usage.get("cache_creation_input_tokens") or 0),
    }


def _parse_gemini_usage_from_sse(buffer: bytes) -> Optional[dict[str, int]]:
    """Gemini's streamGenerateContent emits ``usageMetadata`` on the
    final chunk (sometimes inline JSON, sometimes SSE — both pop out of
    the same parser)."""
    if not buffer:
        return None
    text = buffer.decode("utf-8", errors="replace")
    # Gemini's stream is "JSON-array" style (one big array of objects)
    # OR "SSE" style depending on the request. Try SSE first.
    candidates: list[str] = []
    for frame in text.split("\n\n"):
        for line in frame.splitlines():
            if line.startswith("data:"):
                candidates.append(line[len("data:"):].strip())
    if not candidates:
        # Try JSON-array form: split on `,\n` between objects.
        candidates = [c for c in text.split("\n") if c.strip().startswith("{")]
    for payload in reversed(candidates):
        try:
            evt = json.loads(payload)
        except (TypeError, ValueError):
            continue
        meta = evt.get("usageMetadata")
        if isinstance(meta, dict) and meta:
            return {
                "input": int(meta.get("promptTokenCount") or 0),
                "output": int(meta.get("candidatesTokenCount") or 0),
                "cacheRead": int(meta.get("cachedContentTokenCount") or 0),
                "cacheWrite": 0,
            }
    return None


def _parse_gemini_usage_from_json(payload: dict[str, Any]) -> Optional[dict[str, int]]:
    meta = payload.get("usageMetadata")
    if not isinstance(meta, dict):
        return None
    return {
        "input": int(meta.get("promptTokenCount") or 0),
        "output": int(meta.get("candidatesTokenCount") or 0),
        "cacheRead": int(meta.get("cachedContentTokenCount") or 0),
        "cacheWrite": 0,
    }


def _record_cost(
    *,
    user_id: str,
    model_id: str,
    usage: Optional[dict[str, int]],
    wall_seconds: float,
) -> None:
    """Convert a usage dict into a CreditLedger event. No-op when usage is
    missing — better to under-bill a single call than crash the relay."""
    if not usage:
        return
    try:
        bd = estimate_prompt_cost(usage, model_id=model_id, wall_seconds=wall_seconds)
        CreditLedger.instance().note_cost(
            user_id,
            bd.total_usd,
            source="relay",
            model=model_id,
            usage=usage,
            breakdown={
                "llm_usd": round(bd.llm_usd, 6),
                "vm_usd": round(bd.vm_usd, 6),
                "margin_usd": round(bd.margin_usd, 6),
            },
        )
    except Exception as exc:
        print(f"[llm_relay] note_cost failed (user={user_id}): {exc}", file=sys.stderr)


# ── Anthropic forwarder ──────────────────────────────────────────────
@router.post("/anthropic/v1/messages")
async def anthropic_messages(
    request: Request,
    principal: RelayPrincipal = Depends(verify_relay_jwt),
):
    """Anthropic Messages API forwarder.

    Accepts the standard request body:
        {"model": "claude-sonnet-4-6", "messages": [...], "stream": true|false, ...}

    On the wire to Vertex we strip ``model`` (it goes in the URL),
    add ``anthropic_version: vertex-2023-10-16``, and route to
    ``:streamRawPredict`` or ``:rawPredict`` depending on ``stream``.
    """
    consume_user_quota(principal.user_id)

    raw = await request.body()
    try:
        payload = json.loads(raw or b"{}")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")

    model_id = str(payload.get("model") or DEFAULT_MODEL_ID)
    streaming = bool(payload.get("stream"))

    assert_model_allowed_for_plan(model_id, principal.plan)
    check_relay_budget(principal.user_id, principal.plan)

    project = _gcp_project()
    if not project:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "relay_misconfigured",
                "message": "GOOGLE_CLOUD_PROJECT unset on the relay",
            },
        )

    token = _adc_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "adc_unavailable",
                "message": "Vertex ADC unavailable — see backend logs",
            },
        )

    # Translate body: drop the user-side `model` field (it's in the URL
    # for rawPredict), add `anthropic_version`. Everything else passes
    # through unchanged so future Anthropic features (system prompt,
    # tools, cache_control) Just Work without code edits here.
    body_for_vertex = {k: v for k, v in payload.items() if k != "model"}
    body_for_vertex.setdefault("anthropic_version", "vertex-2023-10-16")
    # Vertex's rawPredict doesn't accept the streaming `stream` toggle
    # in the body (it's encoded in the URL suffix).
    body_for_vertex.pop("stream", None)
    body_bytes = json.dumps(body_for_vertex).encode("utf-8")

    location = _resolve_anthropic_location(model_id)
    host = _vertex_host(location)
    suffix = ":streamRawPredict" if streaming else ":rawPredict"
    upstream_url = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/publishers/anthropic/models/{model_id}{suffix}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project,
    }

    started = asyncio.get_event_loop().time()
    spec = get_model(model_id)
    spec_id = spec.id if spec else model_id

    if streaming:
        sse_buffer = bytearray()

        def _capture(chunk: bytes) -> None:
            # 256 KiB of SSE backlog is plenty for the message_delta
            # tail (it sits at the END of the stream); we only buffer
            # the trailing window to keep memory bounded for very long
            # responses. Drop the head when we exceed.
            if len(sse_buffer) > 256 * 1024:
                # Keep the LAST 128 KiB — the usage frame is always
                # within the final few bytes.
                del sse_buffer[: len(sse_buffer) - 128 * 1024]
            sse_buffer.extend(chunk)

        try:
            up_status, up_headers, gen = await _stream_upstream(
                method="POST",
                url=upstream_url,
                headers=headers,
                body=body_bytes,
                on_chunk=_capture,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "upstream_unreachable", "message": str(exc)},
            )

        async def _wrapped() -> AsyncIterator[bytes]:
            try:
                async for chunk in gen:
                    yield chunk
            finally:
                wall = max(0.0, asyncio.get_event_loop().time() - started)
                usage = _parse_anthropic_usage_from_sse(bytes(sse_buffer))
                _record_cost(
                    user_id=principal.user_id,
                    model_id=spec_id,
                    usage=usage,
                    wall_seconds=wall,
                )

        # Forward the upstream Content-Type so the SDK on the client
        # side parses SSE correctly.
        media_type = up_headers.get("content-type") or "text/event-stream"
        return StreamingResponse(
            _wrapped(), status_code=up_status, media_type=media_type,
        )

    # Non-streaming: small bodies, easy to capture in one shot.
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(upstream_url, content=body_bytes, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_unreachable", "message": str(exc)},
        )

    if resp.status_code == 200:
        try:
            usage = _parse_anthropic_usage_from_json(resp.json())
        except Exception:
            usage = None
        wall = max(0.0, asyncio.get_event_loop().time() - started)
        _record_cost(
            user_id=principal.user_id,
            model_id=spec_id,
            usage=usage,
            wall_seconds=wall,
        )

    return JSONResponse(
        content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text},
        status_code=resp.status_code,
    )


# ── Google Gen AI forwarder ──────────────────────────────────────────
async def _forward_gemini(
    *,
    request: Request,
    principal: RelayPrincipal,
    model: str,
    streaming: bool,
):
    """Shared core for ``:generateContent`` + ``:streamGenerateContent``."""
    consume_user_quota(principal.user_id)
    assert_model_allowed_for_plan(model, principal.plan)
    check_relay_budget(principal.user_id, principal.plan)

    project = _gcp_project()
    if not project:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "relay_misconfigured",
                "message": "GOOGLE_CLOUD_PROJECT unset on the relay",
            },
        )

    token = _adc_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "adc_unavailable",
                "message": "Vertex ADC unavailable — see backend logs",
            },
        )

    body = await request.body()

    location = _resolve_google_location(model)
    host = _vertex_host(location)
    suffix = ":streamGenerateContent" if streaming else ":generateContent"
    qs = "?alt=sse" if streaming else ""
    upstream_url = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/publishers/google/models/{model}{suffix}{qs}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project,
    }

    started = asyncio.get_event_loop().time()

    if streaming:
        sse_buffer = bytearray()

        def _capture(chunk: bytes) -> None:
            if len(sse_buffer) > 256 * 1024:
                del sse_buffer[: len(sse_buffer) - 128 * 1024]
            sse_buffer.extend(chunk)

        try:
            up_status, up_headers, gen = await _stream_upstream(
                method="POST",
                url=upstream_url,
                headers=headers,
                body=body,
                on_chunk=_capture,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "upstream_unreachable", "message": str(exc)},
            )

        async def _wrapped() -> AsyncIterator[bytes]:
            try:
                async for chunk in gen:
                    yield chunk
            finally:
                wall = max(0.0, asyncio.get_event_loop().time() - started)
                usage = _parse_gemini_usage_from_sse(bytes(sse_buffer))
                _record_cost(
                    user_id=principal.user_id,
                    model_id=model,
                    usage=usage,
                    wall_seconds=wall,
                )

        media_type = up_headers.get("content-type") or "text/event-stream"
        return StreamingResponse(
            _wrapped(), status_code=up_status, media_type=media_type,
        )

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(upstream_url, content=body, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_unreachable", "message": str(exc)},
        )

    if resp.status_code == 200:
        try:
            usage = _parse_gemini_usage_from_json(resp.json())
        except Exception:
            usage = None
        wall = max(0.0, asyncio.get_event_loop().time() - started)
        _record_cost(
            user_id=principal.user_id,
            model_id=model,
            usage=usage,
            wall_seconds=wall,
        )

    return JSONResponse(
        content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text},
        status_code=resp.status_code,
    )


@router.post("/google/v1beta/models/{model}:generateContent")
async def gemini_generate(
    model: str,
    request: Request,
    principal: RelayPrincipal = Depends(verify_relay_jwt),
):
    return await _forward_gemini(
        request=request, principal=principal, model=model, streaming=False
    )


@router.post("/google/v1beta/models/{model}:streamGenerateContent")
async def gemini_stream(
    model: str,
    request: Request,
    principal: RelayPrincipal = Depends(verify_relay_jwt),
):
    return await _forward_gemini(
        request=request, principal=principal, model=model, streaming=True
    )


# ── Vertex passthrough (used by desktop local-pi-via-relay) ──────────
#
# The desktop uses pi-coding-agent's existing `anthropic-vertex` /
# `google-vertex` providers, which call the Vertex Prediction Service
# at hard-coded URLs of the form:
#
#   https://{loc}-aiplatform.googleapis.com/v1/projects/{p}/locations/{l}/publishers/{pub}/models/{m}:rawPredict
#   https://{loc}-aiplatform.googleapis.com/v1/projects/{p}/locations/{l}/publishers/{pub}/models/{m}:streamRawPredict
#   https://{loc}-aiplatform.googleapis.com/v1/projects/{p}/locations/{l}/publishers/{pub}/models/{m}:streamGenerateContent
#
# The local pi has no ADC; we redirect it via env-var (PI_VERTEX_RELAY_URL,
# wired in patches/) so the SDK posts to:
#
#   ${PI_VERTEX_RELAY_URL}/v1/projects/{p}/locations/{l}/publishers/{pub}/models/{m}:rawPredict
#
# which lands HERE. We keep the path suffix verbatim, swap the bearer
# for ADC, and forward to real Vertex. No body translation — the
# request body that pi sends is already in the exact shape Vertex
# expects (because the Anthropic-on-Vertex / Google-on-Vertex SDKs
# build it that way).
#
# Why a separate endpoint group from /anthropic/v1/messages: those
# endpoints translate from the ConsumerAPI shape to the Vertex shape;
# this one is pure passthrough. The desktop uses passthrough because
# it lets us patch a single env var instead of registering new
# model entries in pi's catalogue.

# Allowed publisher prefixes — defense-in-depth so a relay client
# can't ask us to forward to publishers we haven't priced.
_ALLOWED_PUBLISHERS = frozenset({"anthropic", "google"})


def _parse_vertex_passthrough_path(rest: str) -> tuple[str, str, str, str, str]:
    """Decompose ``v1/projects/{p}/locations/{l}/publishers/{pub}/models/{m}:rawPredict``
    into ``(project, location, publisher, model, action)``. Raises 400
    when the path doesn't match the well-known shape — the relay must
    NEVER forward arbitrary request paths to Vertex (an attacker could
    otherwise hit `:export`, `:tune`, etc. and run up our bill on
    operations we didn't price)."""
    parts = rest.strip("/").split("/")
    # Expected: ['v1', 'projects', '{p}', 'locations', '{l}',
    #            'publishers', '{pub}', 'models', '{model}:action']
    if len(parts) != 9 or parts[0] != "v1" or parts[1] != "projects" \
            or parts[3] != "locations" or parts[5] != "publishers" \
            or parts[7] != "models":
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_relay_path", "message": "unexpected Vertex path shape"},
        )
    project, location, publisher = parts[2], parts[4], parts[6]
    model_action = parts[8]
    if ":" not in model_action:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_relay_path", "message": "missing :action suffix"},
        )
    model, _, action = model_action.partition(":")
    if not model or not action:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_relay_path", "message": "empty model or action"},
        )
    return project, location, publisher, model, action


# Vertex actions we forward. Anything else (e.g. :export, :tune,
# :batchPredict) is rejected — those have different billing and aren't
# part of the desktop chat surface.
_ALLOWED_VERTEX_ACTIONS = frozenset({
    "rawPredict",
    "streamRawPredict",
    "generateContent",
    "streamGenerateContent",
})


@router.post("/vertex/{rest:path}")
async def vertex_passthrough(
    rest: str,
    request: Request,
    principal: RelayPrincipal = Depends(verify_relay_jwt),
):
    """Vertex-shape passthrough for the desktop local-pi path.

    Treats every request as streaming when the action ends in
    ``streamRawPredict`` / ``streamGenerateContent``; otherwise falls
    back to one-shot. The defenses (auth, rate-limit, plan, budget)
    fire identically to the consumer-API endpoints — we only differ
    in URL shape + lack of body translation.
    """
    consume_user_quota(principal.user_id)

    project, location, publisher, model_id, action = _parse_vertex_passthrough_path(rest)

    if publisher not in _ALLOWED_PUBLISHERS:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "publisher_not_allowed",
                "publisher": publisher,
                "message": (
                    f"Publisher {publisher!r} is not relayed. Allowed: "
                    f"{sorted(_ALLOWED_PUBLISHERS)}"
                ),
            },
        )
    if action not in _ALLOWED_VERTEX_ACTIONS:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "action_not_allowed",
                "action": action,
                "message": (
                    f"Action :{action} is not relayed. Allowed: "
                    f"{sorted(_ALLOWED_VERTEX_ACTIONS)}"
                ),
            },
        )

    assert_model_allowed_for_plan(model_id, principal.plan)
    check_relay_budget(principal.user_id, principal.plan)

    streaming = action.startswith("stream")

    # Force the relay's own configured project/location regardless of
    # what the caller put in the URL. We don't want a misconfigured
    # client (or a malicious one) charging requests to the wrong GCP
    # project. The SDK on the desktop side will produce whatever URL
    # we configure via env var, but the URL parts upstream MUST come
    # from us, not from the request.
    own_project = _gcp_project()
    if not own_project:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "relay_misconfigured",
                "message": "GOOGLE_CLOUD_PROJECT unset on the relay",
            },
        )
    own_location = (
        _resolve_anthropic_location(model_id) if publisher == "anthropic"
        else _resolve_google_location(model_id)
    )

    token = _adc_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "adc_unavailable",
                "message": "Vertex ADC unavailable — see backend logs",
            },
        )

    host = _vertex_host(own_location)
    upstream_url = (
        f"https://{host}/v1/projects/{own_project}/locations/{own_location}"
        f"/publishers/{publisher}/models/{model_id}:{action}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": request.headers.get("content-type") or "application/json",
        "x-goog-user-project": own_project,
    }

    body = await request.body()
    started = asyncio.get_event_loop().time()

    if streaming:
        sse_buffer = bytearray()

        def _capture(chunk: bytes) -> None:
            if len(sse_buffer) > 256 * 1024:
                del sse_buffer[: len(sse_buffer) - 128 * 1024]
            sse_buffer.extend(chunk)

        try:
            up_status, up_headers, gen = await _stream_upstream(
                method="POST",
                url=upstream_url,
                headers=headers,
                body=body,
                on_chunk=_capture,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "upstream_unreachable", "message": str(exc)},
            )

        async def _wrapped() -> AsyncIterator[bytes]:
            try:
                async for chunk in gen:
                    yield chunk
            finally:
                wall = max(0.0, asyncio.get_event_loop().time() - started)
                # Anthropic-Vertex emits Anthropic-shape SSE, even via
                # :streamRawPredict. Gemini emits its own shape. Pick
                # the right parser by publisher.
                if publisher == "anthropic":
                    usage = _parse_anthropic_usage_from_sse(bytes(sse_buffer))
                else:
                    usage = _parse_gemini_usage_from_sse(bytes(sse_buffer))
                _record_cost(
                    user_id=principal.user_id,
                    model_id=model_id,
                    usage=usage,
                    wall_seconds=wall,
                )

        media_type = up_headers.get("content-type") or "text/event-stream"
        return StreamingResponse(
            _wrapped(), status_code=up_status, media_type=media_type,
        )

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(upstream_url, content=body, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_unreachable", "message": str(exc)},
        )

    if resp.status_code == 200:
        try:
            payload = resp.json()
            if publisher == "anthropic":
                usage = _parse_anthropic_usage_from_json(payload)
            else:
                usage = _parse_gemini_usage_from_json(payload)
        except Exception:
            usage = None
        wall = max(0.0, asyncio.get_event_loop().time() - started)
        _record_cost(
            user_id=principal.user_id,
            model_id=model_id,
            usage=usage,
            wall_seconds=wall,
        )

    return JSONResponse(
        content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text},
        status_code=resp.status_code,
    )


# ── Health ───────────────────────────────────────────────────────────
@router.get("/_health")
def relay_health():
    """Public probe — returns {"adc": true|false} so operators can check
    whether the relay can talk to Vertex without standing up a full call.
    No auth required; this is a liveness/readiness signal, not a secret."""
    creds = _ensure_creds()
    return {
        "adc": creds is not None,
        "project": _gcp_project() or None,
    }
