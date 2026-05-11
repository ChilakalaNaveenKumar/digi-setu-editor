"""
title_gen — background LLM-based session titling.

Workflow:
    1. chat_ws sets a cheap heuristic title on the first user prompt
       (`Registry.maybe_set_initial_title` + `_derive_title`). That keeps
       the picker readable instantly without blocking the prompt round
       trip on a network call.
    2. chat_ws also schedules `generate_title()` as a background task.
       This module sends the user's first message to Claude Haiku 4.5
       on Vertex with a tightly-scoped system prompt and returns a
       human-friendly 3–6 word title.
    3. chat_ws calls `Registry.maybe_replace_heuristic_title(sid, old,
       new)` — a compare-and-swap that only overwrites if the title is
       still the heuristic version (so a user-initiated rename mid-flight
       wins).

Why Claude Haiku on Vertex (not Gemini Flash or a local model):
    * Same auth path (`gcloud auth print-access-token` + ADC) the rest
      of the stack uses for `pi --provider anthropic-vertex`. No new
      secret to manage.
    * Roughly $0.0003 per title (≈40 input + 12 output tokens at
      Haiku 4.5 rates). Below the noise floor of even the free tier;
      we absorb the cost rather than billing the user.
    * Haiku reliably produces concise, grammatical titles in one shot;
      Flash-Lite tends to either echo the prompt verbatim or pad with
      filler ("Here's a title for your chat: …").

Reliability:
    * 8 s timeout — never blocks a user-visible flow longer than that.
    * Returns None on any error (network, parse, gcloud). Callers MUST
      treat None as "stay on the heuristic title" — no user-facing
      error path.
    * Access tokens are cached in-process for 50 min (gcloud tokens
      are valid for 60 min). One subprocess call per ~50 min, not per
      title.
    * Output is post-processed (length cap, quote/period strip) so a
      hallucinated answer can't break the picker UI.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import time
from typing import Optional

import httpx

# Pinned model. Haiku 4.5 GA region for Anthropic-on-Vertex is "global".
# We deliberately do NOT read PI_TYPST_ROUTER_MODEL because that's the
# user's search_docs override; titles are an internal product feature
# and shouldn't drift if an operator points search_docs at a different
# router.
_TITLE_MODEL = "claude-haiku-4-5"
_TITLE_REGION = "global"
_TITLE_TIMEOUT_S = 8.0
_TITLE_MAX_TOKENS = 32

# We trim user input to this many chars before sending. Title quality
# plateaus well before this — and trimming bounds our input-token cost
# per title regardless of how much they paste.
_PROMPT_TRIM_CHARS = 1500

# Hard caps on the *generated* title. Heuristic uses 50 chars; we match
# so the picker layout doesn't shift when the LLM result lands.
_TITLE_MAX_CHARS = 50

_SYSTEM = (
    "You title chat sessions for a Typst document editor. "
    "Always output a 2–6 word Title Case label (≤50 chars), even for "
    "tiny, vague, or nonsense input — pick the most sensible label "
    "you can. Examples: "
    "'hi' → 'Quick Greeting'; "
    "'test' → 'Test Chat'; "
    "'jhabhjab' → 'Random Input'; "
    "'fix bug' → 'Bug Fix Help'; "
    "'help me write a resume' → 'Resume Drafting Help'. "
    "Describe the topic or intent — never the act of asking. "
    "Output the title only — no quotes, punctuation, or preamble. "
    "Never reply NO_TITLE; always produce a title."
)

# No length gate and no NO_TITLE escape hatch. Every non-empty prompt
# gets routed to Haiku — the cost of one tiny call is negligible
# compared to the UX damage of leaving a typo, "hi", or one-word stub
# as the chat title forever. Haiku is instructed to label even
# nonsense input ("jhabhjab" → "Random Input").


# ── Vertex access token cache ────────────────────────────────────────────
# gcloud tokens last ~60 min. We refresh at 50 min so a slow title call
# can't hit a freshly-expired token.
_TOKEN_TTL_S = 50 * 60
_token_cache: dict[str, float] = {}  # {"value": <token>, "exp": <epoch>}


async def _vertex_access_token() -> Optional[str]:
    """Return a Vertex-ready access token, refreshing every ~50 min.

    We use `gcloud auth application-default print-access-token` (ADC)
    rather than the user-account `gcloud auth print-access-token`
    because:
      * pi itself runs Vertex via ADC (Google's JS auth library walks
        the ADC chain); using the same source means if pi can talk to
        Vertex, so can we.
      * The user-account token sometimes triggers a reauth flow on
        long-running headless processes (uvicorn) and fails non-
        interactively. ADC tokens regenerate from the cached refresh
        token without a reauth prompt.
    """
    now = time.time()
    cached = _token_cache.get("value")
    exp = _token_cache.get("exp", 0)
    if cached and now < exp:
        return cached  # type: ignore[return-value]

    # gcloud is sync — push to a thread so the event loop keeps moving.
    try:
        token = await asyncio.to_thread(
            subprocess.check_output,
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True,
            timeout=10,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print(
            "[title_gen] gcloud not on PATH; "
            "background title generation disabled",
            file=sys.stderr,
        )
        return None
    except subprocess.TimeoutExpired:
        print("[title_gen] gcloud token fetch timed out", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as exc:
        # `stderr=PIPE` captures the helpful "run gcloud auth
        # application-default login" message when ADC isn't set up.
        err = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
        print(
            f"[title_gen] gcloud ADC token fetch failed "
            f"(exit={exc.returncode}): {err or '(no stderr)'}",
            file=sys.stderr,
        )
        return None

    token = token.strip()
    if not token:
        return None
    _token_cache["value"] = token  # type: ignore[assignment]
    _token_cache["exp"] = now + _TOKEN_TTL_S  # type: ignore[assignment]
    return token


# ── Output sanitizer ────────────────────────────────────────────────────
# Strip wrapping quotes, trailing punctuation, and clamp length so the
# picker UI gets a clean string regardless of model whim.
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("`", "`"), ("“", "”"), ("‘", "’"))


def _clean_title(raw: str) -> Optional[str]:
    s = (raw or "").strip()
    if not s:
        return None
    # Some models prefix "Title:" or "Here's a title:" despite instructions.
    s = re.sub(r"^(title|here'?s\s+(?:a|the)\s+title)\s*[:\-—]\s*",
               "", s, flags=re.IGNORECASE)
    # Take just the first non-empty line — defends against the model
    # appending an explanation on a second line.
    s = s.splitlines()[0].strip()
    # Strip a single set of wrapping quotes/backticks if present.
    for opener, closer in _QUOTE_PAIRS:
        if s.startswith(opener) and s.endswith(closer) and len(s) >= 2:
            s = s[len(opener):-len(closer)].strip()
            break
    # Drop trailing sentence punctuation. Keep ! ? if it conveys intent.
    s = re.sub(r"[\.,;:]+$", "", s).strip()
    if not s:
        return None
    if len(s) > _TITLE_MAX_CHARS:
        s = s[: _TITLE_MAX_CHARS - 1].rstrip() + "…"
    return s


# ── Public API ──────────────────────────────────────────────────────────
async def generate_title(prompt: str) -> Optional[str]:
    """Return an LLM-generated title for `prompt`, or None on any failure.

    Routing
    -------
    The actual HTTP call has TWO flavours, picked by ``PI_MODE``:

      * ``PI_MODE=desktop`` — POST to the local ``/llm-proxy/vertex``
        endpoint. ``routes.llm_proxy`` injects the cached Clerk JWT,
        forwards to ``${PI_RELAY_HTTP_BASE}/v1/relay/vertex/...``, and
        the cloud relay swaps in ADC before talking to Vertex. Same
        codepath pi itself uses for chat. No gcloud / ADC required on
        the laptop — the user's machine never sees a Google bearer.

      * ``PI_MODE=web`` (or unset) — POST directly to
        ``aiplatform.googleapis.com`` with a gcloud-ADC bearer. This
        is the original path used by the web VM, where ADC is
        available out of the box.

    Never raises. Callers can `await asyncio.create_task(generate_title(p))`
    safely.
    """
    text = (prompt or "").strip()
    if not text:
        return None
    if len(text) > _PROMPT_TRIM_CHARS:
        text = text[:_PROMPT_TRIM_CHARS]

    body = {
        "anthropic_version": "vertex-2023-10-16",
        "max_tokens": _TITLE_MAX_TOKENS,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": text}],
    }

    deploy_mode = (os.environ.get("PI_MODE", "web") or "web").strip().lower()
    if deploy_mode == "desktop":
        return await _generate_via_cloud_relay(body)
    return await _generate_via_direct_vertex(body)


async def _generate_via_cloud_relay(body: dict) -> Optional[str]:
    """Desktop path: POST through the localhost JWT-injecting proxy.

    The proxy adds ``Authorization: Bearer <Clerk JWT>`` and forwards
    to the cloud relay, which validates the user, swaps in ADC, and
    talks to Vertex. The project id is a placeholder — the cloud
    relay rewrites it server-side (see ``services/relay_spawn.py`` for
    the matching ``relay-managed`` placeholder pi uses).
    """
    try:
        # Lazy import — config.local_proxy_base() raises if PORT isn't
        # set yet (which happens when this module is imported during
        # pytest collection, before the sidecar boots). We don't want
        # the bare import to fail.
        from config import local_proxy_base
        proxy_base = local_proxy_base()
    except Exception as exc:  # noqa: BLE001
        print(
            f"[title_gen] cloud-relay base unavailable ({exc}); "
            "skipping LLM title (heuristic stays)",
            file=sys.stderr,
        )
        return None

    url = (
        f"{proxy_base}/vertex/v1/projects/relay-managed/locations/global"
        f"/publishers/anthropic/models/{_TITLE_MODEL}:rawPredict"
    )
    try:
        async with httpx.AsyncClient(timeout=_TITLE_TIMEOUT_S) as client:
            resp = await client.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
            )
    except httpx.TimeoutException:
        print(
            f"[title_gen] cloud-relay timeout after {_TITLE_TIMEOUT_S}s; "
            "heuristic stays",
            file=sys.stderr,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[title_gen] cloud-relay request failed: {exc}", file=sys.stderr)
        return None

    if resp.status_code != 200:
        body_preview = resp.text[:200].replace("\n", " ")
        print(
            f"[title_gen] cloud-relay http {resp.status_code}: {body_preview}",
            file=sys.stderr,
        )
        return None

    return _parse_anthropic_response(resp)


async def _generate_via_direct_vertex(body: dict) -> Optional[str]:
    """Web/VM path: direct Vertex call with gcloud-ADC bearer."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        # The chat path also sources env.sh into the pi subprocess env,
        # but uvicorn itself may not have it. We can't generate without
        # a project id — silently fall through to keep the heuristic.
        print(
            "[title_gen] GOOGLE_CLOUD_PROJECT unset; "
            "skipping LLM title (heuristic stays)",
            file=sys.stderr,
        )
        return None

    token = await _vertex_access_token()
    if not token:
        return None

    host = (
        "aiplatform.googleapis.com"
        if _TITLE_REGION == "global"
        else f"{_TITLE_REGION}-aiplatform.googleapis.com"
    )
    url = (
        f"https://{host}/v1/projects/{project}/locations/{_TITLE_REGION}"
        f"/publishers/anthropic/models/{_TITLE_MODEL}:rawPredict"
    )

    try:
        async with httpx.AsyncClient(timeout=_TITLE_TIMEOUT_S) as client:
            resp = await client.post(
                url,
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "x-goog-user-project": project,
                },
            )
    except httpx.TimeoutException:
        print(
            f"[title_gen] Vertex timeout after {_TITLE_TIMEOUT_S}s; "
            "heuristic stays",
            file=sys.stderr,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[title_gen] vertex request failed: {exc}", file=sys.stderr)
        return None

    if resp.status_code != 200:
        # On 401 the cached token is bad — drop it so the next call
        # forces a fresh gcloud fetch.
        if resp.status_code == 401:
            _token_cache.clear()
        body_preview = resp.text[:200].replace("\n", " ")
        print(
            f"[title_gen] vertex http {resp.status_code}: {body_preview}",
            file=sys.stderr,
        )
        return None

    return _parse_anthropic_response(resp)


def _parse_anthropic_response(resp: httpx.Response) -> Optional[str]:
    """Extract a clean title string from a Vertex Anthropic Messages response.

    Shared by both the cloud-relay and direct-Vertex flavours — the
    relay is a transparent passthrough, so the wire shape is identical.
    """
    try:
        data = resp.json()
        for block in data.get("content", []):
            if block.get("type") == "text":
                cleaned = _clean_title(block.get("text", ""))
                # Honour the system-prompt opt-out: if Haiku decides
                # the input was too thin to title, it returns the
                # literal "NO_TITLE" sentinel and we keep the
                # heuristic.
                if cleaned and cleaned.upper().replace(" ", "_") == "NO_TITLE":
                    return None
                return cleaned
    except Exception as exc:  # noqa: BLE001
        print(
            f"[title_gen] failed to parse Anthropic response: {exc}",
            file=sys.stderr,
        )
        return None
    return None
    return None
