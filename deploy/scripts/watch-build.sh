#!/usr/bin/env bash
# watch-build.sh — best-effort progress monitor for a Bitbucket
# Pipelines run when our API token can't read pipeline state.
#
# Polls three signals every 30s for up to MAX_MINUTES (default 25):
#   1. Linux .deb on digi-setu.com/downloads/  (Last-Modified header)
#   2. Web frontend bundle hash in https://digi-setu.com/index.html
#   3. Backend version reported by https://api.digi-setu.com/health
#
# When a signal flips vs the baseline captured at start, we log it.
# Exits cleanly when all three signals have flipped (full deploy
# detected) or when we hit MAX_MINUTES.

set -uo pipefail

MAX_MINUTES="${MAX_MINUTES:-25}"
LOG="${LOG:-/tmp/digi-setu-build-watch.log}"
DEB_URL="${DEB_URL:-https://digi-setu.com/downloads/Digi-Setu-0.1.0-amd64.deb}"
WEB_URL="${WEB_URL:-https://digi-setu.com/}"
HEALTH_URL="${HEALTH_URL:-https://api.digi-setu.com/health}"

stamp() { date -u '+%H:%M:%SZ'; }
say()   { printf '[%s] %s\n' "$(stamp)" "$*" | tee -a "${LOG}"; }

# Snapshot baselines
deb_mtime0=$(curl -sI "${DEB_URL}" | awk -F': ' 'tolower($1)=="last-modified"{print $2}' | tr -d '\r')
web_hash0=$(curl -sL "${WEB_URL}" | grep -oE '/assets/[^"]+\.(js|css)' | sort -u | shasum -a 256 | awk '{print $1}')
health0=$(curl -sL --max-time 5 "${HEALTH_URL}" 2>/dev/null || echo "")

: > "${LOG}"
say "watching for ${MAX_MINUTES} min — initial signals captured:"
say "  .deb     last-modified : ${deb_mtime0:-<none>}"
say "  web      bundle hash   : ${web_hash0:0:16}"
say "  backend  /health       : $(printf '%s' "${health0}" | head -c 80)"
say ""

deb_changed=0; web_changed=0; backend_changed=0
deadline=$(( $(date +%s) + MAX_MINUTES*60 ))
i=0

while (( $(date +%s) < deadline )); do
    sleep 30
    i=$((i+1))
    deb_mtime=$(curl -sI "${DEB_URL}" | awk -F': ' 'tolower($1)=="last-modified"{print $2}' | tr -d '\r')
    web_hash=$(curl -sL "${WEB_URL}" | grep -oE '/assets/[^"]+\.(js|css)' | sort -u | shasum -a 256 | awk '{print $1}')
    health=$(curl -sL --max-time 5 "${HEALTH_URL}" 2>/dev/null || echo "")

    if (( deb_changed == 0 )) && [[ -n "${deb_mtime}" && "${deb_mtime}" != "${deb_mtime0}" ]]; then
        deb_changed=1
        say "✓ Linux .deb refreshed   (was ${deb_mtime0} → now ${deb_mtime})"
    fi
    if (( web_changed == 0 )) && [[ -n "${web_hash}" && "${web_hash}" != "${web_hash0}" ]]; then
        web_changed=1
        say "✓ Web frontend refreshed (bundle hash flipped)"
    fi
    if (( backend_changed == 0 )) && [[ -n "${health}" && "${health}" != "${health0}" ]]; then
        backend_changed=1
        say "✓ Backend /health refreshed (response changed)"
    fi

    # Heartbeat every 2 minutes
    if (( i % 4 == 0 )); then
        say "  ... still watching (deb=${deb_changed} web=${web_changed} backend=${backend_changed})"
    fi

    if (( deb_changed && web_changed && backend_changed )); then
        say ""
        say "ALL THREE SIGNALS FLIPPED — Bitbucket build pipeline finished successfully."
        exit 0
    fi
done

say ""
say "Watch window expired (${MAX_MINUTES} min)."
say "Final state: deb=${deb_changed} web=${web_changed} backend=${backend_changed}"
say "If any flag is 0, check https://bitbucket.org/digi-setu/digi-setu-editor/pipelines for that step's failure."
exit $(( deb_changed && web_changed && backend_changed ? 0 : 1 ))
