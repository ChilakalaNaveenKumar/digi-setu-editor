#!/usr/bin/env bash
# Stream a single pi -p turn with LIVE per-event output.
#
# Usage:
#   scripts/stream.sh "your prompt here"
#
# How it works:
#   1. pi -p --mode json emits one JSON object per line (start, deltas, tool
#      calls, results, end). Node block-buffers stdout when it's a pipe, so
#      we use `script -q /dev/null` to fake a TTY → events flush live.
#   2. jq prettifies each event into a one-liner you can actually read.
#   3. If `script` can't allocate a pty (e.g. non-interactive shell, CI) we
#      fall back to running pi -p directly. Output will only appear at the
#      end in that case — that's a Node limitation, not pi's.

set -uo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
source scripts/env.sh

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 \"<prompt>\"" >&2
  exit 2
fi
PROMPT="$*"

JQ_FILTER='
def shorten: if (type=="string") and (length>200) then .[0:200]+"…[+\(length-200)]" else . end;

if .type == "session"            then "▶ session   id=\(.id[0:8])  cwd=\(.cwd)"
elif .type == "agent_start"      then "▶ agent_start"
elif .type == "turn_start"       then "▶ turn_start"
elif .type == "message_start"    then "→ message  role=\(.message.role // "?")"
elif .type == "message_end"      then ((.message.usage // {}) as $u | "← message  in=\($u.input // 0) out=\($u.output // 0) cost=$\(($u.cost // {}).total // 0)")
elif .type == "tool_execution"   then "⚙ tool      name=\(.toolName // "?")  id=\(.toolCallId // "?" | tostring | .[0:8])"
elif .type == "tool_result"      then "✓ tool_done isError=\(.isError // false)  text=\((.content // []) | map(.text // "") | join(" ") | shorten)"
elif .type == "turn_end"         then "■ turn_end"
elif .type == "agent_end"        then "■ agent_end"
elif .type == "message_update" then
  (.assistantMessageEvent.type) as $t |
  if   $t == "text_delta"          then "  …text:  \(.assistantMessageEvent.delta // "" | shorten)"
  elif $t == "thinking_delta"      then "  …think: \(.assistantMessageEvent.delta // "" | shorten)"
  elif $t == "tool_call_start"     then "  ⚙ call_start  name=\(.assistantMessageEvent.toolName // "?")"
  elif $t == "tool_call_end"       then empty
  elif $t == "text_start"          then empty
  elif $t == "text_end"            then empty
  elif $t == "thinking_start"      then empty
  elif $t == "thinking_end"        then empty
  elif $t == "tool_call_input_delta" then empty
  else "  ·\($t // "?")"
  end
else "·\(.type // "?")"
end
'

run_pi() {
  pi -p \
    --mode json \
    --provider "$PI_PROVIDER" \
    --model "$PI_MODEL" \
    --extension ./extensions/typst-tools.ts \
    "$PROMPT" 2>&1
}

PI_OUTPUT_CMD=()
if [[ "$(uname)" == "Darwin" ]]; then
  if script -q /dev/null true </dev/tty 2>/dev/null; then
    PI_OUTPUT_CMD=(script -q /dev/null bash -c "pi -p --mode json --provider $PI_PROVIDER --model $PI_MODEL --extension ./extensions/typst-tools.ts \"\$1\"" -- "$PROMPT")
  fi
elif command -v script >/dev/null 2>&1; then
  PI_OUTPUT_CMD=(script -q -c "pi -p --mode json --provider $PI_PROVIDER --model $PI_MODEL --extension ./extensions/typst-tools.ts \"$PROMPT\"" /dev/null)
fi

# Filter out CR characters (script adds them on macOS) before piping into jq.
if [[ ${#PI_OUTPUT_CMD[@]} -gt 0 ]]; then
  "${PI_OUTPUT_CMD[@]}" | tr -d '\r' | (command -v jq >/dev/null 2>&1 && jq -r --unbuffered "$JQ_FILTER" || cat)
else
  echo "(no TTY available — pi -p output will arrive in one chunk at the end)" >&2
  run_pi | tr -d '\r' | (command -v jq >/dev/null 2>&1 && jq -r "$JQ_FILTER" || cat)
fi
