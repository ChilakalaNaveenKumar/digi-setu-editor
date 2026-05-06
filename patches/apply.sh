#!/usr/bin/env bash
# patches/apply.sh — Reapply the `anthropic-vertex` provider patch after
# `pi update` (or any reinstall of @mariozechner/pi-coding-agent).
#
# Usage:
#   bash patches/apply.sh
#
# Idempotent: each StrReplace below is a no-op once already applied; the
# script will refuse cleanly if a target file is missing.

set -euo pipefail

PI_PKG_GLOBAL="${PI_PKG_GLOBAL:-$(npm root -g)/@mariozechner/pi-coding-agent}"
PI_AI="$PI_PKG_GLOBAL/node_modules/@mariozechner/pi-ai"
PATCHES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$PI_PKG_GLOBAL" ]]; then
  echo "ERROR: $PI_PKG_GLOBAL not found. Is pi installed globally?" >&2
  exit 1
fi
if [[ ! -d "$PI_AI/dist/providers" ]]; then
  echo "ERROR: $PI_AI/dist/providers not found." >&2
  exit 1
fi

echo "── applying anthropic-vertex provider patch ──"
echo "  pi-coding-agent: $PI_PKG_GLOBAL"
echo "  pi-ai          : $PI_AI"
echo "  patches dir    : $PATCHES_DIR"
echo

# 1) Install the SDK if missing.
if [[ ! -d "$PI_PKG_GLOBAL/node_modules/@anthropic-ai/vertex-sdk" ]]; then
  echo "→ installing @anthropic-ai/vertex-sdk into pi-coding-agent…"
  ( cd "$PI_PKG_GLOBAL" && npm install --no-save @anthropic-ai/vertex-sdk )
else
  echo "✓ @anthropic-ai/vertex-sdk already present"
fi

# 2) Drop the new provider file.
cp "$PATCHES_DIR/files/anthropic-vertex.js" "$PI_AI/dist/providers/anthropic-vertex.js"
echo "✓ wrote dist/providers/anthropic-vertex.js"

# 3) Patch the existing files in-place via a Node helper that does idempotent
#    string replacements. Stops at first applied match.
node "$PATCHES_DIR/apply-edits.mjs" "$PI_PKG_GLOBAL"

echo
echo "── done. smoke test: ──"
echo "  unset ANTHROPIC_API_KEY ANTHROPIC_OAUTH_TOKEN"
echo "  pi --provider anthropic-vertex --model claude-opus-4-7 -p 'say OK'"
