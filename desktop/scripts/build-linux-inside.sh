#!/usr/bin/env bash
# build-linux-inside.sh — runs INSIDE the digi-setu/linux-builder
# Docker image, with /workspace bind-mounted to the repo root.
#
# Why this exists separately from build-linux.sh:
#   build-linux.sh is the host-side wrapper that knows about Docker.
#   This script knows nothing about Docker; it just runs the build
#   steps in order, assuming every prereq is on PATH (which the
#   Dockerfile guarantees). That separation lets us also call this
#   directly from a CI runner if we ever wire up a hosted Linux
#   pipeline (Bitbucket Linux, GitHub Actions ubuntu-latest, etc.)
#   without dragging the Docker layer along.
#
# What it produces inside /workspace:
#   desktop/src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/
#       deb/Digi Setu_<version>_amd64.deb
#       appimage/Digi Setu_<version>_amd64.AppImage
#       rpm/digi-setu-<version>-1.x86_64.rpm    (when rpmbuild present)

set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────
WORKSPACE="${WORKSPACE:-/workspace}"
DESKTOP="$WORKSPACE/desktop"
TARGET="x86_64-unknown-linux-gnu"

cd "$DESKTOP"
echo "[linux-build] cwd: $(pwd)"
echo "[linux-build] arch: $(uname -m)"
echo "[linux-build] node: $(node --version)  npm: $(npm --version)"
echo "[linux-build] rust: $(rustc --version)  python: $(python3 --version)"

# ── 1. Sidecar (PyInstaller, fresh venv inside container) ────────────
# The host venv at desktop/backend/.venv was built against macOS
# Python; ignore it and build a Linux-only venv under /tmp/sidecar-venv
# so PyInstaller's bootloader links against the container's glibc.
# We DO NOT touch desktop/backend/.venv on the bind-mount — it stays
# usable for the dev's Mac terminal.
echo
echo "[linux-build] === sidecar (PyInstaller, in-container venv) ==="
SIDECAR_VENV="/tmp/sidecar-venv"
# Prefer python3.11 if installed (deadsnakes PPA in CI, Homebrew on
# laptops). Falling back to plain `python3` is the path that bit us
# on Bitbucket: ubuntu:22.04's default python3 is 3.10, and that
# image doesn't ship `python3.10-venv`, so `python3 -m venv` failed
# with "ensurepip is not available". The Dockerfile.linux-build
# image always has 3.11; the YAML's apt-get installs 3.11 + venv.
if command -v python3.11 >/dev/null 2>&1; then
    PY=python3.11
else
    PY=python3
fi
echo "[linux-build] sidecar python: $($PY --version)"
"$PY" -m venv "$SIDECAR_VENV"
# shellcheck disable=SC1091
source "$SIDECAR_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install --quiet -r "$DESKTOP/backend/requirements.txt"
python -m pip install --quiet "pyinstaller>=6.10,<7"

cd "$DESKTOP/sidecar"
python -m PyInstaller --clean --noconfirm pyinstaller.spec
DIST="$DESKTOP/sidecar/dist"
test -f "$DIST/pi-typst-sidecar" \
    || { echo "[linux-build] sidecar missing in $DIST" >&2; exit 1; }
cp "$DIST/pi-typst-sidecar" "$DIST/pi-typst-sidecar-${TARGET}"
chmod +x "$DIST/pi-typst-sidecar-${TARGET}"
echo "[linux-build] sidecar OK ($(du -h "$DIST/pi-typst-sidecar" | cut -f1))"
deactivate

# ── 2. Vendored Node + pi (Linux x64 tarball) ────────────────────────
# fetch-node.sh keeps an idempotent local cache; --current-platform-only
# avoids re-downloading the Mac/Win tarballs we already vendored.
echo
echo "[linux-build] === vendoring Linux Node + pi-coding-agent ==="
bash "$DESKTOP/pi-runtime/fetch-node.sh" --current-platform-only
bash "$DESKTOP/pi-runtime/install-pi.sh"

# ── 3. Third-party licenses ──────────────────────────────────────────
echo
echo "[linux-build] === regenerating THIRD_PARTY_LICENSES.txt ==="
node "$DESKTOP/scripts/gen-third-party-licenses.mjs"

# ── 4. Frontend dist ─────────────────────────────────────────────────
echo
echo "[linux-build] === frontend dist (vite) ==="
cd "$DESKTOP/frontend"
# CI installs are non-interactive; pass --no-audit/--no-fund so npm
# stops printing telemetry banners that bloat the build log.
npm install --no-audit --no-fund --prefer-offline
npm run build

# ── 5a. Refresh desktop node_modules for Linux native bindings ───────
# When this Dockerfile runs from a Mac dev's checkout, desktop/node_modules
# only contains @tauri-apps/cli-darwin-arm64 (or -x64) — npm installs the
# host's optionalDependencies entry only. Tauri's CLI then aborts with
# "Cannot find native binding" / "Cannot find module @tauri-apps/cli-
# linux-x64-gnu". Running `npm install` inside the container under the
# same node_modules tree is safe: npm sees the existing packages, then
# adds the missing platform's native binding alongside (different package
# names, no overwrite). The host's macOS binding stays put for the dev's
# next `npm run dev`.
echo
echo "[linux-build] === ensuring Linux tauri CLI binding is present ==="
cd "$DESKTOP"
npm install --no-audit --no-fund --prefer-offline --include=optional

# ── 5b. Tauri bundle (.deb [+ .AppImage]) ────────────────────────────
# The host wrapper passes the same env file we use for the macOS build
# so build.rs reads identical Clerk keys + cloud target URLs.
echo
echo "[linux-build] === tauri build (deb $( [[ "${LINUX_BUILD_APPIMAGE:-0}" = 1 ]] && echo '+ appimage' )) ==="
cd "$DESKTOP"
ENV_FILE="${TAURI_BUILD_ENV:-$DESKTOP/backend/.env}"
if [[ -f "$ENV_FILE" ]]; then
    echo "[linux-build] sourcing env from $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE" || true
    set +a
fi

# Tauri AppImage bundling needs APPIMAGETOOL_PATH so it skips its
# embedded download (which fails inside containers without /dev/fuse).
export APPIMAGETOOL_PATH="${APPIMAGETOOL_PATH:-/usr/local/bin/appimagetool}"
# Tauri's AppImage build inside a Docker container needs
# --appimage-extract-and-run because we don't have FUSE; the bundler
# wraps invocations automatically when this env var is set. The shims
# baked into /usr/local/bin/{appimagetool,linuxdeploy,...} also honour
# this when they delegate to the extracted AppRun payloads.
export APPIMAGE_EXTRACT_AND_RUN=1

# AppImage support is OFF by default because Tauri 2's bundler still
# downloads its own copy of `linuxdeploy.AppImage` to `target/<triple>/
# release/bundle/appimage/` and execs it directly. That ignores any
# PATH overrides we install, and the embedded copy can't run inside a
# container without FUSE. Until upstream gains a `LINUXDEPLOY_PATH`
# escape hatch (issue tracked in tauri-apps/tauri-bundler), .deb is
# the only artefact we ship from this script. .deb covers Ubuntu/
# Debian/Mint/Pop!_OS — easily 80 %+ of Linux desktop installs.
#
# To opt in (e.g. when running inside a privileged CI runner with
# /dev/fuse available), set LINUX_BUILD_APPIMAGE=1 before invoking
# build-linux.sh / release.sh.
BUNDLES="deb"
if [[ "${LINUX_BUILD_APPIMAGE:-0}" = 1 ]]; then
    BUNDLES="deb,appimage"
fi
npx tauri build --target "$TARGET" --bundles "$BUNDLES"

OUT_BASE="$DESKTOP/src-tauri/target/${TARGET}/release/bundle"
echo
echo "[linux-build] === artefacts (in container) ==="
ls -lah "$OUT_BASE/deb/" 2>/dev/null || true
ls -lah "$OUT_BASE/appimage/" 2>/dev/null || true

# The cargo target dir is a Docker named-volume overlay (see
# build-linux.sh: `-v digi-setu-cargo-target:.../target/x86_64...`).
# That volume is invisible to the host, so anything Tauri drops into
# it stays trapped after the container exits with `--rm`. Copy the
# bundles into the bind-mounted /workspace tree under a stable
# location the host wrapper looks at.
HOST_OUT="$DESKTOP/build-out/linux"
mkdir -p "$HOST_OUT/deb" "$HOST_OUT/appimage"
if compgen -G "$OUT_BASE/deb/*.deb" > /dev/null; then
    cp -f "$OUT_BASE"/deb/*.deb "$HOST_OUT/deb/"
fi
if compgen -G "$OUT_BASE/appimage/*.AppImage" > /dev/null; then
    cp -f "$OUT_BASE"/appimage/*.AppImage "$HOST_OUT/appimage/"
fi
echo "[linux-build] copied artefacts → $HOST_OUT (host-visible via bind mount)"
ls -lah "$HOST_OUT/deb/" 2>/dev/null || true
ls -lah "$HOST_OUT/appimage/" 2>/dev/null || true
echo "[linux-build] DONE."
