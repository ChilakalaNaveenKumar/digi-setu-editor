#!/usr/bin/env bash
# Download Node.js LTS binaries for every platform we ship to.
#
# We bundle Node inside the desktop app so users don't need it
# installed system-wide. The pi CLI is a Node CLI (`@mariozechner/
# pi-coding-agent`) and shipping our own runtime is the only way to
# keep "drag-the-dmg-to-Applications" the entire onboarding.
#
# Output:
#     desktop/pi-runtime/vendor/node-darwin-arm64/   ← unpacked tree
#     desktop/pi-runtime/vendor/node-darwin-x64/
#     desktop/pi-runtime/vendor/node-linux-x64/
#     desktop/pi-runtime/vendor/node-win-x64/
#
# By default we fetch ALL platforms so a single Mac dev can build the
# Windows installer too. Pass `--current-platform-only` to fetch just
# the host's platform (~30 MB instead of ~120 MB).
#
# The Node version is pinned so the desktop binary is reproducible
# across machines. Bumping it = bumping desktop's bundled runtime.
set -euo pipefail

NODE_VERSION="22.13.0"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$HERE/vendor"
mkdir -p "$VENDOR"

CURRENT_ONLY=0
[[ "${1:-}" == "--current-platform-only" ]] && CURRENT_ONLY=1

# Map the current host to a vendor subdir so we know which platform
# the dev's likely to run `tauri dev` against first.
host_platform=""
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)  host_platform="darwin-arm64" ;;
    Darwin-x86_64) host_platform="darwin-x64"   ;;
    Linux-x86_64)  host_platform="linux-x64"    ;;
    Linux-aarch64) host_platform="linux-arm64"  ;;
    *)             host_platform="darwin-arm64" ;;
esac

fetch_node() {
    local platform="$1"        # darwin-arm64, darwin-x64, linux-x64, win-x64
    local archive_kind         # tarball or zip — depends on platform
    local archive_ext

    case "$platform" in
        darwin-*|linux-*) archive_kind=tar; archive_ext=tar.gz ;;
        win-*)            archive_kind=zip; archive_ext=zip ;;
        *) echo "Unknown platform: $platform" >&2; return 1 ;;
    esac

    local dist="node-v${NODE_VERSION}-${platform}"
    local url="https://nodejs.org/dist/v${NODE_VERSION}/${dist}.${archive_ext}"
    local target="$VENDOR/node-${platform}"

    if [[ -d "$target" && -x "$target/bin/node" ]] || [[ -d "$target" && -f "$target/node.exe" ]]; then
        echo "[pi-runtime] $platform already vendored, skipping"
        return 0
    fi

    echo "[pi-runtime] fetching Node $NODE_VERSION for $platform…"
    local tmp; tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN

    if [[ "$archive_kind" == tar ]]; then
        curl -fsSL "$url" -o "$tmp/node.tar.gz"
        tar -xzf "$tmp/node.tar.gz" -C "$tmp"
        mkdir -p "$target"
        rsync -a --remove-source-files "$tmp/$dist/" "$target/" 2>/dev/null \
            || cp -R "$tmp/$dist/." "$target/"
    else
        curl -fsSL "$url" -o "$tmp/node.zip"
        # Mac/Linux: prefer `unzip`, fall back to ditto on Mac.
        if command -v unzip >/dev/null 2>&1; then
            unzip -q "$tmp/node.zip" -d "$tmp"
        else
            ditto -x -k "$tmp/node.zip" "$tmp"
        fi
        mkdir -p "$target"
        cp -R "$tmp/$dist/." "$target/"
    fi

    echo "[pi-runtime] $platform: ready at $target"
}

if [[ $CURRENT_ONLY -eq 1 ]]; then
    fetch_node "$host_platform"
else
    fetch_node "darwin-arm64"
    fetch_node "darwin-x64"
    fetch_node "linux-x64"
    fetch_node "win-x64"
fi

echo "[pi-runtime] Node fetch complete."
