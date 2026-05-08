# Install pi-coding-agent + the project's extensions into the vendored
# tree on Windows. Mirror of install-pi.sh.

$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Here "vendor"
$ProjectRoot = Resolve-Path "$Here\..\..\"

$NodeBin = Join-Path $Vendor "node-win-x64\node.exe"
$NpmCli = Join-Path $Vendor "node-win-x64\node_modules\npm\bin\npm-cli.js"

if (-not (Test-Path $NodeBin)) {
    Write-Error "Bundled Node not found. Run fetch-node.ps1 first."
    exit 1
}
if (-not (Test-Path $NpmCli)) {
    Write-Error "Bundled npm CLI script missing at $NpmCli. Re-run fetch-node.ps1 to refresh."
    exit 1
}

$PiDir = Join-Path $Vendor "pi"
New-Item -ItemType Directory -Force -Path $PiDir | Out-Null

@'
{
  "name": "pi-runtime-bundle",
  "version": "0.1.0",
  "private": true,
  "description": "Vendored install of pi-coding-agent + typst-tools deps for Digi Setu desktop.",
  "dependencies": {
    "@mariozechner/pi-coding-agent": "*",
    "@anthropic-ai/vertex-sdk": "^0.16.0",
    "@google/genai": "^1.0.0",
    "typebox": "^1.1.24",
    "tsx": "^4.21.0"
  }
}
'@ | Set-Content -Path (Join-Path $PiDir "package.json") -Encoding UTF8

Write-Host "[pi-runtime] installing pi-coding-agent + extension deps..."
Push-Location $PiDir
try {
    & $NodeBin $NpmCli install --no-audit --no-fund
} finally {
    Pop-Location
}

$PiBin = Join-Path $PiDir "node_modules\.bin\pi.cmd"
if (-not (Test-Path $PiBin)) {
    Write-Error "vendor/pi/node_modules/.bin/pi.cmd missing after install"
    exit 1
}

# Copy the project extensions into vendor/extensions/ so absolute paths
# in pi --extension don't depend on the user's picked folder.
$Extensions = Join-Path $Vendor "extensions"
New-Item -ItemType Directory -Force -Path $Extensions | Out-Null
Copy-Item -Path (Join-Path $ProjectRoot "extensions\*") -Destination $Extensions -Recurse -Force

# Apply pi-ai patches (vertex providers, GCE metadata trust). Same as
# install-pi.sh — idempotent, no-ops if already patched.
$PiPkg = Join-Path $PiDir "node_modules\@mariozechner\pi-coding-agent"
$PiAi  = Join-Path $PiDir "node_modules\@mariozechner\pi-ai"
$ApplyEdits = Join-Path $ProjectRoot "patches\apply-edits.mjs"
if ((Test-Path $PiPkg) -and (Test-Path $PiAi) -and (Test-Path $ApplyEdits)) {
    Write-Host "[pi-runtime] applying pi-ai patches (vertex providers + GCE-metadata trust)..."
    & $NodeBin $ApplyEdits $PiPkg $PiAi
} else {
    Write-Warning "[pi-runtime] pi-coding-agent / pi-ai / patches missing - skipping patch step"
}

Write-Host "[pi-runtime] pi installed at $PiBin"
Write-Host "[pi-runtime] extensions copied to $Extensions"
& $NodeBin (Join-Path $PiDir "node_modules\@mariozechner\pi-coding-agent\dist\index.js") --version
Write-Host "[pi-runtime] install complete."
