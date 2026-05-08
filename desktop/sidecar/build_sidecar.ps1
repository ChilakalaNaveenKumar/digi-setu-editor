# Build the PyInstaller-frozen FastAPI sidecar binary on Windows.
#
# Output:
#     desktop\sidecar\dist\pi-typst-sidecar.exe
#     desktop\sidecar\dist\pi-typst-sidecar-x86_64-pc-windows-msvc.exe
#                                                  (so Tauri's externalBin
#                                                  glob picks it up)
#
# Builds against desktop\backend (the desktop fork). Auto-creates
# desktop\backend\.venv on first run if missing.

$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopRoot = Resolve-Path "$Here\.."
$BackendDir = Join-Path $DesktopRoot "backend"
$Venv = Join-Path $BackendDir ".venv"

if (-not (Test-Path $Venv)) {
    Write-Host "[build] backend venv missing at $Venv - creating it now..."
    & python -m venv $Venv
    & (Join-Path $Venv "Scripts\python.exe") -m pip install --upgrade pip
    & (Join-Path $Venv "Scripts\python.exe") -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

# Activate the venv for this script's lifetime.
. (Join-Path $Venv "Scripts\Activate.ps1")

# Lazy-install PyInstaller — keeps it out of the prod requirements.txt
$probe = & python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[build] Installing PyInstaller into backend venv..."
    python -m pip install --quiet "pyinstaller>=6.10,<7"
}

Push-Location $Here
try {
    Write-Host "[build] Running PyInstaller..."
    python -m PyInstaller --clean --noconfirm pyinstaller.spec

    $Dist = Join-Path $Here "dist"
    $Bin = Join-Path $Dist "pi-typst-sidecar.exe"
    if (-not (Test-Path $Bin)) {
        Write-Error "PyInstaller did not produce $Bin"
        exit 1
    }

    $Triple = (& rustc -vV | Select-String "^host: ").ToString().Replace("host: ", "").Trim()
    $Suffixed = Join-Path $Dist "pi-typst-sidecar-$Triple.exe"
    Copy-Item -Path $Bin -Destination $Suffixed -Force

    Write-Host "[build] Wrote $Bin"
    Write-Host "[build] Wrote $Suffixed"
    Write-Host "[build] Done."
} finally {
    Pop-Location
}
