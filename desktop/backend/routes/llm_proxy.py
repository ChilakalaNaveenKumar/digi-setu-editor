"""
LLM localhost proxy — JWT-injecting forwarder for locally-spawned pi.

Why this exists
---------------
The desktop app wants two things at once that look contradictory:

  - **Files persist on the user's local disk.** When the AI writes a
    PDF or PNG it has to land in the user's chosen folder; that means
    `pi-coding-agent` runs ON THE LAPTOP, not on a cloud VM.

  - **GCP Application Default Credentials must NEVER leak to laptops.**
    A single ADC token unlocks our entire Google Cloud project,
    including data we host for OTHER users. The credential perimeter
    must stay on the VM.

This module reconciles them. Pi runs locally with its EXISTING
``anthropic-vertex`` / ``google-vertex`` providers — no model-registry
changes — and just has its SDK base URL pointed at this localhost
proxy via ``ANTHROPIC_VERTEX_BASE_URL`` / ``GOOGLE_VERTEX_BASE_URL``
(see ``services/relay_spawn.py``). The proxy:

  1. Reads the cached Clerk session (refreshed transparently by
     ``routes.desktop_auth.get_cached_desktop_session``).
  2. Strips any client-supplied auth — the local pi has no ADC token,
     and even if it did, we never want to forward it.
  3. Replaces auth with ``Bearer <jwt>``.
  4. Forwards verbatim to ``${PI_RELAY_HTTP_BASE}/v1/relay/vertex/...``,
     where the cloud relay validates the JWT, enforces plan + budget
     gates, swaps in ADC, and proxies on to Vertex.

Body shape is whatever the Vertex SDK produced — we do not interpret
it. The cloud-side ``vertex_passthrough`` endpoint matches.

Why PI_RELAY_HTTP_BASE (api subdomain), not PI_CLOUD_API_BASE (apex)
-------------------------------------------------------------------
The relay endpoints (``/v1/relay/*``, ``/v1/typst/*``) are mounted on
``api.digi-setu.com`` ONLY. The apex ``digi-setu.com`` returns 404 /
SPA HTML for unknown paths (see deploy/caddy/Caddyfile — the apex
handler only catches ``/api/*``, ``/ws/*``, ``/healthz``,
``/downloads/*`` plus the static SPA fallback). Forwarding to the
apex makes pi POST against a static-file route that 405s, which on
the user side looks like "chat hangs forever on streaming…" because
pi retries the failed bearer-less response in a loop. The apex base
``PI_CLOUD_API_BASE`` is reserved for billing / usage REST endpoints
mounted as ``/api/*`` on the apex (see routes/usage.py).

The proxy is bound to 127.0.0.1 only (sidecar's bind address — see
``desktop/backend/main.py``). A remote attacker cannot reach this
endpoint; a local attacker process can, but it would still need to
hit the cloud relay's defenses to actually spend money.

Endpoints
---------
- POST /llm-proxy/vertex/{rest:path}    Catch-all Vertex passthrough.
- POST /llm-proxy/typst/search_docs     Server-side typst doc search
                                         (corpus lives on the VM, not
                                         on the laptop — see
                                         web/backend/routes/typst_docs.py).
- GET  /llm-proxy/_health                Sign-in probe (no auth).
"""

from __future__ import annotations

import zlib
from typing import AsyncIterator, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from config import PI_RELAY_HTTP_BASE


router = APIRouter(prefix="/llm-proxy", tags=["llm-proxy"])


# Headers we always strip from the inbound request before forwarding
# upstream. Any auth that the local SDK might have stamped on (the
# Anthropic-Vertex SDK adds an empty Authorization, the @google/genai
# SDK adds whatever credentials chain it walked) is replaced with our
# JWT. Hop-by-hop headers are also dropped — httpx will recompute
# them for the upstream connection.
_HEADERS_TO_DROP = {
    "host",
    "authorization",
    "x-api-key",
    "anthropic-api-key",
    "x-goog-api-key",
    "x-goog-user-project",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
}


def _fresh_bearer() -> Optional[str]:
    """Return the latest cached desktop bearer, refreshing if needed.

    Lazy import is deliberate: ``routes.desktop_auth`` imports the
    Clerk SDK on first touch, which we don't want to pay for on a
    desktop where the LLM proxy is never used (e.g. BYOK-only
    operators).
    """
    try:
        from routes.desktop_auth import get_cached_desktop_session
    except ImportError:
        return None
    cached = get_cached_desktop_session()
    if not cached:
        return None
    jwt, _user_id = cached
    return jwt or None


def _scrub_headers(src: dict[str, str]) -> dict[str, str]:
    """Pass through every header except auth + hop-by-hop. Lower-cased
    on the way out to dodge case-sensitivity bugs in upstream proxies."""
    out: dict[str, str] = {}
    for k, v in src.items():
        if k.lower() in _HEADERS_TO_DROP:
            continue
        out[k] = v
    return out


def _is_streaming_action(rest_path: str) -> bool:
    """Vertex actions ending in ``streamRawPredict`` /
    ``streamGenerateContent`` produce SSE. We must keep the upstream
    connection open across the response in those cases; the catch-all
    forwarder uses this to flip ``stream=True`` on the httpx request.

    Safe default for unknown actions: non-streaming. A non-streaming
    request streamed back is still consumable (just slower) so a
    misclassification toward non-stream is the safer error.
    """
    last = rest_path.rsplit(":", 1)[-1] if ":" in rest_path else ""
    return last in ("streamRawPredict", "streamGenerateContent")


@router.post("/vertex/{rest:path}")
async def vertex_passthrough(rest: str, request: Request):
    """Forward an arbitrary Vertex API call to the cloud relay.

    Pi's existing ``anthropic-vertex`` / ``google-vertex`` providers
    target a URL of the form
    ``{base}/v1/projects/{p}/locations/{l}/publishers/{pub}/models/{m}:action``.
    We set the SDK's base URL to ``http://127.0.0.1:<port>/llm-proxy/vertex``
    so requests land here, then forward path + body verbatim to
    ``${PI_RELAY_HTTP_BASE}/v1/relay/vertex/{rest}``.

    The cloud relay validates the path shape, JWT, plan, and budget
    before swapping the bearer for ADC. Body is opaque to us.
    """
    bearer = _fresh_bearer()
    if not bearer:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "desktop_signin_required",
                "message": (
                    "No active sign-in for this desktop. Open the app "
                    "and sign in to continue."
                ),
            },
        )

    body = await request.body()
    headers = _scrub_headers(dict(request.headers))
    headers["authorization"] = f"Bearer {bearer}"
    headers["content-type"] = headers.get("content-type") or "application/json"

    upstream_url = f"{PI_RELAY_HTTP_BASE}/v1/relay/vertex/{rest}"
    streaming = _is_streaming_action(rest)

    # 5-min total: matches the cloud relay's upstream timeout. Connect
    # timeout stays short so a network blip surfaces fast (the SPA
    # then renders a "network" toast and lets the user retry).
    timeout = httpx.Timeout(connect=15.0, read=300.0, write=60.0, pool=15.0)

    if streaming:
        client = httpx.AsyncClient(timeout=timeout)
        try:
            req = client.build_request(
                "POST", upstream_url, content=body, headers=headers
            )
            response = await client.send(req, stream=True)
        except httpx.RequestError as exc:
            await client.aclose()
            raise HTTPException(
                status_code=502,
                detail={"code": "relay_unreachable", "message": str(exc)},
            )

        # ── gzip-on-the-wire handling ───────────────────────────────
        # Vertex AI gzips SSE on the wire (``Content-Encoding: gzip``
        # is set on the GCP→Cloud Run leg) but our cloud relay forwards
        # via ``response.aiter_raw()`` and only propagates Content-Type
        # in its StreamingResponse — the encoding hint is dropped.
        # Result: we receive gzipped bytes but ``response.headers``
        # has NO ``Content-Encoding: gzip`` for us to forward, AND
        # pi's SDK can't auto-decompress because there's no header to
        # tell it the body is gzipped. Pi parses the gzip magic bytes
        # as garbage SSE frames, records 0 text + 0 tokens, and
        # ``message_end`` fires immediately after ``message_start``
        # with empty content. The user sees their prompt vanish into
        # a no-op assistant turn.
        #
        # Two ways to fix this:
        #   1. Update the cloud relay to propagate Content-Encoding —
        #      the right long-term fix; a separate change in
        #      ``web/backend/routes/llm_relay.py`` is in flight.
        #   2. Detect gzip locally and either decompress on the way
        #      through OR re-stamp the encoding header.
        # We do BOTH:
        #   * If upstream advertised ``Content-Encoding`` we forward
        #     it verbatim (transparent-proxy behaviour, used once the
        #     cloud relay propagates the header).
        #   * Otherwise we sniff the first chunk; if it starts with
        #     the gzip magic bytes (``1f 8b 08``) we decompress
        #     incrementally and forward plain bytes downstream. Pi's
        #     SDK then sees a real ``text/event-stream`` body with
        #     no encoding header — exactly what its SSE parser
        #     expects.
        upstream_encoding = response.headers.get("content-encoding")

        async def _gen() -> AsyncIterator[bytes]:
            decoder: Optional["zlib._Decompress"] = None
            sniffed = False
            try:
                async for chunk in response.aiter_raw():
                    if not sniffed and not upstream_encoding and chunk[:3] == b"\x1f\x8b\x08":
                        # 16 + MAX_WBITS = "treat header as gzip".
                        # Without that flag zlib expects raw deflate
                        # and barfs on the gzip header bytes.
                        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                    sniffed = True
                    if decoder is not None:
                        out = decoder.decompress(chunk)
                        if out:
                            yield out
                    else:
                        yield chunk
                if decoder is not None:
                    tail = decoder.flush()
                    if tail:
                        yield tail
            finally:
                await response.aclose()
                await client.aclose()

        media_type = response.headers.get("content-type") or "text/event-stream"
        passthrough_headers: dict[str, str] = {}
        # Only propagate Content-Encoding if upstream already supplied
        # it AND we're not the ones decompressing — otherwise we'd
        # mark a plain-bytes body as gzip and pi would barf.
        if upstream_encoding:
            passthrough_headers["content-encoding"] = upstream_encoding
        for header_name in (
            "cache-control",
            "x-anthropic-request-id",
            "anthropic-request-id",
            "x-request-id",
        ):
            value = response.headers.get(header_name)
            if value is not None:
                passthrough_headers[header_name] = value
        return StreamingResponse(
            _gen(),
            status_code=response.status_code,
            media_type=media_type,
            headers=passthrough_headers,
        )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(upstream_url, content=body, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "relay_unreachable", "message": str(exc)},
        )

    # ``resp.json()``, ``resp.text``, and friends transparently
    # decompress the upstream body using whatever Content-Encoding
    # the response advertised — that's why we don't need the
    # gzip-sniffing dance from the streaming branch here. ``resp.text``
    # is the decoded payload; we rebuild a JSON / passthrough response
    # from that without re-encoding.
    if resp.headers.get("content-type", "").startswith("application/json"):
        try:
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except ValueError:
            pass
    return JSONResponse(
        content={"raw": resp.text},
        status_code=resp.status_code,
    )


# ── Typst docs (server-side corpus + LLM call) ────────────────────────
@router.post("/typst/search_docs")
async def typst_search_docs(request: Request):
    """Forward a search_docs JSON brief to the cloud's typst endpoint.

    The local extension (extensions/typst-tools.ts) POSTs ``{package,
    query}`` here; we inject the cached Clerk JWT and forward to
    ``${PI_RELAY_HTTP_BASE}/v1/typst/search_docs``. The cloud responds
    with ``{answer, cited, elapsedMs, model, usage}``, which we replay
    verbatim back to the extension. Body is small (~100 bytes up,
    ~5 KB down) — no streaming, no special handling.
    """
    bearer = _fresh_bearer()
    if not bearer:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "desktop_signin_required",
                "message": (
                    "No active sign-in for this desktop. Open the app "
                    "and sign in to continue."
                ),
            },
        )

    body = await request.body()
    headers = _scrub_headers(dict(request.headers))
    headers["authorization"] = f"Bearer {bearer}"
    headers["content-type"] = headers.get("content-type") or "application/json"

    upstream_url = f"{PI_RELAY_HTTP_BASE}/v1/typst/search_docs"
    timeout = httpx.Timeout(connect=15.0, read=180.0, write=60.0, pool=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(upstream_url, content=body, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "relay_unreachable", "message": str(exc)},
        )

    if resp.headers.get("content-type", "").startswith("application/json"):
        try:
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except ValueError:
            pass
    return JSONResponse(
        content={"raw": resp.text},
        status_code=resp.status_code,
    )


# ── Health ───────────────────────────────────────────────────────────
@router.get("/_health")
def proxy_health():
    """Public probe — returns ``{"signed_in": bool, "cloud": "..."}``.

    No auth required: the sidecar binds to 127.0.0.1 only, so this is
    already gated by the OS. Useful for the SPA to render a "cloud
    relay ready" indicator without doing a full LLM round-trip.
    """
    bearer = _fresh_bearer()
    return {
        "signed_in": bearer is not None,
        "cloud": PI_RELAY_HTTP_BASE,
    }
