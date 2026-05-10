#!/usr/bin/env bash
# Install pi-coding-agent + the project's TypeScript extensions into a
# self-contained vendored tree under desktop/pi-runtime/vendor/.
#
# Layout produced:
#
#     vendor/pi/
#       package.json                     ← anchors the install
#       node_modules/
#         .bin/pi                        ← the CLI shim
#         @mariozechner/
#           pi-coding-agent/dist/...
#         @google/genai/                 ← deps for typst-tools.ts
#         typebox/
#         …
#     vendor/extensions/
#       typst-tools.ts                   ← copy of project root's
#       permission.ts                       extensions/, so absolute
#                                           paths in pi --extension
#                                           don't depend on the user's
#                                           picked folder layout.
#
# The desktop sidecar passes:
#     PI_DESKTOP_NODE_BIN  → the bundled Node 22 binary
#     PI_DESKTOP_PI_DIR    → vendor/pi (so pi_session.py can resolve
#                            node_modules/.bin/pi without a global
#                            install).
#
# pi_session.py reads those env vars and rewrites the spawn command
# to use the bundled runtime. See web/backend/services/pi_session.py
# `_build_subprocess_cmd` (added in Phase 2 of the desktop migration).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$HERE/vendor"
PROJECT_ROOT="$(cd "$HERE/../.." && pwd)"

mkdir -p "$VENDOR/pi"

# We use the bundled Node + the host's own npm to drive the install.
# This ensures we get a node_modules tree that matches the bundled
# Node's ABI (matters for any native deps pi might depend on).
host_platform=""
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)  host_platform="darwin-arm64" ;;
    Darwin-x86_64) host_platform="darwin-x64"   ;;
    Linux-x86_64)  host_platform="linux-x64"    ;;
    Linux-aarch64) host_platform="linux-arm64"  ;;
    *)             host_platform="darwin-arm64" ;;
esac
NODE_BIN="$VENDOR/node-$host_platform/bin/node"
NPM_BIN="$VENDOR/node-$host_platform/bin/npm"

if [[ ! -x "$NODE_BIN" || ! -f "$NPM_BIN" ]]; then
    echo "ERROR: bundled Node not found. Run scripts/fetch-node.sh first." >&2
    exit 1
fi

# Anchor file. We use a fixed package.json so the install is
# reproducible — if you bump the pi version, edit it here, not in
# `npm install` flags.
cat > "$VENDOR/pi/package.json" <<'EOF'
{
  "name": "pi-runtime-bundle",
  "version": "0.1.0",
  "private": true,
  "description": "Vendored install of pi-coding-agent + typst-tools deps for Digi Setu desktop.",
  "dependencies": {
    "@mariozechner/pi-coding-agent": "*",
    "@anthropic-ai/vertex-sdk": "^0.16.0",
    "@google/genai": "^1.0.0",
    "typebox": "^1.1.24",
    "tsx": "^4.21.0"
  }
}
EOF

echo "[pi-runtime] installing pi-coding-agent + extension deps…"
cd "$VENDOR/pi"
"$NODE_BIN" "$NPM_BIN" install --no-audit --no-fund

# Sanity-check.
if [[ ! -x "$VENDOR/pi/node_modules/.bin/pi" ]]; then
    echo "ERROR: vendor/pi/node_modules/.bin/pi missing after install" >&2
    ls "$VENDOR/pi/node_modules/.bin" 2>/dev/null >&2 || true
    exit 1
fi

# Copy the project's TypeScript extensions into the vendored tree so
# `pi --extension /abs/path/typst-tools.ts` works no matter what
# folder the user picked. We don't symlink because the bundler can't
# follow symlinks across drives on Windows.
mkdir -p "$VENDOR/extensions"
cp -R "$PROJECT_ROOT/extensions/." "$VENDOR/extensions/"

# Apply the project's pi-ai patches. These add the `anthropic-vertex`
# and `google-vertex` providers (Vertex AI hosts both Anthropic and
# Google models) which our `services.byok` routing assumes are
# available. Without these patches a freshly-vendored pi-ai rejects
# `--provider anthropic-vertex` with "Unknown provider", which is what
# we hit on the first run after a clean fork.
#
# The patcher is idempotent (sentinel-guarded), so re-running this
# script after a pi-coding-agent version bump just no-ops the patches
# that already took effect.
PI_PKG="$VENDOR/pi/node_modules/@mariozechner/pi-coding-agent"
PI_AI="$VENDOR/pi/node_modules/@mariozechner/pi-ai"
if [[ -d "$PI_PKG" && -d "$PI_AI" ]]; then
    echo "[pi-runtime] dropping anthropic-vertex provider source…"
    # apply-edits.mjs registers a lazy `import("./anthropic-vertex.js")`
    # in register-builtins.js but the actual provider source file is
    # not part of upstream pi-ai — it lives only in our patches/ tree.
    # Without this copy, importing `anthropic-vertex` at runtime throws
    # MODULE_NOT_FOUND, which crashes the spawned pi BEFORE it makes any
    # LLM call. Symptom on the desktop: the chat hangs forever on
    # "streaming…" because pi exits silently and there is no further
    # WS traffic. apply.sh (the standalone reapply script) already does
    # this; we just mirror it in install-pi.sh so the bundled DMG ships
    # a complete provider tree without depending on a manual step.
    cp "$PROJECT_ROOT/patches/files/anthropic-vertex.js" \
        "$PI_AI/dist/providers/anthropic-vertex.js"
    echo "[pi-runtime] applying pi-ai patches (vertex providers + GCE-metadata trust)…"
    "$NODE_BIN" "$PROJECT_ROOT/patches/apply-edits.mjs" "$PI_PKG" "$PI_AI"
else
    echo "[pi-runtime] WARNING: pi-coding-agent or pi-ai dir missing — patches not applied" >&2
    echo "             pi_pkg=$PI_PKG"
    echo "             pi_ai=$PI_AI"
fi

# Stage the patch SOURCE files alongside the install so the sidecar
# can self-heal at runtime. This is the safety net for two scenarios
# we actually see in the wild:
#
#   1. The bundled `node_modules/@mariozechner/pi-ai/dist/providers/
#      anthropic-vertex.js` gets stripped or rewritten by something
#      outside our control — e.g. a future `pi update` that runs
#      against the bundled tree, or a sysadmin reinstalling a global
#      pi-coding-agent on top of (or around) the app bundle.
#   2. A bad merge or a botched manual edit silently drops the
#      `_isLocalRelayBaseUrl` shim, which the SDK needs to skip the
#      GoogleAuth dance on a laptop without ADC.
#
# In either case, before this change the user's chat would fail
# silently — pi would either crash importing the provider, or hang
# on the GCE metadata server while we showed an empty "streaming…"
# pill. After this change the sidecar (see services/pi_integrity.py)
# detects the drift on boot, copies the canonical patch back into
# place, and pi works again. If the staged source itself is missing
# (corrupted bundle), the sidecar logs a clear setup_required error
# and the chat dispatcher refuses cloud-relay sessions instead of
# letting them silent-fail.
echo "[pi-runtime] staging patch sources for runtime self-heal…"
mkdir -p "$VENDOR/patches/files"
cp "$PROJECT_ROOT/patches/files/anthropic-vertex.js" \
    "$VENDOR/patches/files/anthropic-vertex.js"
# Stage apply-edits.mjs as well so a corrupted register-builtins.js
# (the OTHER half of the anthropic-vertex install) can be reapplied
# without rerunning the whole npm install.
cp "$PROJECT_ROOT/patches/apply-edits.mjs" \
    "$VENDOR/patches/apply-edits.mjs"

echo "[pi-runtime] pi installed at $VENDOR/pi/node_modules/.bin/pi"
echo "[pi-runtime] extensions copied to $VENDOR/extensions/"
echo "[pi-runtime] patch sources staged at $VENDOR/patches/"
"$NODE_BIN" "$VENDOR/pi/node_modules/.bin/pi" --version || true
echo "[pi-runtime] install complete."
