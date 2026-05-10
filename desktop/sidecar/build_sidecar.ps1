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
}

# Activate the venv for this script's lifetime.
. (Join-Path $Venv "Scripts\Activate.ps1")

# Always sync requirements.txt against the venv. pip is idempotent so
# this is a no-op when nothing has changed, but it saves us from the
# "venv was created two PRs ago, requirements have grown since, the
# spec file still lists the new packages as hidden imports, frozen
# binary import-errors at runtime" failure mode. Symptom for the
# end-user: read_doc returns the markitdown-not-installed placeholder
# even though everything was supposed to be bundled.
Write-Host "[build] Syncing $BackendDir\requirements.txt into venv..."
& python -m pip install --quiet --disable-pip-version-check `
    -r (Join-Path $BackendDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "pip install -r requirements.txt failed (exit $LASTEXITCODE)"
}

# Lazy-install PyInstaller — keeps it out of the prod requirements.txt.
#
# `python -c "import PyInstaller"` writes a Python traceback to stderr when
# the module is missing. In PowerShell 7 with $ErrorActionPreference = "Stop"
# any stderr write from a native command is promoted to a terminating
# NativeCommandError, so the `if ($LASTEXITCODE)` branch below never even
# runs. Easiest workaround: skip the probe and install unconditionally —
# `pip install` is idempotent and a no-op when PyInstaller is already
# present (~1s overhead vs. forever-broken Windows builds).
Write-Host "[build] Ensuring PyInstaller is present in backend venv..."
& python -m pip install --quiet --disable-pip-version-check "pyinstaller>=6.10,<7"
if ($LASTEXITCODE -ne 0) {
    throw "pip install pyinstaller failed (exit $LASTEXITCODE)"
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
