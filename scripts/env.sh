#!/usr/bin/env bash
# Source this file to set the env pi expects.
#
# Order of precedence:
#   1. Anything you exported BEFORE sourcing this file (we never overwrite).
#   2. The typst-agent's own .env (../refernecs/typst-agent/backend/.env)
#      so pi runs against the *exact* same Vertex project / location / models
#      as your existing ADK agent — no drift.
#   3. The defaults at the bottom (only fire if .env is missing too).

# ── Pull from typst-agent .env (single source of truth) ────────────────────
TYPST_AGENT_ENV="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)/../refernecs/typst-agent/backend/.env"

if [[ -f "$TYPST_AGENT_ENV" ]]; then
  while IFS='=' read -r key value; do
    case "$key" in
      ""|\#*) continue ;;
      GOOGLE_GENAI_USE_VERTEXAI|GOOGLE_CLOUD_PROJECT|GOOGLE_CLOUD_LOCATION|TYPST_AGENT_MODEL|TYPST_AGENT_ROUTER_MODEL|TYPST_AGENT_COMPACT_MODEL)
        value="${value%\"}"; value="${value#\"}"
        value="${value%\'}"; value="${value#\'}"
        existing="$(printenv "$key" 2>/dev/null || true)"
        if [[ -z "$existing" ]]; then
          export "$key=$value"
        fi
        ;;
    esac
  done < "$TYPST_AGENT_ENV"
fi

# ── Defaults (fire only if neither your shell nor the .env set them) ──────
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-true}"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-frontend-472812}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"

# ── Map typst-agent model names → pi env vars ─────────────────────────────
# search_docs uses PI_TYPST_ROUTER_MODEL (read inside typst-tools.ts).
# DEFAULT: claude-haiku-4-5 on Vertex. Costs ~10× more per call than the old
# Gemini Flash Lite default, but gets ~90% off via Anthropic prompt caching
# on follow-up lookups (the corpus block is marked `cache_control: ephemeral`),
# AND gives substantially better answers for "explain how this codly/touying
# feature actually works" — which Flash-Lite often hand-waves on.
# To revert to Flash-Lite for cost: `export PI_TYPST_ROUTER_MODEL=gemini-3.1-flash-lite-preview`.
export PI_TYPST_ROUTER_MODEL="${PI_TYPST_ROUTER_MODEL:-${TYPST_AGENT_ROUTER_MODEL:-claude-haiku-4-5}}"

# style_guide uses PI_TYPST_DESIGN_MODEL (read inside typst-tools.ts).
# Flash by default — fast & cheap (~$0.015 per design call). If outputs come
# back generic / the agent keeps reaching for the same palette, flip to Pro
# either globally (export below) or per-call (pass model="gemini-3.1-pro-preview"
# into style_guide).
export PI_TYPST_DESIGN_MODEL="${PI_TYPST_DESIGN_MODEL:-gemini-3-flash-preview}"

# web_search uses PI_TYPST_WEB_SEARCH_MODEL. 2.5-flash bills grounding per
# *prompt* (predictable). The 3.x series bills per *query* and Gemini fans one
# brief out into 4-5 searches → costs explode. Stick with 2.5-flash unless
# your project's IAM blocks it.
export PI_TYPST_WEB_SEARCH_MODEL="${PI_TYPST_WEB_SEARCH_MODEL:-gemini-2.5-flash}"

# pi's main agent model (passed via --model on the command line).
#
# To switch the brain to Claude Opus 4.7 on Vertex (patched provider
# `anthropic-vertex` — see patches/PATCH.md):
#   export PI_PROVIDER=anthropic-vertex
#   export PI_MODEL=claude-opus-4-7
#   export PI_VERTEX_ANTHROPIC_LOCATION=global   # opus-4-7 GA region
# All three Anthropic-on-Vertex models reuse GOOGLE_CLOUD_PROJECT + ADC.
export PI_MODEL="${PI_MODEL:-${TYPST_AGENT_MODEL:-gemini-3.1-pro-preview-customtools}}"
export PI_PROVIDER="${PI_PROVIDER:-google-vertex}"

# When PI_PROVIDER=anthropic-vertex, anchor the location to "global" because
# claude-opus-4-7 is only GA in that region today (see patches/PATCH.md).
if [[ "$PI_PROVIDER" == "anthropic-vertex" ]]; then
  export PI_VERTEX_ANTHROPIC_LOCATION="${PI_VERTEX_ANTHROPIC_LOCATION:-global}"
fi

# ── Sanity ─────────────────────────────────────────────────────────────────
if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  echo "WARNING: GOOGLE_CLOUD_PROJECT is not set." >&2
fi

if [[ "${PI_TYPST_ENV_VERBOSE:-0}" == "1" ]]; then
  echo "── pi-typst-test env ──"
  echo "  GOOGLE_CLOUD_PROJECT  = $GOOGLE_CLOUD_PROJECT"
  echo "  GOOGLE_CLOUD_LOCATION = $GOOGLE_CLOUD_LOCATION"
  echo "  PI_PROVIDER           = $PI_PROVIDER"
  echo "  PI_MODEL              = $PI_MODEL"
  echo "  PI_TYPST_ROUTER_MODEL     = $PI_TYPST_ROUTER_MODEL"
  echo "  PI_TYPST_DESIGN_MODEL     = $PI_TYPST_DESIGN_MODEL"
  echo "  PI_TYPST_WEB_SEARCH_MODEL = $PI_TYPST_WEB_SEARCH_MODEL"
fi
