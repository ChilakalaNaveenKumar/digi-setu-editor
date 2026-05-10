"""
Typst docs server-side endpoint — corpus lives here, not on user laptops.

Why this exists
---------------
The desktop ``search_docs`` tool (defined in
``extensions/typst-tools.ts``) used to do its own LLM call from the
laptop, sending the full ~210k-token typst/cetz/fletcher/quill/codly/
circuiteria/touying corpus over the wire on every invocation. This
broke for non-dev users (the corpus only existed on disk if the user
happened to pick our dev repo as their workspace) and was slow even
when it worked because:

  * 1–2 MB of body per call eats laptop bandwidth.
  * Vertex's implicit prompt cache misses across distinct laptop
    request fingerprints, so each call paid full price (30–90 s).

Moving the corpus + the LLM call to the server fixes all three:

  * Corpus is loaded from ``/app/guides/`` once at process boot.
  * Every user hitting this VM sends the BYTE-IDENTICAL corpus prefix
    to Vertex, so its prompt cache hits on the second call onwards
    (~1 s response after the first warm-up; 90 % discount on the
    cached input tokens).
  * Laptop only ships the ~100-byte query and receives ~5 KB answer.

The contract this endpoint exposes mirrors the JSON the local tool
used to build itself, so the extension can swap to remote with a
single env-var-gated branch.

Defenses
--------
Same defense chain as ``llm_relay.py`` — bearer JWT, per-user rate-
limit (shared ``relay.message`` bucket; one search_docs counts the
same as one relay LLM call from a quota perspective), and credit
gate. Plan gating is intentionally NOT enforced because the router
model is operator-pinned: the user can't pick it, so there's nothing
to gate. We DO however cost-record the usage against the user's
ledger — a search_docs call is real spend.

Endpoint
--------
- POST /v1/typst/search_docs
    body: {"package": "cetz", "query": "how do I draw a curve?"}
    out:  {
            "answer": "...",
            "cited": ["guides/cetz-0.5.0/docs/...", ...],
            "elapsedMs": 1234,
            "model": "gemini-3-flash-preview",
            "usage": {"input": ..., "output": ..., "cacheRead": ...,
                      "cacheWrite": ...},
          }
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from routes.llm_relay import (
    _adc_token,
    _gcp_project,
    _record_cost,
    _resolve_anthropic_location,
    _resolve_google_location,
    _vertex_host,
)
from services.auth import RelayPrincipal, verify_relay_jwt
from services.billing import check_relay_budget
from services.rate_limit import consume_user_quota


router = APIRouter(prefix="/v1/typst", tags=["typst-docs"])


# Mirror of VALID_CORPORA + PACKAGES from extensions/typst-tools.ts.
# When adding a package: also drop its docs into ``guides/<pkg>-<ver>/``
# and confirm a fresh build of the corpus index includes it (server
# logs ``[typst-docs] corpus loaded`` summary on startup).
_VALID_PACKAGES: frozenset[str] = frozenset({
    "typst", "cetz", "fletcher", "quill", "codly", "circuiteria", "touying",
})

_PACKAGES = {
    "typst": ("Typst",
              "core Typst language and stdlib"),
    "cetz": ("CeTZ",
             "vector drawing — `canvas`, `draw`, `line`, `circle`, `content`, `decorations`"),
    "fletcher": ("Fletcher",
                 "diagrams over CeTZ — `diagram`, `node`, `edge`, marks, layout"),
    "quill": ("Quill",
              "quantum circuit diagrams — `quantum-circuit`, `gate`, `ctrl`, `mqgate`, `meter`"),
    "codly": ("Codly",
              "code-block styling — `codly()`, `codly-init`, line numbers, language pills, highlights"),
    "circuiteria": ("Circuiteria",
                    "block circuit diagrams — `element.block/alu/multiplexer`, `wire.direct/zigzag/dodge`, gates"),
    "touying": ("Touying",
                "slide framework — themes, slide envelopes, `#pause`, `#meanwhile`, `only`/`uncover`"),
}


# ── Corpus loader ─────────────────────────────────────────────────────
#
# Read every .md / .typ under guides/, bucket by package owner, and
# concatenate into ONE big string per package. Mirrors loadCorpus in
# extensions/typst-tools.ts so we can lift the per-call LLM logic
# without semantic drift.
#
# We exclude vendored upstream source folders (``guides/<pkg>-<semver>/``)
# from the typst bucket — they're test files / examples we keep on disk
# for the AI to grep but they bloat the corpus past 1M tokens and
# cross-contaminate (cetz tests landing under typst, etc.). Same rule
# as the extension's `EXCLUDE_VENDORED_PATTERN`.
_VENDORED_PATTERN = re.compile(r"^guides/[^/]+-\d+\.\d+\.\d+(-[A-Za-z0-9.+-]+)?/")


def _guides_root() -> Path:
    """Where the corpus lives in the deployed image. Overridable for
    tests and dev (set ``PI_TYPST_GUIDES_ROOT`` to point at a different
    directory)."""
    override = os.environ.get("PI_TYPST_GUIDES_ROOT", "").strip()
    if override:
        return Path(override).resolve()
    # Container path (set by deploy/Dockerfile.backend COPY guides/ ./guides/)
    container = Path("/app/guides")
    if container.exists():
        return container.resolve()
    # Dev fallback — repo root, two dirs up from web/backend/routes/
    return (Path(__file__).resolve().parents[3] / "guides").resolve()


_CORPUS_CACHE: Optional[dict[str, str]] = None
_CORPUS_LOCK = asyncio.Lock()


def _bucket_for(rel: str) -> str:
    """Decide which package owns a guides/-relative path. Mirrors the
    extension's classification: longest matching prefix wins, default
    to ``typst``."""
    candidates: list[tuple[int, str]] = []
    for key in _PACKAGES.keys():
        prefix = f"guides/{key}/"
        if rel.startswith(prefix):
            candidates.append((len(prefix), key))
    if not candidates:
        return "typst"
    candidates.sort(key=lambda t: -t[0])
    return candidates[0][1]


def _load_corpus_sync(root: Path) -> dict[str, str]:
    """Walk ``root`` and produce ``{package_key: concatenated_text}``.

    Skips vendored upstream source folders (``guides/<pkg>-<semver>/``)
    so the typst bucket doesn't balloon past 1M tokens with tests.
    """
    if not root.exists():
        return {k: "" for k in _PACKAGES}

    buckets: dict[str, list[str]] = {k: [] for k in _PACKAGES}
    skipped_vendored = 0
    total_files = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".md", ".typ"):
            continue
        rel = "guides/" + path.relative_to(root).as_posix()
        if _VENDORED_PATTERN.match(rel):
            skipped_vendored += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        owner = _bucket_for(rel)
        buckets[owner].append(f"<<<file: {rel}>>>\n{text}\n")
        total_files += 1

    print(
        f"[typst-docs] corpus loaded — root={root} "
        f"files={total_files} skipped_vendored={skipped_vendored} "
        f"sizes={ {k: len(v) for k, v in {kk: ''.join(vv) for kk, vv in buckets.items()}.items()} }",
        file=sys.stderr,
    )
    return {k: "".join(v) for k, v in buckets.items()}


async def _ensure_corpus() -> dict[str, str]:
    """Lazy-load the corpus on first request. Subsequent calls return
    the cached dict (cheap)."""
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None:
        return _CORPUS_CACHE
    async with _CORPUS_LOCK:
        if _CORPUS_CACHE is not None:
            return _CORPUS_CACHE
        root = _guides_root()
        # The walk + read is sync I/O. Off-loop it so we don't stall
        # the event loop on the first hit (typst corpus is ~10 MB on
        # disk; cold read can take 100–300 ms on a busy VM).
        loop = asyncio.get_event_loop()
        _CORPUS_CACHE = await loop.run_in_executor(None, _load_corpus_sync, root)
        return _CORPUS_CACHE


# ── Prompt construction (mirrors typst-tools.ts) ──────────────────────
def _persona_for(package: str) -> str:
    label, blurb = _PACKAGES[package]
    if package == "typst":
        return (
            "You're a senior Typst engineer. The user is working in core "
            "Typst (no third-party packages). The full text of every "
            "core-Typst doc and example file is in your context."
        )
    return (
        f"You're a senior engineer who knows the {label} Typst package "
        f"cold. {label}: {blurb}. The full text of every doc and example "
        f"file in that package is in your context."
    )


_RULES = (
    "Another agent will read your reply and use it to write and compile a real Typst artifact. "
    "So your reply IS the answer, not a routing memo.\n\n"
    "Rules:\n"
    "- Go deep. Don't give an overview — give a full, in-depth explanation. "
    "Cover what the relevant symbols do, what each parameter means, and how the pieces compose.\n"
    "- Show 2-3 fully-formed copy-paste examples (15-60 lines each). Each example should target "
    "a different real use case, not three variations of the same thing. Walk through at least "
    "one of them inline so the reader sees why each line is there.\n"
    "- Call out non-obvious behaviours, common pitfalls, parameter combinations that matter, "
    "and edge cases (units, defaults, scope, layout interactions).\n"
    "- Use the exact symbol names and import lines from the corpus. If the question touches "
    "multiple packages, say which package owns each symbol.\n"
    "- If the corpus genuinely doesn't cover the question, say so plainly in one line; "
    "don't invent API.\n"
    "- Do NOT print a \"Sources\" section, a citations footer, or any list of doc paths. "
    "The agent doesn't need them.\n"
    "- No preamble. No \"great question\". Just the answer."
)


# ── Cited-source extractor (mirrors splitAnswerAndSources) ────────────
_CITED_PATTERN = re.compile(r"`?(guides/[A-Za-z0-9_./-]+\.(?:md|typ))`?")


def _split_answer_and_sources(raw: str) -> tuple[str, list[str]]:
    """Return ``(answer, cited)``. ``cited`` is a deduped list of
    ``guides/...`` paths the model referenced inline OR in a Sources
    block. Same logic as the extension's helper."""
    sources_marker = re.search(r"\n\s*Sources?\s*:?\s*\n", raw, re.IGNORECASE)
    if not sources_marker:
        inline = [m.group(1) for m in _CITED_PATTERN.finditer(raw)]
        seen: set[str] = set()
        deduped = [x for x in inline if not (x in seen or seen.add(x))]
        return raw.strip(), deduped
    answer = raw[: sources_marker.start()].strip()
    tail = raw[sources_marker.end():].splitlines()
    cited: list[str] = []
    for line in tail:
        line = line.lstrip(" \t*-•").strip().strip("`").strip()
        if line.startswith("guides/") and (line.endswith(".md") or line.endswith(".typ")):
            if line not in cited:
                cited.append(line)
    return answer, cited


# ── Vertex callers ────────────────────────────────────────────────────
def _router_model() -> str:
    """Server-side pin for the search_docs router. Defaults to
    Gemini Flash (matches the local extension's default). Operators
    can pin Claude Haiku 4.5 via env if they want explicit
    cache_control."""
    return os.environ.get("PI_TYPST_ROUTER_MODEL", "gemini-3-flash-preview").strip()


async def _call_anthropic_vertex(
    *, model_id: str, persona: str, query: str, package: str, corpus_text: str,
) -> tuple[str, dict[str, int]]:
    """POST to Vertex's :rawPredict for an anthropic-on-vertex model.

    We mark the corpus block as ``cache_control: ephemeral`` so back-to-
    back lookups on the same package hit the prompt cache (~90% off).
    This is the same wire shape pi-coding-agent's anthropic-vertex
    provider builds — kept in lockstep for billing parity.
    """
    project = _gcp_project()
    if not project:
        raise HTTPException(
            status_code=503,
            detail={"code": "relay_misconfigured",
                    "message": "GOOGLE_CLOUD_PROJECT unset on the relay"},
        )
    token = _adc_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail={"code": "adc_unavailable",
                    "message": "Vertex ADC unavailable — see backend logs"},
        )
    location = _resolve_anthropic_location(model_id)
    host = _vertex_host(location)
    url = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/publishers/anthropic/models/{model_id}:rawPredict"
    )

    body = {
        "anthropic_version": "vertex-2023-10-16",
        "max_tokens": 4096,
        "temperature": 0.2,
        "system": persona,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"The full {package} corpus follows. Read what you need; ignore the rest.\n\n{corpus_text}",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": f"{_RULES}\n\nThe user's brief:\n{query}",
                    },
                ],
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, content=json.dumps(body), headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_unreachable", "message": str(exc)},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"code": "vertex_error", "status": resp.status_code,
                    "body": resp.text[:500]},
        )
    data = resp.json()
    text = "\n".join(
        (b.get("text") or "")
        for b in (data.get("content") or [])
        if b.get("type") == "text"
    ).strip()
    u = data.get("usage") or {}
    cache_read = int(u.get("cache_read_input_tokens") or 0)
    cache_write = int(u.get("cache_creation_input_tokens") or 0)
    base_input = int(u.get("input_tokens") or 0)
    usage = {
        "input": max(0, base_input - cache_read - cache_write),
        "output": int(u.get("output_tokens") or 0),
        "cacheRead": cache_read,
        "cacheWrite": cache_write,
    }
    return text, usage


async def _call_google_vertex(
    *, model_id: str, persona: str, query: str, package: str, corpus_text: str,
) -> tuple[str, dict[str, int]]:
    """POST to Vertex's :generateContent for a Gemini model.

    No explicit ``cache_control`` — Vertex's implicit prefix cache fires
    automatically when ≥ ~32 input tokens are byte-identical across
    requests, which is true of the persona+rules+corpus prefix every
    user shares from THIS VM. Cache hit-rate ≈ 100 % after warm-up.
    """
    project = _gcp_project()
    if not project:
        raise HTTPException(
            status_code=503,
            detail={"code": "relay_misconfigured",
                    "message": "GOOGLE_CLOUD_PROJECT unset on the relay"},
        )
    token = _adc_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail={"code": "adc_unavailable",
                    "message": "Vertex ADC unavailable — see backend logs"},
        )
    location = _resolve_google_location(model_id)
    host = _vertex_host(location)
    url = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/publishers/google/models/{model_id}:generateContent"
    )
    prompt = (
        f"{persona}\n\n{_RULES}\n\nThe user's brief:\n{query}\n\n"
        f"The full corpus follows. Read what you need, ignore the rest.\n\n"
        f"{corpus_text}"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 30000,
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, content=json.dumps(body), headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_unreachable", "message": str(exc)},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"code": "vertex_error", "status": resp.status_code,
                    "body": resp.text[:500]},
        )
    data = resp.json()
    parts = []
    for cand in data.get("candidates", []) or []:
        for p in (cand.get("content") or {}).get("parts", []) or []:
            if isinstance(p.get("text"), str):
                parts.append(p["text"])
    text = "".join(parts).strip()
    um = data.get("usageMetadata") or {}
    prompt_tokens = int(um.get("promptTokenCount") or 0)
    cache_read = int(um.get("cachedContentTokenCount") or 0)
    output = int(um.get("candidatesTokenCount") or 0)
    thoughts = int(um.get("thoughtsTokenCount") or 0)
    usage = {
        "input": max(0, prompt_tokens - cache_read),
        # Fold reasoning tokens into output so the host ledger doesn't
        # double-count them (matches normalizeGeminiUsage in the extension).
        "output": output + thoughts,
        "cacheRead": cache_read,
        "cacheWrite": 0,
    }
    return text, usage


# ── Endpoint ──────────────────────────────────────────────────────────
@router.post("/search_docs")
async def search_docs(
    request: Request,
    principal: RelayPrincipal = Depends(verify_relay_jwt),
):
    """Server-side search_docs. See module docstring for the contract."""
    consume_user_quota(principal.user_id)
    check_relay_budget(principal.user_id, principal.plan)

    raw = await request.body()
    try:
        payload = json.loads(raw or b"{}")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")

    package = str(payload.get("package") or "").strip()
    query = str(payload.get("query") or "").strip()
    if package not in _VALID_PACKAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_package",
                "package": package,
                "valid": sorted(_VALID_PACKAGES),
            },
        )
    if not query:
        raise HTTPException(
            status_code=400,
            detail={"code": "missing_query", "message": "`query` is required"},
        )

    corpus = await _ensure_corpus()
    corpus_text = corpus.get(package, "")
    if not corpus_text.strip():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "empty_corpus",
                "package": package,
                "message": (
                    "Server-side corpus is empty for this package. "
                    "This is an operator misconfiguration — guides/ may "
                    "not have been COPYd into the image."
                ),
            },
        )

    model_id = _router_model()
    is_anthropic = model_id.lower().startswith("claude-")
    persona = _persona_for(package)
    started = time.monotonic()
    try:
        if is_anthropic:
            text, usage = await _call_anthropic_vertex(
                model_id=model_id, persona=persona, query=query,
                package=package, corpus_text=corpus_text,
            )
        else:
            text, usage = await _call_google_vertex(
                model_id=model_id, persona=persona, query=query,
                package=package, corpus_text=corpus_text,
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Defensive: never let a bug in the upstream dance bubble up as
        # a 500 — wrap it as a 502 so the client renders a network
        # error instead of exposing a stack trace.
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_error", "message": str(exc)},
        )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    answer, cited = _split_answer_and_sources(text)

    _record_cost(
        user_id=principal.user_id,
        model_id=model_id,
        usage=usage,
        wall_seconds=elapsed_ms / 1000.0,
    )

    return {
        "answer": answer,
        "cited": cited,
        "elapsedMs": elapsed_ms,
        "model": model_id,
        "usage": usage,
    }


# ── Health / introspection probe ──────────────────────────────────────
@router.get("/_health")
async def typst_docs_health():
    """Public probe — reports which packages have a non-empty corpus on
    disk. Useful when the deploy went through but the COPY guides/
    line was missing or the volume mount failed."""
    corpus = await _ensure_corpus()
    return {
        "guides_root": str(_guides_root()),
        "router_model": _router_model(),
        "packages": {k: len(v) for k, v in corpus.items()},
    }
