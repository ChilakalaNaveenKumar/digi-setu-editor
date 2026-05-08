#!/usr/bin/env bash
# End-to-end macOS release build.
#
# Produces:
#     desktop/src-tauri/target/release/bundle/dmg/Digi Setu_<version>_<arch>.dmg
#     desktop/src-tauri/target/release/bundle/macos/Digi Setu.app
#
# Order of operations:
#   1. Make sure Rust target for the host arch is installed.
#   2. Build the PyInstaller sidecar (desktop/backend → frozen binary).
#   3. Fetch + install bundled Node + pi-coding-agent (pi-runtime/vendor/).
#   4. Build the desktop frontend (desktop/frontend/dist/).
#   5. Run `tauri build` which assembles the .app + .dmg.
#
# We currently produce an UNSIGNED build per the v0.1 plan. To enable
# code signing + notarization later:
#   - Set TAURI_SIGNING_PRIVATE_KEY + TAURI_SIGNING_PRIVATE_KEY_PASSWORD
#     env vars, plus an Apple Developer ID via APPLE_CERTIFICATE +
#     APPLE_CERTIFICATE_PASSWORD + APPLE_ID + APPLE_ID_PASSWORD +
#     APPLE_TEAM_ID. The Tauri docs cover the full env list.
#   - Update tauri.conf.json's `bundle.macOS.signingIdentity` to your
#     Developer ID.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$(cd "$HERE/.." && pwd)"

ARCH="$(uname -m)"
case "$ARCH" in
    arm64)  TARGET="aarch64-apple-darwin" ;;
    x86_64) TARGET="x86_64-apple-darwin" ;;
    *) echo "Unknown Mac arch: $ARCH" >&2; exit 1 ;;
esac

echo "[release-mac] target = $TARGET"

# 1. Rust target — the first time this runs on a fresh Mac it pulls
# down the std library for the host triple. No-op afterwards.
if ! rustup target list --installed | grep -q "$TARGET"; then
    rustup target add "$TARGET"
fi

# 2. Sidecar (PyInstaller frozen FastAPI). Auto-creates
# desktop/backend/.venv on first run.
echo "[release-mac] building sidecar…"
bash "$DESKTOP/sidecar/build_sidecar.sh"

# 3. Bundled Node + pi-coding-agent. Already idempotent; skips
# re-download if the platform's tarball is already vendored.
echo "[release-mac] vendoring Node + pi…"
bash "$DESKTOP/pi-runtime/fetch-node.sh" --current-platform-only
bash "$DESKTOP/pi-runtime/install-pi.sh"

# 4. Frontend production build. tauri.conf.json's beforeBuildCommand
# re-runs this anyway, but doing it here surfaces frontend errors
# before the (slow) Rust release build kicks off.
echo "[release-mac] building frontend dist…"
( cd "$DESKTOP/frontend" && npm run build )

# 5. Tauri bundle.
echo "[release-mac] running tauri build…"
( cd "$DESKTOP" && npx tauri build --target "$TARGET" )

OUT_DMG="$DESKTOP/src-tauri/target/$TARGET/release/bundle/dmg"
OUT_APP="$DESKTOP/src-tauri/target/$TARGET/release/bundle/macos"

echo
echo "[release-mac] Done."
echo "  .app  → $OUT_APP"
echo "  .dmg  → $OUT_DMG"
ls -1 "$OUT_DMG" 2>/dev/null || true
