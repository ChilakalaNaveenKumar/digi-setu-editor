#!/usr/bin/env bash
# Launch pi interactively — TUI with live streaming, the way you actually use it.
#
# Usage:
#   scripts/run.sh                 # interactive TUI (LIVE progress)
#   scripts/run.sh "<prompt>"      # one-shot, streamed line-by-line via `script`
#                                  # (uses macOS/BSD `script` to fake a TTY so
#                                  # pi flushes its JSON events as they happen)

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
source scripts/env.sh

# ── Interactive: just exec pi. Its TUI handles streaming itself. ────────────
if [[ $# -eq 0 ]]; then
  exec pi \
    --provider "$PI_PROVIDER" \
    --model "$PI_MODEL" \
    --extension ./extensions/typst-tools.ts
fi

# ── One-shot with LIVE streaming via a fake TTY ─────────────────────────────
# `pi -p` is block-buffered when its stdout is a pipe (Node.js default).
# `script` (BSD/macOS variant) wraps the command in a pty so pi sees a TTY
# and flushes line-by-line. The `-q` suppresses script's start/done banners.
PROMPT="$*"
if [[ "$(uname)" == "Darwin" ]]; then
  exec script -q /dev/null pi -p \
    --provider "$PI_PROVIDER" \
    --model "$PI_MODEL" \
    --extension ./extensions/typst-tools.ts \
    "$PROMPT"
else
  # GNU script (Linux) has different flag order: -c CMD -q -O FILE
  exec script -q -c "pi -p --provider $PI_PROVIDER --model $PI_MODEL --extension ./extensions/typst-tools.ts \"$PROMPT\"" /dev/null
fi
