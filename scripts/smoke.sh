#!/usr/bin/env bash
# Non-interactive smoke test. Runs four prompts via `pi -p` and reports how
# each one went. Exit code is the count of failures (0 = all passed).
#
# Usage: scripts/smoke.sh
#
# Each test prompt exercises a different surface:
#   1. Tool listing             — does pi load the extension at all?
#   2. compile_typ              — does the compile loop work end to end?
#   3. search_docs (touying)    — does the corpus + Vertex Flash-Lite work?
#   4. Anti-hallucination       — does it actually call list_fonts before
#                                 picking a font?

set -uo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
source scripts/env.sh

if ! command -v pi >/dev/null 2>&1; then
  echo "pi is not on PATH. Run scripts/install.sh first." >&2
  exit 1
fi

LOG_DIR="logs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR"
echo "Logs: $LOG_DIR"

run_case() {
  local name="$1"
  local must_match="$2"
  local prompt="$3"
  local out="$LOG_DIR/${name}.log"

  echo
  echo "── $name ─────────────────────────────────────────────"
  echo "prompt: $prompt"
  echo
  if pi -p \
        --provider "$PI_PROVIDER" \
        --model "$PI_MODEL" \
        --extension ./extensions/typst-tools.ts \
        "$prompt" 2>&1 | tee "$out"; then
    if grep -qiE "$must_match" "$out"; then
      echo "PASS  ($name): matched /$must_match/"
      return 0
    else
      echo "FAIL  ($name): did not match /$must_match/"
      return 1
    fi
  else
    echo "FAIL  ($name): pi exited non-zero"
    return 1
  fi
}

fails=0

run_case "01_tools_loaded" \
  "compile_typ.*search_docs.*list_fonts|search_docs.*compile_typ.*list_fonts" \
  "List the four custom Typst tools you have available, just by name, comma-separated, on one line. Do not call any of them." \
  || fails=$((fails+1))

run_case "02_compile_loop" \
  "OK|wrote.*workspace/main\.pdf" \
  "Compile workspace/main.typ. Use compile_typ. If it errors, fix it and retry. Report the result in one line." \
  || fails=$((fails+1))

run_case "03_search_docs_touying" \
  "metropolis|touying-theme|show: metropolis-theme" \
  "Use search_docs with package=touying to find the minimal boilerplate to make a 3-slide deck using the metropolis theme. Just paste the boilerplate, no commentary." \
  || fails=$((fails+1))

run_case "04_anti_halluc_fonts" \
  "list_fonts|New Computer Modern|did not find" \
  "Suggest a serif font for a thesis. Before recommending one, you MUST call list_fonts to confirm it is installed. Then say which font you picked and why." \
  || fails=$((fails+1))

echo
echo "════════════════════════════════════════════════"
if [[ $fails -eq 0 ]]; then
  echo "ALL PASS (4/4)"
else
  echo "$fails / 4 cases failed. Logs in $LOG_DIR/"
fi
echo "════════════════════════════════════════════════"
exit "$fails"
