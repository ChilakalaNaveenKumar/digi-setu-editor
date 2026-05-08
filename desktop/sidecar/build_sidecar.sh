#!/usr/bin/env bash
# Build the PyInstaller-frozen FastAPI sidecar binary on macOS / Linux.
#
# Output:
#     desktop/sidecar/dist/pi-typst-sidecar
#     desktop/sidecar/dist/pi-typst-sidecar-<rust-target-triple>
#                                                  (so Tauri's externalBin
#                                                  glob picks it up)
#
# Re-uses the .venv at web/backend/.venv. We do NOT create a fresh venv
# here because the user's local one already has every requirement
# installed; bypassing it would just download the same wheels twice.
# If the venv is missing we abort with a friendly message.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_ROOT="$(cd "$HERE/.." && pwd)"
# Desktop owns its own forked backend. The top-level web/ tree stays
# untouched; we only build against desktop/backend/ from now on.
BACKEND_DIR="$DESKTOP_ROOT/backend"
VENV="$BACKEND_DIR/.venv"

if [[ ! -d "$VENV" ]]; then
    echo "[build] backend venv missing at $VENV — creating it now…" >&2
    python3 -m venv "$VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    python -m pip install --upgrade pip
    python -m pip install -r "$BACKEND_DIR/requirements.txt"
    deactivate || true
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Make sure PyInstaller is installed in the venv. We do this lazily so
# we don't bloat the prod requirements.txt with a build-time dep.
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "[build] Installing PyInstaller into backend venv…"
    python -m pip install --quiet "pyinstaller>=6.10,<7"
fi

cd "$HERE"

# --clean wipes the build/ cache; --noconfirm accepts overwrites.
echo "[build] Running PyInstaller…"
python -m PyInstaller --clean --noconfirm pyinstaller.spec

DIST="$HERE/dist"

if [[ ! -f "$DIST/pi-typst-sidecar" ]]; then
    echo "ERROR: PyInstaller did not produce $DIST/pi-typst-sidecar" >&2
    exit 1
fi

# Tauri's externalBin requires a per-platform suffixed binary. Compute
# the Rust target triple for the current host.
TRIPLE="$(rustc -vV | sed -n 's/host: //p' | tr -d '[:space:]')"
SUFFIXED="$DIST/pi-typst-sidecar-$TRIPLE"
cp "$DIST/pi-typst-sidecar" "$SUFFIXED"
chmod +x "$SUFFIXED"

echo "[build] Wrote $DIST/pi-typst-sidecar"
echo "[build] Wrote $SUFFIXED"
echo "[build] Done."
