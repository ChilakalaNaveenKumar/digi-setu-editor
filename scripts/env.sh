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
  # IMPORTANT: we deliberately DO NOT import TYPST_AGENT_ROUTER_MODEL or
  # TYPST_AGENT_COMPACT_MODEL anymore. The legacy typst-agent .env points
  # those at gemini-3.1-flash-lite-preview, which would silently leak
  # into PI_TYPST_ROUTER_MODEL via the fallback chain below and degrade
  # search_docs answers (Flash-Lite hand-waves on niche packages).
  # search_docs defaults to gemini-3-flash-preview (set on line 78 below
  # and in deploy/docker-compose.yml) — Gemini 3 Flash has a 1M context
  # window which fits the ~210k-token core Typst corpus comfortably. The
  # right place to override the default is web/backend/.env, not the
  # legacy typst-agent file.
  while IFS='=' read -r key value; do
    case "$key" in
      ""|\#*) continue ;;
      GOOGLE_GENAI_USE_VERTEXAI|GOOGLE_CLOUD_PROJECT|GOOGLE_CLOUD_LOCATION|TYPST_AGENT_MODEL)
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

# ── Custom typst fonts ─────────────────────────────────────────────────────
# Typst auto-discovers fonts from $TYPST_FONT_PATHS (colon-separated). We
# bundle ~80 professional fonts in web/backend/fonts/ so the agent can
# recommend Inter / Lato / Merriweather / FiraCode / Font Awesome / Symbols
# Nerd / etc. without depending on the host having them installed. Without
# this export, `typst compile` silently substitutes Linux Libertine for
# everything and the doc looks wrong.
PI_TYPST_FONTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)/web/backend/fonts"
if [[ -d "$PI_TYPST_FONTS_DIR" ]]; then
  if [[ -z "${TYPST_FONT_PATHS:-}" ]]; then
    export TYPST_FONT_PATHS="$PI_TYPST_FONTS_DIR"
  elif [[ ":${TYPST_FONT_PATHS}:" != *":${PI_TYPST_FONTS_DIR}:"* ]]; then
    export TYPST_FONT_PATHS="${PI_TYPST_FONTS_DIR}:${TYPST_FONT_PATHS}"
  fi
fi
unset PI_TYPST_FONTS_DIR

# ── Map typst-agent model names → pi env vars ─────────────────────────────
# search_docs uses PI_TYPST_ROUTER_MODEL (read inside typst-tools.ts).
# DEFAULT: gemini-3-flash-preview on Vertex.
#
# Why not Haiku 4.5 anymore: the core Typst corpus (`reference/` + `tutorial/`
# + `guides/`) is ~210k tokens, which exceeds Haiku's 200k context window
# and blows up search_docs("typst", …) with a 400. The third-party package
# corpora (cetz, codly, fletcher, …) all fit comfortably, but we don't want
# the agent's first instinct — "look up base Typst" — to be a guaranteed
# failure. Gemini 3 Flash has a 1M context window and costs roughly 6× less
# per million output tokens than Haiku, and Vertex Gemini does implicit
# prefix caching so repeated lookups still get a discount.
#
# We INTENTIONALLY do not chain through TYPST_AGENT_ROUTER_MODEL. The legacy
# typst-agent .env still points that var at Flash-Lite (old, smaller model)
# for backwards-compat with the ADK agent. If you want a different router
# model, override PI_TYPST_ROUTER_MODEL directly in web/backend/.env or your
# shell.
export PI_TYPST_ROUTER_MODEL="${PI_TYPST_ROUTER_MODEL:-gemini-3-flash-preview}"

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
  echo "── digi-setu env ──"
  echo "  GOOGLE_CLOUD_PROJECT  = $GOOGLE_CLOUD_PROJECT"
  echo "  GOOGLE_CLOUD_LOCATION = $GOOGLE_CLOUD_LOCATION"
  echo "  PI_PROVIDER           = $PI_PROVIDER"
  echo "  PI_MODEL              = $PI_MODEL"
  echo "  PI_TYPST_ROUTER_MODEL     = $PI_TYPST_ROUTER_MODEL"
  echo "  PI_TYPST_WEB_SEARCH_MODEL = $PI_TYPST_WEB_SEARCH_MODEL"
fi
