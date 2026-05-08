# Download Node.js LTS binaries on Windows.
#
# Mirrors fetch-node.sh's behaviour for PowerShell:
#   - Pinned Node version, identical to the bash script
#   - All four platforms by default (so a Win box can build Mac builds
#     on CI in theory), `-CurrentPlatformOnly` for just win-x64
#   - Skips re-fetching if vendor/node-<platform>/ already has node.

$ErrorActionPreference = "Stop"

$NodeVersion = "22.13.0"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Here "vendor"
New-Item -ItemType Directory -Force -Path $Vendor | Out-Null

param([switch]$CurrentPlatformOnly)

function Fetch-Node {
    param([string]$Platform)

    $isWin = $Platform.StartsWith("win-")
    $ext = if ($isWin) { "zip" } else { "tar.gz" }
    $dist = "node-v$NodeVersion-$Platform"
    $url = "https://nodejs.org/dist/v$NodeVersion/$dist.$ext"
    $target = Join-Path $Vendor "node-$Platform"

    $sentinel = if ($isWin) {
        Join-Path $target "node.exe"
    } else {
        Join-Path $target "bin/node"
    }
    if (Test-Path $sentinel) {
        Write-Host "[pi-runtime] $Platform already vendored, skipping"
        return
    }

    Write-Host "[pi-runtime] fetching Node $NodeVersion for $Platform..."
    $tmp = Join-Path $env:TEMP "pi-node-$Platform-$([guid]::NewGuid())"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    try {
        $archive = Join-Path $tmp "node.$ext"
        Invoke-WebRequest -Uri $url -OutFile $archive

        if ($isWin) {
            Expand-Archive -Path $archive -DestinationPath $tmp -Force
        } else {
            tar -xzf $archive -C $tmp
        }
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        Copy-Item -Path (Join-Path $tmp "$dist\*") -Destination $target -Recurse -Force
        Write-Host "[pi-runtime] $Platform: ready at $target"
    } finally {
        Remove-Item -Path $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($CurrentPlatformOnly) {
    Fetch-Node "win-x64"
} else {
    Fetch-Node "win-x64"
    Fetch-Node "darwin-arm64"
    Fetch-Node "darwin-x64"
    Fetch-Node "linux-x64"
}

Write-Host "[pi-runtime] Node fetch complete."
