# build-windows.ps1 — end-to-end Windows release build (NSIS .exe + .msi).
#
# Run on Windows 10/11 with:
#   - PowerShell 7+ (Set-StrictMode v3 features below)
#   - Rust + cargo on PATH (rustup-init.exe), with the
#     x86_64-pc-windows-msvc target installed
#   - Python 3.11 on PATH (matches our PyInstaller spec)
#   - Visual Studio 2022 Build Tools (MSVC linker for Rust + Tauri)
#   - Node 22 on PATH (for the Vite frontend build)
#   - WiX Toolset 3.11+ (Tauri's MSI bundler)
#   - Optionally: gcloud CLI authenticated against digi-setu-dev so we
#     can pull Clerk + cloud-target keys from Secret Manager. Without
#     it we fall back to desktop\backend\.env (just like release.sh).
#
# Usage:
#   .\desktop\scripts\build-windows.ps1                 # build .exe + .msi
#   .\desktop\scripts\build-windows.ps1 -LocalEnv       # bypass GSM
#   .\desktop\scripts\build-windows.ps1 -SkipSidecar    # reuse existing dist
#
# Output:
#   desktop\src-tauri\target\x86_64-pc-windows-msvc\release\bundle\
#       msi\Digi Setu_<version>_x64_en-US.msi
#       nsis\Digi Setu_<version>_x64-setup.exe

param(
    [switch]$LocalEnv,
    [switch]$SkipSidecar,
    [switch]$SkipGsm,         # CI: read TAURI_BUILD_ENV instead of pulling from GSM
    [string]$GcpProject = "digi-setu-dev",
    [string]$AppVersion = "0.1.0"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = Resolve-Path "$Here\.."
$Repo = Resolve-Path "$Desktop\.."

$Target = "x86_64-pc-windows-msvc"

function Log($msg)  { Write-Host "[release-win] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Warning "[release-win] $msg" }

# ── 1. Preflight ──────────────────────────────────────────────────────
Log "target = $Target  · version = $AppVersion"
foreach ($bin in @("rustup", "cargo", "npm", "node", "python")) {
    if (-not (Get-Command $bin -ErrorAction SilentlyContinue)) {
        throw "Missing required tool on PATH: $bin"
    }
}

$installed = & rustup target list --installed
if ($installed -notmatch [regex]::Escape($Target)) {
    Log "installing rust target $Target"
    & rustup target add $Target
}

# ── 2. Fetch secrets (GSM with .env fallback) ─────────────────────────
$EnvTmp = [System.IO.Path]::GetTempFileName()
$cleanup = { if (Test-Path $EnvTmp) { Remove-Item $EnvTmp -Force } }
trap { & $cleanup; throw }   # Wipe the temp env file even on error

if ($SkipGsm) {
    # CI path: GitHub Actions stages a .release-secrets.tmp.env file and
    # exports its absolute path as $env:TAURI_BUILD_ENV. This avoids
    # needing a GCP service-account key on the runner just to read two
    # values that already live in the workflow's repo secrets.
    if (-not $env:TAURI_BUILD_ENV -or -not (Test-Path $env:TAURI_BUILD_ENV)) {
        throw "(-SkipGsm) requires `$env:TAURI_BUILD_ENV to point at a readable .env file"
    }
    Log "(-SkipGsm) using $env:TAURI_BUILD_ENV"
    Copy-Item $env:TAURI_BUILD_ENV $EnvTmp -Force
} elseif ($LocalEnv) {
    Log "(--local-env) copying desktop\backend\.env"
    if (-not (Test-Path "$Desktop\backend\.env")) {
        throw "desktop\backend\.env missing — re-run with -LocalEnv after creating one, or drop the flag and authenticate gcloud."
    }
    Copy-Item "$Desktop\backend\.env" $EnvTmp -Force
} else {
    if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
        throw "gcloud not on PATH — install Google Cloud SDK or pass -LocalEnv"
    }
    Log "pulling Clerk + cloud-target keys from GSM project $GcpProject"
    $pulled = 0
    foreach ($key in @("CLERK_PUBLISHABLE_KEY_PROD", "CLERK_SECRET_KEY_PROD")) {
        $val = & gcloud secrets versions access latest `
            --project $GcpProject --secret $key 2>$null
        if ($LASTEXITCODE -eq 0 -and $val) {
            "${key}=${val}" | Out-File -FilePath $EnvTmp -Append -Encoding ASCII
            $pulled++
        } else {
            Warn "GSM missing: $key"
        }
    }
    # Cloud target URLs — match release.sh exactly. Apex domain for
    # /api/* routes, api subdomain for /v1/* (WebSocket relay).
    $cloudApi  = if ($env:PI_CLOUD_API_BASE) { $env:PI_CLOUD_API_BASE } else { "https://digi-setu.com" }
    $relayBase = if ($env:PI_RELAY_BASE)     { $env:PI_RELAY_BASE     } else { "https://api.digi-setu.com" }
    $tenant    = if ($env:CLERK_TENANT)      { $env:CLERK_TENANT      } else { "prod" }
    "PI_CLOUD_API_BASE=$cloudApi"   | Out-File -FilePath $EnvTmp -Append -Encoding ASCII
    "PI_RELAY_BASE=$relayBase"      | Out-File -FilePath $EnvTmp -Append -Encoding ASCII
    "CLERK_TENANT=$tenant"          | Out-File -FilePath $EnvTmp -Append -Encoding ASCII
    Log "pulled $pulled secrets from GSM"
    if ($pulled -eq 0) {
        Warn "no secrets pulled; falling back to desktop\backend\.env"
        if (Test-Path "$Desktop\backend\.env") {
            Copy-Item "$Desktop\backend\.env" $EnvTmp -Force
        }
    }
}

# Source the env file into the current process so build.rs sees them.
Get-Content $EnvTmp | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $k = $matches[1].Trim()
        $v = $matches[2].Trim()
        Set-Item -Path "Env:$k" -Value $v
    }
}

# ── 3. Sidecar (PyInstaller) ──────────────────────────────────────────
if (-not $SkipSidecar) {
    Log "building sidecar..."
    & powershell -ExecutionPolicy Bypass -File (Join-Path $Desktop "sidecar\build_sidecar.ps1")
    if ($LASTEXITCODE -ne 0) { throw "sidecar build failed" }
} else {
    Log "(-SkipSidecar) reusing existing sidecar dist"
}

# ── 4. Vendored Node + pi (Windows tarball) ───────────────────────────
Log "vendoring Windows Node + pi-coding-agent..."
& powershell -ExecutionPolicy Bypass -File (Join-Path $Desktop "pi-runtime\fetch-node.ps1") -CurrentPlatformOnly
& powershell -ExecutionPolicy Bypass -File (Join-Path $Desktop "pi-runtime\install-pi.ps1")

# ── 5. Third-party licences ───────────────────────────────────────────
Log "regenerating THIRD_PARTY_LICENSES.txt..."
& node (Join-Path $Desktop "scripts\gen-third-party-licenses.mjs")
if ($LASTEXITCODE -ne 0) { throw "license generator failed" }

# ── 6. Frontend dist ──────────────────────────────────────────────────
Log "building frontend dist..."
Push-Location (Join-Path $Desktop "frontend")
try {
    & npm install --no-audit --no-fund --prefer-offline
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally { Pop-Location }

# ── 7. Tauri bundle (.exe via NSIS, .msi via WiX) ─────────────────────
Log "running tauri build..."
Push-Location $Desktop
try {
    & npx tauri build --target $Target --bundles nsis,msi
    if ($LASTEXITCODE -ne 0) { throw "tauri build failed" }
} finally { Pop-Location }

# ── 8. Locate + normalise output filenames ────────────────────────────
$BundleDir = Join-Path $Desktop "src-tauri\target\$Target\release\bundle"
$MsiSrc  = Get-ChildItem -Path (Join-Path $BundleDir "msi")  -Filter *.msi  -ErrorAction SilentlyContinue | Select-Object -First 1
$ExeSrc  = Get-ChildItem -Path (Join-Path $BundleDir "nsis") -Filter *-setup.exe -ErrorAction SilentlyContinue | Select-Object -First 1

$MsiOut = Join-Path $env:TEMP "Digi-Setu-$AppVersion-x64.msi"
$ExeOut = Join-Path $env:TEMP "Digi-Setu-$AppVersion-x64-setup.exe"

if ($MsiSrc) {
    Copy-Item $MsiSrc.FullName $MsiOut -Force
    Log ".msi  → $MsiOut  ($([math]::Round((Get-Item $MsiOut).Length/1MB,1)) MB)"
} else { Warn "no .msi produced under $BundleDir\msi" }

if ($ExeSrc) {
    Copy-Item $ExeSrc.FullName $ExeOut -Force
    Log ".exe  → $ExeOut  ($([math]::Round((Get-Item $ExeOut).Length/1MB,1)) MB)"
} else { Warn "no -setup.exe produced under $BundleDir\nsis" }

# ── 9. Code signing (skipped if no cert env vars) ─────────────────────
# When TRUSTED_SIGNING_DLIB_PATH + TRUSTED_SIGNING_ENDPOINT +
# TRUSTED_SIGNING_ACCOUNT + TRUSTED_SIGNING_PROFILE are all set,
# sign both artefacts via signtool with the Azure Trusted Signing
# Dlib. Otherwise we ship unsigned (SmartScreen warning is documented
# on the download page).
if ($env:TRUSTED_SIGNING_DLIB_PATH -and $env:TRUSTED_SIGNING_ENDPOINT -and
    $env:TRUSTED_SIGNING_ACCOUNT   -and $env:TRUSTED_SIGNING_PROFILE) {
    Log "Azure Trusted Signing detected — signing artefacts"
    foreach ($artefact in @($ExeOut, $MsiOut)) {
        if ($artefact -and (Test-Path $artefact)) {
            $metadata = @{
                Endpoint = $env:TRUSTED_SIGNING_ENDPOINT
                CodeSigningAccountName = $env:TRUSTED_SIGNING_ACCOUNT
                CertificateProfileName = $env:TRUSTED_SIGNING_PROFILE
            } | ConvertTo-Json -Compress
            $metaFile = [System.IO.Path]::GetTempFileName() + ".json"
            $metadata | Out-File -FilePath $metaFile -Encoding ASCII
            & signtool sign /v /debug /fd SHA256 /tr "http://timestamp.acs.microsoft.com" `
                /td SHA256 /dlib $env:TRUSTED_SIGNING_DLIB_PATH /dmdf $metaFile $artefact
            Remove-Item $metaFile -Force
            if ($LASTEXITCODE -ne 0) { throw "signtool failed for $artefact" }
            Log "signed: $artefact"
        }
    }
} else {
    Warn "Trusted Signing env vars not set — shipping UNSIGNED (SmartScreen warning will display on first launch)"
}

& $cleanup
Log "done."
