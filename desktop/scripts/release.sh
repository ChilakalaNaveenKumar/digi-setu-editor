#!/usr/bin/env bash
# release.sh — one-command end-to-end desktop release pipeline.
#
# What it does, in order, FOR EVERY ENABLED PLATFORM:
#   1.  Preflight: every binary the build needs (rust, npm, codesign,
#       create-dmg, gcloud, docker) is on PATH; we also check the
#       current gcloud auth and the target macOS arch.
#   2.  Fetch Clerk + cloud-target env vars from Google Secret Manager
#       (project: digi-setu-dev) into a TEMP file. Falls back to
#       desktop/backend/.env when GSM access fails — so this script
#       still works on a dev laptop without GCP access. The same env
#       file is bind-mounted into the Linux Docker builder so build.rs
#       inside the container picks up identical Clerk keys.
#   3.  Rebuild app icons from the source vector so every platform
#       ships a sharp multi-resolution .icns / .ico. Without this the
#       macOS dock auto-downscales the single 1024px PNG and the
#       result looks blurry. Pass --skip-icons to reuse what's on disk.
#   4.  macOS path (when --mac or --all):
#       a. PyInstaller sidecar (host-arch frozen FastAPI)
#       b. Vendor Node + pi-coding-agent (desktop/pi-runtime/vendor/)
#       c. Regenerate THIRD_PARTY_LICENSES.txt
#       d. npm install + Vite frontend dist
#       e. tauri build --target <host arch> --bundles app
#       f. Deep ad-hoc sign
#       g. create-dmg with drag-to-Applications layout
#       h. Upload to digi-setu.com/downloads/ via upload-installer.sh
#   5.  Linux path (when --linux or --all):
#       a. Build (or reuse) the digi-setu/linux-builder Docker image
#       b. Run build-linux-inside.sh inside the container — fresh
#          PyInstaller venv, vendored Linux Node, frontend, then
#          tauri build --bundles deb,appimage
#       c. Copy artefacts out with normalised filenames
#       d. Upload both .deb and .AppImage
#   6.  Smoke-test: each public URL is reachable and matches our
#       local sha256.
#
# Windows path is intentionally separate (build-windows.ps1) — that
# script must run on Windows, so this Mac-side pipeline can't drive
# it. CI handles cross-platform Windows builds; see
# .github/workflows/release.yml or run build-windows.ps1 manually.
#
# Idempotent: rerunning produces a fresh build with a fresh upload.
# The temp env file is wiped via `trap EXIT` so we never leave Clerk
# secrets on disk after we're done.
#
# Usage:
#   desktop/scripts/release.sh                # default: --mac
#   desktop/scripts/release.sh --linux        # Linux .deb + .AppImage
#   desktop/scripts/release.sh --all          # mac + linux
#   desktop/scripts/release.sh --no-upload    # local artefacts only
#   desktop/scripts/release.sh --skip-sidecar # reuse existing sidecar dist
#   desktop/scripts/release.sh --skip-icons   # don't rebuild icons
#   desktop/scripts/release.sh --local-env    # bypass GSM, use local .env
#   desktop/scripts/release.sh --dmg-only     # rebuild + reupload Mac DMG
#                                                from existing .app
#
# Env overrides:
#   APP_VERSION   default 0.1.0       — used in artefact filenames
#   GCP_PROJECT   default digi-setu-dev
#   DMG_NAME      default Digi-Setu-${APP_VERSION}-${ARCH}.dmg

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$DESKTOP/.." && pwd)"

APP_VERSION="${APP_VERSION:-0.1.0}"
GCP_PROJECT="${GCP_PROJECT:-digi-setu-dev}"

ARCH="$(uname -m)"
case "$ARCH" in
    arm64)  TARGET="aarch64-apple-darwin"; DMG_ARCH="arm64" ;;
    x86_64) TARGET="x86_64-apple-darwin";  DMG_ARCH="x86_64" ;;
    *) printf '[release] unsupported arch: %s\n' "$ARCH" >&2; exit 1 ;;
esac

DMG_NAME="${DMG_NAME:-Digi-Setu-${APP_VERSION}-${DMG_ARCH}.dmg}"
APP_PATH="${DESKTOP}/src-tauri/target/${TARGET}/release/bundle/macos/Digi Setu.app"
DMG_OUT="/tmp/${DMG_NAME}"

LINUX_DEB_OUT="/tmp/Digi-Setu-${APP_VERSION}-amd64.deb"
LINUX_APPIMG_OUT="/tmp/Digi-Setu-${APP_VERSION}-amd64.AppImage"

# Parse flags.
NO_UPLOAD=0
SKIP_SIDECAR=0
SKIP_ICONS=0
LOCAL_ENV=0
DMG_ONLY=0
DO_MAC=0
DO_LINUX=0
for arg in "$@"; do
    case "$arg" in
        --no-upload)    NO_UPLOAD=1 ;;
        --skip-sidecar) SKIP_SIDECAR=1 ;;
        --skip-icons)   SKIP_ICONS=1 ;;
        --local-env)    LOCAL_ENV=1 ;;
        --dmg-only)     DMG_ONLY=1; DO_MAC=1 ;;
        --mac)          DO_MAC=1 ;;
        --linux)        DO_LINUX=1 ;;
        --all)          DO_MAC=1; DO_LINUX=1 ;;
        -h|--help)
            sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            printf '[release] unknown flag: %s\n' "$arg" >&2
            exit 64
            ;;
    esac
done

# Default: build mac when no platform flag was passed.
if [[ ${DO_MAC} -eq 0 && ${DO_LINUX} -eq 0 ]]; then
    DO_MAC=1
fi

# ── Helpers ───────────────────────────────────────────────────────
banner() {
    printf '\n\033[1;36m=== [%s] %s ===\033[0m\n' "$(date +%H:%M:%S)" "$*"
}
log()  { printf '\033[1;34m[release]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[release]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[release]\033[0m %s\n' "$*" >&2; exit 1; }

ENV_TMP=""
cleanup() {
    [[ -n "${ENV_TMP}" && -f "${ENV_TMP}" ]] && rm -f "${ENV_TMP}"
}
trap cleanup EXIT

# ── 1. Preflight ─────────────────────────────────────────────────
preflight() {
    banner "preflight"
    local missing=()
    # Always-needed tools.
    for bin in rustup cargo npm node python3; do
        command -v "$bin" >/dev/null 2>&1 || missing+=("$bin")
    done
    if [[ ${DO_MAC} -eq 1 ]]; then
        for bin in codesign create-dmg; do
            command -v "$bin" >/dev/null 2>&1 || missing+=("$bin")
        done
    fi
    if [[ ${DO_LINUX} -eq 1 ]]; then
        command -v docker >/dev/null 2>&1 || missing+=("docker")
    fi
    if [[ ${LOCAL_ENV} -eq 0 || ${NO_UPLOAD} -eq 0 ]]; then
        command -v gcloud >/dev/null 2>&1 || missing+=("gcloud")
    fi
    if [[ ${#missing[@]} -gt 0 ]]; then
        fail "missing required tools: ${missing[*]}
Install hints:
  brew install create-dmg librsvg
  brew install --cask docker
  curl https://sh.rustup.rs -sSf | sh
  brew install --cask google-cloud-sdk
  pip3 install Pillow"
    fi

    # macOS-only: docker daemon reachable check.
    if [[ ${DO_LINUX} -eq 1 ]]; then
        docker info >/dev/null 2>&1 \
            || fail "docker daemon not reachable; start Docker Desktop"
    fi

    if [[ ${DO_MAC} -eq 1 ]]; then
        if ! rustup target list --installed | grep -q "$TARGET"; then
            log "installing rust target ${TARGET}"
            rustup target add "$TARGET"
        fi
    fi

    if [[ ${LOCAL_ENV} -eq 0 ]]; then
        local active
        active=$(gcloud config get-value account 2>/dev/null || true)
        [[ -n "${active}" ]] || fail "no active gcloud account; run 'gcloud auth login'"
        log "gcloud account: ${active}"
    fi

    log "platforms: mac=${DO_MAC}  linux=${DO_LINUX}"
    log "host arch: ${ARCH} → mac target: ${TARGET}"
    log "version  : ${APP_VERSION}"
    [[ ${DO_MAC}   -eq 1 ]] && log "  -> ${DMG_NAME}"
    [[ ${DO_LINUX} -eq 1 ]] && log "  -> $(basename "${LINUX_DEB_OUT}") + $(basename "${LINUX_APPIMG_OUT}")"
    # Explicit success: under `set -e`, a function whose last command
    # is a `[[ … ]] && cmd` returns the test's exit status (1 when the
    # condition is false), which would silently abort the whole
    # release right after the preflight banner. We've verified the
    # tools we care about above; nothing left to check.
    return 0
}

# ── 2. Fetch secrets ─────────────────────────────────────────────
fetch_secrets() {
    banner "fetch secrets"
    # Place the temp env file inside the repo because Docker Desktop
    # on macOS only bind-mounts paths under VirtioFS-shared roots
    # (typically /Users, /private/tmp, /Volumes). The default macOS
    # TMPDIR (/var/folders/...) is NOT shared and Docker errors out
    # with "mountpoint is outside of rootfs". Putting the file under
    # the repo (already bind-mounted at /workspace) makes it visible
    # to the Linux container at a deterministic path.
    ENV_TMP="${REPO_ROOT}/.release-secrets.tmp.env"
    : > "${ENV_TMP}"
    chmod 0600 "${ENV_TMP}"
    if [[ ${LOCAL_ENV} -eq 1 ]]; then
        log "--local-env set, copying desktop/backend/.env"
        cp "${DESKTOP}/backend/.env" "${ENV_TMP}"
        return 0
    fi
    log "pulling Clerk + cloud-target keys from GSM project ${GCP_PROJECT}"
    # Keys the Tauri build.rs reads via cargo:rustc-env. Production
    # tenant takes precedence — we still pull the test-tenant pair
    # for a developer who runs the same binary against a local
    # FastAPI configured with the test tenant.
    local pulled=0 missing=0
    for key in CLERK_PUBLISHABLE_KEY_PROD CLERK_SECRET_KEY_PROD; do
        local v
        v=$(gcloud secrets versions access latest \
                --project "${GCP_PROJECT}" \
                --secret "${key}" 2>/dev/null || true)
        if [[ -z "${v}" ]]; then
            missing=$((missing + 1))
            warn "GSM missing: ${key}"
        else
            printf '%s=%s\n' "${key}" "${v}" >> "${ENV_TMP}"
            pulled=$((pulled + 1))
        fi
    done
    # Cloud-target overrides — never secrets, but keeping them in the
    # same env file means the Rust build picks them up too.
    #
    # CRITICAL: PI_CLOUD_API_BASE is the apex (digi-setu.com), NOT the
    # api subdomain. cloud_api.py builds URLs like ${base}/api/usage and
    # the /api/* routes only exist on the apex. The api subdomain only
    # serves /v1/* (which is what PI_RELAY_BASE points at — that's
    # the WebSocket relay). Mixing them up turns every billing/usage/
    # workspace call into a 404 and the desktop UI shows
    # "Something went wrong reaching the cloud chat service" + an
    # offline-looking credit chip even though the user is signed in.
    {
        printf 'PI_CLOUD_API_BASE=%s\n' "${PI_CLOUD_API_BASE:-https://digi-setu.com}"
        printf 'PI_RELAY_BASE=%s\n'     "${PI_RELAY_BASE:-https://api.digi-setu.com}"
        printf 'CLERK_TENANT=%s\n'      "${CLERK_TENANT:-prod}"
    } >> "${ENV_TMP}"
    log "pulled ${pulled} secrets from GSM (${missing} missing)"
    if [[ ${pulled} -eq 0 ]]; then
        warn "no GSM secrets pulled; falling back to desktop/backend/.env"
        cp "${DESKTOP}/backend/.env" "${ENV_TMP}"
    fi
}

# ── 3. Icons (rebuild from vector source) ─────────────────────────
rebuild_icons() {
    [[ ${SKIP_ICONS} -eq 1 ]] && { log "--skip-icons set, reusing existing icons/"; return 0; }
    [[ ${DMG_ONLY}   -eq 1 ]] && return 0
    banner "rebuild app icons"
    # Pillow is the only hard dep — install on demand into the user's
    # python3 if it's missing, so a clean Mac doesn't trip preflight.
    if ! python3 -c 'import PIL' 2>/dev/null; then
        log "installing Pillow for the icon pipeline"
        pip3 install --quiet Pillow
    fi
    python3 "${HERE}/build-icons.py"
}

# ── 4. macOS pipeline ─────────────────────────────────────────────
build_sidecar_mac() {
    [[ ${SKIP_SIDECAR} -eq 1 ]] && { log "--skip-sidecar set, reusing existing sidecar"; return 0; }
    [[ ${DMG_ONLY} -eq 1 ]] && return 0
    banner "macOS · build sidecar (PyInstaller)"
    bash "${DESKTOP}/sidecar/build_sidecar.sh"
}

vendor_pi_runtime_mac() {
    [[ ${DMG_ONLY} -eq 1 ]] && return 0
    banner "macOS · vendor Node + pi-coding-agent"
    # Idempotent on a dev's laptop (skips re-download if the platform's
    # tarball already lives under desktop/pi-runtime/vendor). On a fresh
    # CI runner this is the only step that makes pi-coding-agent + the
    # node binary visible to Tauri's bundle.resources block.
    bash "${DESKTOP}/pi-runtime/fetch-node.sh" --current-platform-only
    bash "${DESKTOP}/pi-runtime/install-pi.sh"
}

regen_third_party_licenses_mac() {
    [[ ${DMG_ONLY} -eq 1 ]] && return 0
    banner "regenerate THIRD_PARTY_LICENSES.txt"
    # Must run AFTER pi-runtime is vendored (so node_modules exist) and
    # BEFORE the sidecar build (so the frozen binary picks up the file).
    # Help → Open Source Licenses surfaces this to the user offline.
    node "${HERE}/gen-third-party-licenses.mjs"
}

build_frontend_mac() {
    [[ ${DMG_ONLY} -eq 1 ]] && return 0
    banner "macOS · build frontend"
    # `npm install` (not `npm ci`) for forgiving behaviour on a dev's
    # laptop where node_modules might already exist with a slightly
    # different lockfile state. On CI the cache key is keyed off
    # package-lock.json so this still installs from the lockfile in
    # practice. --no-audit + --no-fund cuts ~10s of network chatter
    # we don't care about during a release.
    ( cd "${DESKTOP}/frontend" && \
      npm install --no-audit --no-fund --prefer-offline && \
      npm run build )
}

build_tauri_mac() {
    [[ ${DMG_ONLY} -eq 1 ]] && return 0
    banner "macOS · tauri build (cargo bundle)"
    log "loading env from ${ENV_TMP} for build.rs"
    # `set -a` exports every var read by the upcoming source line so
    # build.rs's std::env::var(KEY) sees them (build.rs's own
    # backend/.env fallback is layered below in priority — shell env
    # wins). The `|| true` keeps the trap-safe `set -e` from killing
    # us on a malformed env line; build.rs just won't see the bad var.
    # `npm install` here picks up @tauri-apps/cli from desktop/package.json's
    # devDependencies so `npx tauri` resolves to the workspace-pinned
    # version. On a dev's laptop this is a no-op (~1s) because the
    # tree is already populated; on a fresh CI runner it's the only
    # way `npx tauri` finds the cli at all.
    # Only ask Tauri for the .app bundle. Tauri's bundle_dmg.sh has
    # been flaky (creates a corrupt DMG at random ~1 in 5 builds, see
    # https://github.com/tauri-apps/tauri/issues/3055). We hand the
    # signed .app to `create-dmg` ourselves below — gives a real
    # drag-to-Applications window AND deterministic exit codes.
    ( set -a; source "${ENV_TMP}" || true; set +a;
      cd "${DESKTOP}" && \
      npm install --no-audit --no-fund --prefer-offline && \
      npx tauri build --target "${TARGET}" --bundles app )
}

sign_app_mac() {
    banner "macOS · deep-sign .app"
    [[ -d "${APP_PATH}" ]] || fail ".app not found at ${APP_PATH}"
    codesign --force --deep --sign - "${APP_PATH}"
    codesign --verify --deep --strict --verbose=1 "${APP_PATH}"
    log "signed: ${APP_PATH}"
}

build_dmg() {
    banner "macOS · build DMG (create-dmg)"
    rm -f "${DMG_OUT}"
    create-dmg \
        --volname "Digi Setu" \
        --window-pos 200 120 \
        --window-size 640 400 \
        --icon-size 128 \
        --icon "Digi Setu.app" 180 200 \
        --hide-extension "Digi Setu.app" \
        --app-drop-link 460 200 \
        --no-internet-enable \
        "${DMG_OUT}" \
        "${APP_PATH}"
    log "DMG: ${DMG_OUT} ($(du -h "${DMG_OUT}" | cut -f1))"
}

mac_pipeline() {
    [[ ${DO_MAC} -eq 1 ]] || return 0
    # Order matters:
    #   1. sidecar      — PyInstaller-frozen FastAPI (host-arch).
    #   2. pi-runtime   — vendored Node + pi-coding-agent. Must come
    #                      before the licenses step (which scans
    #                      node_modules) and before the Tauri build
    #                      (whose bundle.resources block ships the
    #                      vendor/ directory).
    #   3. licenses     — regenerates THIRD_PARTY_LICENSES.txt that
    #                      Help → Open Source Licenses reads.
    #   4. frontend     — npm install + Vite build → frontend/dist.
    #   5. tauri build  — assembles the .app from sidecar + dist + rust.
    #   6. ad-hoc sign  — strict codesign with `-` identity so Gatekeeper
    #                      accepts it after a right-click → Open.
    #   7. DMG          — create-dmg gives the drag-to-Applications UX.
    build_sidecar_mac
    vendor_pi_runtime_mac
    regen_third_party_licenses_mac
    build_frontend_mac
    build_tauri_mac
    sign_app_mac
    build_dmg
}

# ── 5. Linux pipeline (Docker) ────────────────────────────────────
linux_pipeline() {
    [[ ${DO_LINUX} -eq 1 ]] || return 0
    banner "Linux · build (Docker)"
    # build-linux.sh handles image build + bind-mount + env wiring.
    # We pass our env file via TAURI_BUILD_ENV so build.rs inside the
    # container reads identical Clerk + cloud-target keys.
    APP_VERSION="${APP_VERSION}" \
    TAURI_BUILD_ENV="${ENV_TMP}" \
        bash "${HERE}/build-linux.sh"
}

# ── 6. Upload + smoke-test ────────────────────────────────────────
upload_and_smoke_one() {
    local local_path="$1"
    local remote_name="$2"
    [[ -f "${local_path}" ]] || { warn "not found, skipping upload: ${local_path}"; return 0; }
    log "uploading ${remote_name}"
    bash "${REPO_ROOT}/deploy/scripts/upload-installer.sh" \
        "${local_path}" "${remote_name}"
    [[ ${NO_UPLOAD} -eq 1 ]] && return 0
    smoke_one "${local_path}" "${remote_name}"
}

smoke_one() {
    local local_path="$1"
    local remote_name="$2"
    local url="https://digi-setu.com/downloads/${remote_name}"
    local local_sha
    local_sha=$(shasum -a 256 "${local_path}" | awk '{print $1}')
    log "  local sha256:  ${local_sha}"
    log "  HEAD ${url}"
    local code
    code=$(curl -sIL -o /dev/null -w '%{http_code}' --max-time 30 "${url}")
    if [[ "${code}" != "200" && "${code}" != "206" ]]; then
        fail "public URL returned HTTP ${code}; aborting"
    fi
    log "  HTTP ${code} OK; downloading to verify sha256 (~30-60s)"
    local remote_sha
    remote_sha=$(curl -fsSL --max-time 600 "${url}" | shasum -a 256 | awk '{print $1}')
    log "  remote sha256: ${remote_sha}"
    [[ "${local_sha}" == "${remote_sha}" ]] || fail "  sha256 mismatch — CDN serving stale copy or upload corrupted"
    log "  ✓ ${url}"
}

upload_phase() {
    [[ ${NO_UPLOAD} -eq 1 ]] && { log "--no-upload set, skipping upload"; return 0; }
    banner "upload + smoke-test"
    if [[ ${DO_MAC}   -eq 1 ]]; then upload_and_smoke_one "${DMG_OUT}"          "${DMG_NAME}"; fi
    if [[ ${DO_LINUX} -eq 1 ]]; then
        upload_and_smoke_one "${LINUX_DEB_OUT}"    "$(basename "${LINUX_DEB_OUT}")"
        upload_and_smoke_one "${LINUX_APPIMG_OUT}" "$(basename "${LINUX_APPIMG_OUT}")"
    fi
    printf '\n\033[1;32m[release]\033[0m DONE.\n'
    [[ ${DO_MAC}   -eq 1 ]] && printf '  macOS    https://digi-setu.com/downloads/%s\n' "${DMG_NAME}"
    [[ ${DO_LINUX} -eq 1 ]] && {
        printf '  Linux    https://digi-setu.com/downloads/%s\n' "$(basename "${LINUX_DEB_OUT}")"
        printf '           https://digi-setu.com/downloads/%s\n' "$(basename "${LINUX_APPIMG_OUT}")"
    }
}

# ── Main ─────────────────────────────────────────────────────────
preflight
fetch_secrets
rebuild_icons
mac_pipeline
linux_pipeline
upload_phase
