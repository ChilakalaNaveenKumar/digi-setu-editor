"""
Cloud-relay-via-HTTP spawn helpers (Vertex-passthrough flavour).

When the desktop user is signed in but doesn't have a BYOK key for the
picked model, we still want to spawn pi LOCALLY (so file ops touch the
user's chosen folder, see ``routes/llm_proxy.py`` for the full
rationale) — but pi must talk to our cloud relay for the actual LLM
call so we never ship ADC to the laptop.

This module is the one place that knows how to translate a
"cloud-routed model" + a backend env dict into a Vertex-passthrough
spawn env. Mirror of ``services.byok``: ``byok_provider_for`` +
``byok_subprocess_env`` sit on the BYOK branch; ``cloud_relay_provider_for``
+ ``cloud_relay_subprocess_env`` sit on this branch. Pi_session.py
picks one (or neither) before spawning.

Architecture choice — Vertex passthrough vs. consumer-API translation
---------------------------------------------------------------------
We keep pi's existing ``anthropic-vertex`` / ``google-vertex``
providers and just redirect their SDK base URL to our localhost proxy.
The proxy forwards to ``${PI_CLOUD_API_BASE}/v1/relay/vertex/{rest}``,
which validates the JWT, swaps in ADC, and proxies to real Vertex.

Why passthrough over translation:
  * Zero changes to pi-coding-agent's model registry — our model ids
    (``claude-sonnet-4-6`` etc.) are already registered under
    ``anthropic-vertex`` / ``google-vertex``.
  * Body shapes match upstream exactly — no Anthropic⇄Vertex /
    Gemini⇄Vertex translation code to maintain.
  * One env var per provider is the only knob needed.

Env vars set
------------
  ``ANTHROPIC_VERTEX_BASE_URL``  — natively respected by
                                   ``@anthropic-ai/vertex-sdk``
                                   (no patch required).
  ``GOOGLE_VERTEX_BASE_URL``     — respected by ``@google/genai`` BUT
                                   pi's wrapper passes a hardcoded
                                   ``model.baseUrl`` that overrides it;
                                   we land a small patch in
                                   ``patches/apply-edits.mjs`` that
                                   makes the wrapper prefer the env
                                   var when set.

ADC scrub policy
----------------
We DO NOT strip ``GOOGLE_CLOUD_PROJECT`` / ``GOOGLE_CLOUD_LOCATION`` —
the Anthropic-Vertex / Google-Vertex SDKs need them to build the
``/v1/projects/{project}/locations/{location}/...`` URL path. The
project + location they encode in the path is purely cosmetic from
the relay's point of view: the cloud-side passthrough endpoint
ignores them and forces its OWN configured project + location before
forwarding upstream (see ``web/backend/routes/llm_relay.py``
``vertex_passthrough``). So the laptop pi can ship any project id it
likes — the cloud relay overrides it.

We DO strip ``GOOGLE_APPLICATION_CREDENTIALS`` and the
``PI_TRUST_GCE_METADATA`` opt-in. The ADC chain MUST NOT be walked
on the laptop — even if a credentials file exists by accident, the
SDK should not pick it up. The cloud relay is the sole path to a
real Vertex bearer.
"""

from __future__ import annotations

from typing import Optional

from config import local_proxy_base
from services.models_registry import ModelSpec


def _proxy_base_url() -> str:
    """Backwards-compat alias for ``config.local_proxy_base()``.

    All new call sites should import ``local_proxy_base`` directly
    from ``config``; this thin wrapper is kept so existing tests keep
    passing without churn. The single source of truth for the URL
    shape, error policy, and PORT env handling lives in ``config.py``.
    """
    return local_proxy_base()


def cloud_relay_provider_for(spec: ModelSpec) -> Optional[str]:
    """Return the pi provider name that talks to our cloud relay
    for this model, or None if there is no relay route for it.

    For the Vertex-passthrough flavour the provider name is unchanged:
      ``anthropic-vertex``  → ``anthropic-vertex``
      ``google-vertex``     → ``google-vertex``
    Returning the provider verbatim (rather than None) tells the
    caller "this model has a relay route" and signals which env vars
    to set. Other provider types return None — we don't relay raw
    OpenAI etc. today (BYOK is the only path for those).
    """
    cloud = (spec.pi_provider or "").strip()
    if cloud in ("anthropic-vertex", "google-vertex"):
        return cloud
    return None


def cloud_relay_subprocess_env(spec: ModelSpec, env: dict[str, str]) -> dict[str, str]:
    """Return a NEW env dict configured for cloud-relay-via-HTTP.

    Mutations:
      * Set ``ANTHROPIC_VERTEX_BASE_URL`` (anthropic-vertex provider)
        OR ``GOOGLE_VERTEX_BASE_URL`` (google-vertex) so the SDK
        targets our localhost proxy. The proxy forwards to the cloud
        Vertex passthrough endpoint with the cached Clerk JWT.
      * Strip ``GOOGLE_APPLICATION_CREDENTIALS`` + ADC-trust opt-ins
        so the laptop-side SDK never tries to walk the ADC chain.

    Caller (pi_session._build_subprocess_cmd) keeps the provider name
    as-is — this is a passthrough flow, not a provider swap.
    """
    out = dict(env)
    base = _proxy_base_url()
    pi_provider = (spec.pi_provider or "").strip()

    if pi_provider == "anthropic-vertex":
        # @anthropic-ai/vertex-sdk reads this env var when no baseURL
        # is passed to the constructor. Our anthropic-vertex.js
        # wrapper (see patches/files/anthropic-vertex.js) doesn't
        # pass one, so the env var wins. Targets the cloud relay's
        # /v1/relay/vertex/* endpoint via the localhost proxy.
        # The "/v1" suffix is what the SDK appends after; we provide
        # the path up to /v1 so the SDK's project/locations/... gets
        # tacked on correctly.
        out["ANTHROPIC_VERTEX_BASE_URL"] = f"{base}/vertex/v1"
    elif pi_provider == "google-vertex":
        # @google/genai's getBaseUrl() respects this env var ONLY when
        # httpOptions.baseUrl is not set. pi-ai's google-vertex.js
        # passes a hardcoded baseUrl, which overrides the env var. We
        # land a small patch (see patches/apply-edits.mjs §11) that
        # makes the wrapper prefer this env var when set.
        out["GOOGLE_VERTEX_BASE_URL"] = f"{base}/vertex/"

    # Tell the typst-tools.ts extension to call the server endpoint
    # for search_docs instead of doing the LLM call locally with a
    # 210k-token corpus over the wire. The extension's `execute`
    # function checks this env var and falls through to the existing
    # local-LLM path when it's empty (BYOK mode keeps the local
    # behaviour because the user's own keys are direct-to-provider).
    out["PI_TYPST_DOCS_REMOTE_URL"] = f"{base}/typst/search_docs"

    # Strip ADC + Vertex hints. The local pi must NOT walk the ADC
    # chain — there is no Application Default Credentials file on a
    # user's laptop, and even if one existed by accident (operator
    # also runs the cloud backend dev loop on the same machine), we
    # don't want the laptop pi using it. The cloud relay is the sole
    # path to a real Vertex bearer.
    for key in (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "PI_TRUST_GCE_METADATA",
        "GCE_METADATA_HOST",
        "GCE_METADATA_IP",
        "METADATA_SERVER_DETECTION",
    ):
        out.pop(key, None)

    # We deliberately KEEP GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION
    # — the Vertex SDKs use them to build the URL path. The cloud
    # relay's vertex_passthrough re-derives the upstream project +
    # location from its OWN env, so whatever the laptop encodes here
    # is cosmetic and gets overridden. We let pi keep these so the
    # SDK doesn't crash with "Vertex AI requires a project ID".
    #
    # If the parent process didn't set them (the common case on a
    # stock laptop — the desktop user has no GCP env), inject safe
    # placeholders. The Anthropic Vertex SDK and the @google/genai
    # SDK both throw at construction when no project id is resolvable;
    # without these defaults pi crashes BEFORE making any HTTP call
    # and the chat hangs forever on "streaming…". The cloud relay
    # rewrites both values upstream so the placeholder leaks no info.
    out.setdefault("GOOGLE_CLOUD_PROJECT", "relay-managed")
    out.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    # @anthropic-ai/vertex-sdk reads CLOUD_ML_REGION as the region
    # source — match the location placeholder above so the
    # constructor doesn't throw "No region was given".
    out.setdefault("CLOUD_ML_REGION", out["GOOGLE_CLOUD_LOCATION"])

    return out
