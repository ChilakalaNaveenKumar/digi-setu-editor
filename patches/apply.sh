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
PATCHES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$PI_PKG_GLOBAL" ]]; then
  echo "ERROR: $PI_PKG_GLOBAL not found. Is pi installed globally?" >&2
  exit 1
fi

echo "── applying anthropic-vertex provider patch ──"
echo "  pi-coding-agent: $PI_PKG_GLOBAL"
echo "  patches dir    : $PATCHES_DIR"
echo

# 1) Install the SDK FIRST, before probing for pi-ai. npm install into
#    pi-coding-agent pulls in @mariozechner/pi-ai as a transitive
#    dependency, which can create a NESTED unpatched copy at
#    $PI_PKG_GLOBAL/node_modules/@mariozechner/pi-ai even if pi-ai was
#    previously hoisted. If we probe first and patch only the hoisted
#    copy, the npm install below silently produces a second unpatched
#    copy and pi loads THAT at runtime (Node prefers the nearest
#    ancestor's node_modules), making the patch effectively a no-op.
#    Symptom: `pi --list-models` returns google models only and
#    `--provider anthropic-vertex` errors with "Unknown provider".
if [[ ! -d "$PI_PKG_GLOBAL/node_modules/@anthropic-ai/vertex-sdk" ]]; then
  echo "→ installing @anthropic-ai/vertex-sdk into pi-coding-agent…"
  ( cd "$PI_PKG_GLOBAL" && npm install --no-save @anthropic-ai/vertex-sdk )
else
  echo "✓ @anthropic-ai/vertex-sdk already present"
fi

# 2) AFTER the install, probe for pi-ai. pi-ai can live in TWO places
#    depending on npm's hoisting + the install above:
#
#      NESTED   $PI_PKG_GLOBAL/node_modules/@mariozechner/pi-ai
#               — usually created by the npm install in step (1).
#      HOISTED  $(dirname $PI_PKG_GLOBAL)/pi-ai
#               — present from the original `npm install` of pi-coding-agent.
#
#    Both can exist simultaneously. We MUST patch all copies that exist,
#    because Node's resolver picks whichever is closest to the importer
#    and we can't reliably predict which one any given internal pi-ai
#    import will resolve to.
PI_AI_CANDIDATES=()
for candidate in \
    "$PI_PKG_GLOBAL/node_modules/@mariozechner/pi-ai" \
    "$(dirname "$PI_PKG_GLOBAL")/pi-ai"; do
  if [[ -d "$candidate/dist/providers" ]]; then
    PI_AI_CANDIDATES+=("$candidate")
  fi
done

if [[ ${#PI_AI_CANDIDATES[@]} -eq 0 ]]; then
  echo "ERROR: could not locate @mariozechner/pi-ai with a dist/providers/ subdir." >&2
  echo "       Searched:" >&2
  echo "         - $PI_PKG_GLOBAL/node_modules/@mariozechner/pi-ai" >&2
  echo "         - $(dirname "$PI_PKG_GLOBAL")/pi-ai" >&2
  exit 1
fi

echo "  pi-ai copies   : ${#PI_AI_CANDIDATES[@]}"
for p in "${PI_AI_CANDIDATES[@]}"; do echo "    - $p"; done
echo

# 3) Patch every pi-ai copy. Drop the new provider file, then run the
#    idempotent in-place edits via apply-edits.mjs.
for PI_AI in "${PI_AI_CANDIDATES[@]}"; do
  echo "→ patching $PI_AI"
  cp "$PATCHES_DIR/files/anthropic-vertex.js" "$PI_AI/dist/providers/anthropic-vertex.js"
  echo "  ✓ wrote dist/providers/anthropic-vertex.js"
  node "$PATCHES_DIR/apply-edits.mjs" "$PI_PKG_GLOBAL" "$PI_AI"
  echo
done

echo
echo "── done. smoke test: ──"
echo "  unset ANTHROPIC_API_KEY ANTHROPIC_OAUTH_TOKEN"
echo "  pi --provider anthropic-vertex --model claude-opus-4-7 -p 'say OK'"
