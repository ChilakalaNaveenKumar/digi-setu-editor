# End-to-end Windows release build (NSIS + MSI).
#
# Produces:
#     desktop\src-tauri\target\release\bundle\msi\Digi Setu_<version>_x64_en-US.msi
#     desktop\src-tauri\target\release\bundle\nsis\Digi Setu_<version>_x64-setup.exe
#
# Run this from a PowerShell session with:
#   - Rust + cargo on PATH (rustup-init.exe)
#   - Python 3.11 on PATH (must match desktop/backend/.venv's Python)
#   - Visual Studio 2022 Build Tools (for the MSVC linker the Rust
#     toolchain uses to link Tauri/wry)
#   - Node 22 on PATH (for the frontend build; the bundled Node
#     installed by fetch-node.ps1 is for runtime, not build)

$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = Resolve-Path "$Here\.."

$Target = "x86_64-pc-windows-msvc"

Write-Host "[release-win] target = $Target"

# 1. Rust target.
$installed = rustup target list --installed
if ($installed -notmatch [regex]::Escape($Target)) {
    rustup target add $Target
}

# 2. Sidecar.
Write-Host "[release-win] building sidecar..."
& powershell -ExecutionPolicy Bypass -File (Join-Path $Desktop "sidecar\build_sidecar.ps1")
if ($LASTEXITCODE -ne 0) { throw "sidecar build failed" }

# 3. Vendored Node + pi.
Write-Host "[release-win] vendoring Node + pi..."
& powershell -ExecutionPolicy Bypass -File (Join-Path $Desktop "pi-runtime\fetch-node.ps1") -CurrentPlatformOnly
& powershell -ExecutionPolicy Bypass -File (Join-Path $Desktop "pi-runtime\install-pi.ps1")

# 4. Frontend dist.
Write-Host "[release-win] building frontend dist..."
Push-Location (Join-Path $Desktop "frontend")
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally {
    Pop-Location
}

# 5. Tauri bundle.
Write-Host "[release-win] running tauri build..."
Push-Location $Desktop
try {
    npx tauri build --target $Target
    if ($LASTEXITCODE -ne 0) { throw "tauri build failed" }
} finally {
    Pop-Location
}

$OutMsi = Join-Path $Desktop "src-tauri\target\$Target\release\bundle\msi"
$OutNsis = Join-Path $Desktop "src-tauri\target\$Target\release\bundle\nsis"
Write-Host ""
Write-Host "[release-win] Done."
Write-Host "  .msi → $OutMsi"
Write-Host "  setup.exe → $OutNsis"
Get-ChildItem -Path $OutMsi -ErrorAction SilentlyContinue | Format-Table -AutoSize
Get-ChildItem -Path $OutNsis -ErrorAction SilentlyContinue | Format-Table -AutoSize
