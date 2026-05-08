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
    "Title the user's chat in 3–6 words, Title Case, ≤50 chars. "
    "Describe the topic or intent — never the act of asking. "
    "Always produce a title for any topical message, even vague ones "
    "(use a generic label like 'Open-Ended Build' or 'Bug Fix Help'). "
    "Output the title only — no quotes, punctuation, or preamble. "
    "Reply NO_TITLE only for pure greetings like 'hi' or 'hey'."
)

# Minimum prompt length to bother calling Haiku at all. Anything
# shorter is almost certainly a greeting or a typo and the heuristic
# title ("Hi", "Test", etc.) is just as informative as anything an LLM
# would invent.
_MIN_PROMPT_CHARS = 12


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

    Never raises. Callers can `await asyncio.create_task(generate_title(p))`
    safely.
    """
    text = (prompt or "").strip()
    if len(text) < _MIN_PROMPT_CHARS:
        # Too thin to title meaningfully. The heuristic title for a
        # short prompt is itself just the trimmed prompt, which is
        # already as good as it gets — don't burn an LLM call.
        return None
    if len(text) > _PROMPT_TRIM_CHARS:
        text = text[:_PROMPT_TRIM_CHARS]

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
    body = {
        "anthropic_version": "vertex-2023-10-16",
        "max_tokens": _TITLE_MAX_TOKENS,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": text}],
    }

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
    except Exception as exc:
        print(f"[title_gen] vertex request failed: {exc}", file=sys.stderr)
        return None

    if resp.status_code != 200:
        # On 401 the cached token is bad — drop it so the next call
        # forces a fresh gcloud fetch.
        if resp.status_code == 401:
            _token_cache.clear()
        # 200-char preview is enough to debug without polluting the log.
        body_preview = resp.text[:200].replace("\n", " ")
        print(
            f"[title_gen] vertex http {resp.status_code}: {body_preview}",
            file=sys.stderr,
        )
        return None

    try:
        data = resp.json()
        # Anthropic Messages format: content is a list of blocks; we want
        # the concatenated text from the first text block.
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
    except Exception as exc:
        print(f"[title_gen] failed to parse vertex response: {exc}", file=sys.stderr)
        return None
    return None
