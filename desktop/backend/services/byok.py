"""
BYOK (bring-your-own-key) routing helpers — desktop only.

In desktop mode the user can drop AI provider credentials into
``~/.digi-setu/.env``. When at least one of these credentials is
present (see ``config.DETECTED_BYOK_KEYS``) the backend skips Clerk
authentication and lets every chat call go directly from the user's
machine to the AI provider's endpoint, billed against the user's own
account.

This module decides, for any given (model, available keys) tuple:

  * route        — "byok" (user pays provider) or "cloud" (we pay,
                   user is on a subscription)
  * pi_provider  — value to pass as ``pi --provider``. With BYOK keys
                   we route directly (anthropic / google / openai)
                   instead of through Vertex (anthropic-vertex /
                   google-vertex), avoiding the Vertex auth path.
  * env          — the single API key the chosen provider needs,
                   stripped down so an Anthropic call doesn't see the
                   user's OpenAI key, etc.

The rules are deliberately conservative — we never silently drop the
user's key in favour of cloud relay or vice versa. The model picker
in the frontend exposes the route per model so the user always knows
which path their next prompt takes (and we can charge / not charge
accordingly).

Web mode is unaffected — :data:`config.BYOK_MODE` is always False
there, so :func:`route_for_model` always returns ``"cloud"``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from config import BYOK_MODE
from services.models_registry import ModelSpec


# Cache the project_id we lifted out of GOOGLE_APPLICATION_CREDENTIALS
# so we don't re-read the JSON on every prompt. Keyed by absolute path
# so a credentials swap (user edits ~/.digi-setu/.env mid-session) is
# picked up correctly.
_PROJECT_ID_CACHE: dict[str, Optional[str]] = {}


def _project_id_from_adc_json(adc_path: str) -> Optional[str]:
    """
    Pull `project_id` out of a Google service-account / ADC JSON file.

    Returns None if the file is unreadable, isn't JSON, or doesn't
    carry a project_id (e.g. a user-credentials JSON that only has a
    refresh_token — those are valid for AI Studio but not for Vertex,
    which is project-scoped).
    """
    try:
        abs_path = str(Path(adc_path).expanduser().resolve())
    except (OSError, RuntimeError):
        return None
    if abs_path in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[abs_path]

    project: Optional[str] = None
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"[byok] WARN: GOOGLE_APPLICATION_CREDENTIALS={abs_path!r} unreadable ({exc}); "
            "Vertex calls will fail until you set GOOGLE_CLOUD_PROJECT in ~/.digi-setu/.env",
            file=sys.stderr,
        )
        _PROJECT_ID_CACHE[abs_path] = None
        return None

    # Service-account JSONs use `project_id`. The legacy gcloud
    # ADC user-credentials JSON uses `quota_project_id` (and only
    # sometimes). Try both.
    if isinstance(data, dict):
        for key in ("project_id", "quota_project_id"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                project = value.strip()
                break

    _PROJECT_ID_CACHE[abs_path] = project
    return project


# ── Per-family preferred BYOK env var ───────────────────────────────
# Order matters within each family: when more than one key is
# present, the first one in the tuple wins. Direct API keys take
# priority over Vertex (GOOGLE_APPLICATION_CREDENTIALS) because direct
# calls have lower latency and clearer billing for the user.
#
# The Vertex entries (GOOGLE_APPLICATION_CREDENTIALS) are
# operator-only: they only kick in when `PI_OPERATOR_VERTEX=1` is set
# in the dev's local env (see config.py). End users never have a
# service-account JSON, and admitting one as BYOK would route their
# Gemini chat through `provider=google-vertex` and hang on the
# missing project. See docs/desktop-architecture.md §5.
_BYOK_PREFS: dict[str, tuple[tuple[str, str], ...]] = {
    # family -> ((env_var, pi_provider), ...)
    "anthropic": (
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("GOOGLE_APPLICATION_CREDENTIALS", "anthropic-vertex"),
    ),
    "google": (
        ("GEMINI_API_KEY", "google"),
        ("GOOGLE_API_KEY", "google"),
        ("GOOGLE_APPLICATION_CREDENTIALS", "google-vertex"),
    ),
    "openai": (
        ("OPENAI_API_KEY", "openai"),
    ),
}

# Mirror of config._PI_OPERATOR_VERTEX. Recomputed each call so a
# `os.environ` mutation in tests is reflected without re-importing.
_OPERATOR_VERTEX_ENVS = ("1", "true", "yes")


def _operator_vertex_admitted() -> bool:
    return os.environ.get("PI_OPERATOR_VERTEX", "").strip().lower() in _OPERATOR_VERTEX_ENVS


def _key_present(name: str) -> bool:
    if name == "GOOGLE_APPLICATION_CREDENTIALS" and not _operator_vertex_admitted():
        return False
    return bool(os.environ.get(name, "").strip())


def detected_keys() -> list[str]:
    """Return env var names that are currently set with a non-empty
    value. Re-evaluated each call so a hot reload of ``~/.digi-setu/
    .env`` (when we add that) is reflected immediately."""
    out = []
    for family_prefs in _BYOK_PREFS.values():
        for env_var, _provider in family_prefs:
            if _key_present(env_var) and env_var not in out:
                out.append(env_var)
    return out


def byok_provider_for(model: ModelSpec) -> Optional[tuple[str, str]]:
    """Pick the best (env_var, pi_provider) for a model, or None if
    the user has no key compatible with this model's family. Hidden
    models (used internally by sub-LLM tools) are routable too — they
    inherit the parent chat's BYOK keys."""
    prefs = _BYOK_PREFS.get(model.family)
    if not prefs:
        return None
    for env_var, pi_provider in prefs:
        if _key_present(env_var):
            return env_var, pi_provider
    return None


def route_for_model(model: ModelSpec) -> str:
    """Return ``"byok"`` if BYOK mode is active and a compatible key
    is present for this model, else ``"cloud"``. Frontend uses this
    to badge the model picker; chat_ws uses it to gate cloud-only
    models behind Clerk login.

    Web mode always returns ``"cloud"`` because BYOK_MODE is False
    by construction (see ``config.py``).
    """
    if not BYOK_MODE:
        return "cloud"
    return "byok" if byok_provider_for(model) is not None else "cloud"


def byok_default_model(catalogue: list[ModelSpec]) -> Optional[str]:
    """Pick the cheapest model in `catalogue` that's BYOK-routable
    given the user's currently-installed keys. Used by chat_ws as the
    fallback when the user has no pinned/workspace model and the plan
    default would land on a cloud-only model that the BYOK gate would
    just reject.

    Cheapest is approximated as lowest output cost — the dimension
    that dominates spend for chat use. Hidden / internal models are
    excluded.
    """
    candidates: list[ModelSpec] = []
    for m in catalogue:
        if getattr(m, "hidden", False):
            continue
        if byok_provider_for(m) is not None:
            candidates.append(m)
    if not candidates:
        return None
    candidates.sort(key=lambda m: (m.cost.output, m.cost.input))
    return candidates[0].id


def byok_subprocess_env(model: ModelSpec, base_env: dict[str, str]) -> dict[str, str]:
    """Build the env dict for spawning ``pi`` with this model under
    BYOK. Starts from ``base_env`` (already-scrubbed subprocess env),
    drops any credentials NOT relevant to the picked provider so an
    Anthropic call never sees the user's Gemini key, and pins
    ``PI_PROVIDER``.

    Caller (``pi_session._build_subprocess_cmd``) is expected to also
    drop our cloud-relay defaults (``GOOGLE_CLOUD_PROJECT`` etc) when
    the picked provider doesn't need them — that's done here by
    omitting them from the returned dict unless the BYOK provider is
    Vertex-based.
    """
    pick = byok_provider_for(model)
    if pick is None:
        # Caller should have checked route_for_model first; defensive
        # fallback: leave env untouched.
        return dict(base_env)

    env_var, pi_provider = pick
    env = dict(base_env)

    # Always pin the picked provider so the user's choice in the UI
    # wins over any PI_PROVIDER inherited from env.sh / parent shell.
    env["PI_PROVIDER"] = pi_provider
    env["PI_MODEL"] = model.id

    # Strip credentials for the OTHER families so the picked provider
    # never sees them. This is defence in depth — pi-coding-agent
    # already keys off PI_PROVIDER, but environment leakage between
    # SDKs has bitten us before.
    other_creds = set()
    for fam, prefs in _BYOK_PREFS.items():
        for var, _ in prefs:
            other_creds.add(var)
    other_creds.discard(env_var)

    # Vertex providers (anthropic-vertex / google-vertex) need ADC
    # AND the project/location from the user. Keep those vars; strip
    # everything else.
    if pi_provider in ("anthropic-vertex", "google-vertex"):
        # Drop only the *other* family's direct keys.
        for var in other_creds:
            if var == "GOOGLE_APPLICATION_CREDENTIALS":
                continue
            env.pop(var, None)

        # Vertex endpoints are project-scoped: every URL is
        #   https://<region>-aiplatform.googleapis.com/v1/projects/<project>/...
        # so pi-ai literally can't form a request without a project.
        # In BYOK desktop almost no one sets GOOGLE_CLOUD_PROJECT
        # explicitly — they just point GOOGLE_APPLICATION_CREDENTIALS
        # at a service-account JSON. The JSON carries `project_id`,
        # so we lift it into the env. Without this auto-fill pi
        # silently hangs forever (no token stream, no error) which
        # was issue #3 from the 2026-05-08 desktop debug session.
        if not env.get("GOOGLE_CLOUD_PROJECT", "").strip():
            adc = env.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            if adc:
                project = _project_id_from_adc_json(adc)
                if project:
                    env["GOOGLE_CLOUD_PROJECT"] = project
                    print(
                        f"[byok] auto-filled GOOGLE_CLOUD_PROJECT={project!r} "
                        f"from GOOGLE_APPLICATION_CREDENTIALS",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "[byok] WARN: GOOGLE_CLOUD_PROJECT unset and the "
                        "credentials JSON has no project_id. Set "
                        "GOOGLE_CLOUD_PROJECT explicitly in ~/.digi-setu/.env "
                        "or the Vertex call will hang.",
                        file=sys.stderr,
                    )

        # Default the location to whatever config.VERTEX_DEFAULT_LOCATION
        # says (currently "global", matching scripts/env.sh line 41 —
        # web's source of truth). This is the SINGLE place that decides
        # the desktop's Vertex region; do not hard-code another literal
        # somewhere else. Setdefault so the user's shell or
        # ~/.digi-setu/.env can still override.
        from config import VERTEX_DEFAULT_LOCATION  # local import: avoid cycles
        env.setdefault("GOOGLE_CLOUD_LOCATION", VERTEX_DEFAULT_LOCATION)

        # Tell @google/genai to take the Vertex code path instead
        # of AI Studio. Without this, the SDK defaults to AI Studio
        # and ignores GOOGLE_CLOUD_PROJECT entirely.
        env["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

        # Patched pi-ai (`hasVertexAdcCredentials`) checks this flag
        # before falling back to its on-disk ADC heuristic. The
        # heuristic is meant for Cloud Run with metadata server;
        # on a laptop with a service-account JSON we want it to
        # trust the env-derived auth chain directly.
        env.setdefault("PI_TRUST_GCE_METADATA", "1")
    else:
        # Direct provider (anthropic / google / openai). Drop the
        # Vertex bits because they'd otherwise route through GCP
        # billing instead of the user's direct account.
        for var in other_creds:
            env.pop(var, None)
        env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        env.pop("GOOGLE_CLOUD_PROJECT", None)
        env.pop("GOOGLE_CLOUD_LOCATION", None)
        env.pop("GOOGLE_GENAI_USE_VERTEXAI", None)
        env.pop("PI_TRUST_GCE_METADATA", None)

    return env
