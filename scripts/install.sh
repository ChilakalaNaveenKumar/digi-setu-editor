#!/usr/bin/env bash
# Install pi-coding-agent + this project's extension deps.
# Run once after cloning, then again whenever package.json changes.

set -euo pipefail
cd "$(dirname "$0")/.."

# Install local extension deps (@google/genai, typebox, pi types) into ./node_modules
# so jiti resolves them when pi loads extensions/typst-tools.ts.
npm install --no-audit --no-fund

# Install pi globally so the `pi` command is on PATH.
# If the user prefers a per-user install, replace `-g` with `--prefix "$HOME/.local"`.
if ! command -v pi >/dev/null 2>&1; then
  echo "Installing @mariozechner/pi-coding-agent globally..."
  npm install -g @mariozechner/pi-coding-agent
fi

echo
echo "Versions:"
echo "  node:  $(node --version)"
echo "  typst: $(typst --version 2>/dev/null || echo 'NOT INSTALLED — brew install typst')"
echo "  pi:    $(pi --version 2>/dev/null || echo 'NOT INSTALLED')"
echo
echo "Now run:  scripts/run.sh"
