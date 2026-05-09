#!/usr/bin/env bash
# build-linux.sh — host-side wrapper that builds the Linux desktop
# artefacts (.deb + .AppImage) inside a Docker container.
#
# Why Docker:
#   - Tauri 2 on Linux needs GTK3 + WebKit2GTK 4.1 dev headers, which
#     don't exist on macOS. Cross-compiling without a real Linux
#     userland leads to broken webview links at runtime.
#   - PyInstaller binaries are OS-specific. The frozen sidecar must
#     be built on the SAME glibc + OpenSSL we ship to.
#   - Docker is already installed on every dev machine in the team
#     (we use it for cloud Compose), so this adds no new dep.
#
# Usage:
#   desktop/scripts/build-linux.sh                # build .deb + .AppImage
#   desktop/scripts/build-linux.sh --rebuild-image  # force-rebuild the image
#
# Outputs (mirrored back to the host via the bind mount):
#   desktop/src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/
#       deb/Digi Setu_<version>_amd64.deb
#       appimage/Digi Setu_<version>_amd64.AppImage
#
# The script writes a normalised copy alongside the macOS DMG output:
#   /tmp/Digi-Setu-<version>-amd64.deb
#   /tmp/Digi-Setu-<version>-amd64.AppImage
# so release.sh can hand these to upload-installer.sh without
# worrying about Tauri's quoting (Tauri puts a space in the filename).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$DESKTOP/.." && pwd)"

APP_VERSION="${APP_VERSION:-0.1.0}"
IMAGE_TAG="${LINUX_BUILDER_IMAGE:-digi-setu/linux-builder:latest}"
DOCKERFILE="${HERE}/Dockerfile.linux-build"
ENV_FILE="${TAURI_BUILD_ENV:-${DESKTOP}/backend/.env}"

REBUILD_IMAGE=0
for arg in "$@"; do
    case "$arg" in
        --rebuild-image) REBUILD_IMAGE=1 ;;
        -h|--help)
            sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) printf '[linux] unknown flag: %s\n' "$arg" >&2; exit 64 ;;
    esac
done

log() { printf '\033[1;34m[linux]\033[0m %s\n' "$*"; }

# ── 1. Preflight ─────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 \
    || { echo "[linux] docker not on PATH; install Docker Desktop" >&2; exit 1; }
docker info >/dev/null 2>&1 \
    || { echo "[linux] docker daemon not reachable; start Docker Desktop" >&2; exit 1; }

# ── 2. Ensure builder image is present (or rebuild on demand) ────────
if [[ ${REBUILD_IMAGE} -eq 1 ]] || ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    log "building image ${IMAGE_TAG} (this takes ~3-5 min on first run)"
    # Use the repo root as the build context so the Dockerfile can
    # reference any file in the tree if we ever add COPY directives.
    # Right now the image is purely a toolchain install — no project
    # files baked in — so it stays cacheable for weeks.
    docker build \
        --platform linux/amd64 \
        -f "${DOCKERFILE}" \
        -t "${IMAGE_TAG}" \
        "${REPO}"
else
    log "reusing image ${IMAGE_TAG} (pass --rebuild-image to force a refresh)"
fi

# ── 3. Run the in-container build ────────────────────────────────────
log "running in-container build (target: x86_64-unknown-linux-gnu)"
# Wire-through env file: build-linux-inside.sh sources it so build.rs
# inside the container picks up the same Clerk + cloud-target keys we
# bake into the macOS binary. Mounted read-only so a buggy build can't
# clobber the host's .env.
ENV_MOUNT_ARGS=()
if [[ -f "$ENV_FILE" ]]; then
    ENV_MOUNT_ARGS=(
        -v "${ENV_FILE}:/workspace/.env-build:ro"
        -e "TAURI_BUILD_ENV=/workspace/.env-build"
    )
    log "passing env file: $ENV_FILE → /workspace/.env-build (ro)"
else
    log "no env file at $ENV_FILE — build.rs will fall back to compiled defaults"
fi

# Cache the cargo registry + git index across runs (~30s saved on a
# warm rebuild; ~6 min saved on the first compile after a cold cache).
docker volume create digi-setu-cargo-cache >/dev/null
docker volume create digi-setu-cargo-target >/dev/null

docker run --rm \
    --platform linux/amd64 \
    -v "${REPO}:/workspace" \
    -v digi-setu-cargo-cache:/root/.cargo/registry \
    -v digi-setu-cargo-target:/workspace/desktop/src-tauri/target/x86_64-unknown-linux-gnu \
    "${ENV_MOUNT_ARGS[@]}" \
    -e "LINUX_BUILD_APPIMAGE=${LINUX_BUILD_APPIMAGE:-0}" \
    -w /workspace \
    "${IMAGE_TAG}" \
    bash /workspace/desktop/scripts/build-linux-inside.sh

# ── 4. Copy artefacts out with normalised filenames ──────────────────
# The container drops the bundles under desktop/build-out/linux/
# (a host-visible bind-mounted directory) because the cargo target
# dir lives in a Docker named volume that the host can't see. See
# the tail of build-linux-inside.sh for the copy step that puts
# them there.
BUNDLE_DIR="${DESKTOP}/build-out/linux"
DEB_SRC=$(ls "${BUNDLE_DIR}/deb/"*.deb 2>/dev/null | head -1 || true)
APPIMG_SRC=$(ls "${BUNDLE_DIR}/appimage/"*.AppImage 2>/dev/null | head -1 || true)

DEB_OUT="/tmp/Digi-Setu-${APP_VERSION}-amd64.deb"
APPIMG_OUT="/tmp/Digi-Setu-${APP_VERSION}-amd64.AppImage"

if [[ -n "${DEB_SRC}" ]]; then
    cp "${DEB_SRC}" "${DEB_OUT}"
    log "deb       → ${DEB_OUT}  ($(du -h "${DEB_OUT}" | cut -f1))"
else
    log "WARN: no .deb produced under ${BUNDLE_DIR}/deb/"
fi
if [[ -n "${APPIMG_SRC}" ]]; then
    cp "${APPIMG_SRC}" "${APPIMG_OUT}"
    chmod +x "${APPIMG_OUT}"
    log "AppImage  → ${APPIMG_OUT}  ($(du -h "${APPIMG_OUT}" | cut -f1))"
else
    log "WARN: no .AppImage produced under ${BUNDLE_DIR}/appimage/"
fi

log "done."
