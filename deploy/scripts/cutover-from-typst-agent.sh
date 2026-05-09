#!/usr/bin/env bash
# cutover-from-typst-agent.sh — replace the legacy typst-agent stack on
# the SAME VM (digi-setu-live) with this digi-setu deployment.
#
# Assumes you've already run, locally:
#   scripts/remote-deploy.sh stack        # pushed compose + caddy
#   scripts/remote-deploy.sh backend      # built + uploaded the image
#   scripts/remote-deploy.sh frontend     # streamed dist/ to /srv/pi/www
# …but typst-agent.service is still the one bound to :443.
#
# This script (run on the VM):
#   1. Stops the legacy typst-agent stack so :80/:443 are free.
#   2. Disables typst-agent + typst-agent-prepare so they don't fight
#      pi.service on the next boot.
#   3. Snapshots /srv/typst-agent/users → /srv/pi/legacy-backup so we
#      have a 30-day "oops" window before deletion.
#   4. Starts pi-prepare.service then pi.service, waits for /healthz,
#      prints status.
#
# WARNING: destructive in the sense that the OLD typst-agent stops
# serving the moment we hit step 1. Run during a low-traffic window.
# The DOMAIN itself doesn't change — Caddy on the same VM picks up
# the same hostnames, Cloudflare DNS keeps pointing at the same IP,
# end-users see only a brief 5xx blip.

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "cutover-from-typst-agent.sh must run as root" >&2
  exit 1
fi

say() { printf '\033[1;33m[cutover]\033[0m %s\n' "$*"; }

# ── 1. Stop the legacy stack ───────────────────────────────────────
say "Stopping legacy typst-agent.service if present…"
if systemctl list-unit-files | grep -q '^typst-agent\.service'; then
  systemctl stop  typst-agent.service             || true
  systemctl disable typst-agent.service           || true
fi
if systemctl list-unit-files | grep -q '^typst-agent-prepare\.service'; then
  systemctl disable typst-agent-prepare.service   || true
fi
docker ps --format '{{.Names}}' | grep -E '^typst-agent-' | xargs -r docker stop || true
docker ps -a --format '{{.Names}}' | grep -E '^typst-agent-' | xargs -r docker rm  || true

# ── 2. Backup legacy data ──────────────────────────────────────────
if [[ -d /srv/typst-agent/users ]]; then
  STAMP="$(date +%Y%m%d-%H%M%S)"
  say "Snapshotting /srv/typst-agent/users → /srv/pi/legacy-backup/typst-agent-users-$STAMP/"
  install -d -m 0700 /srv/pi/legacy-backup
  cp -a /srv/typst-agent/users /srv/pi/legacy-backup/"typst-agent-users-$STAMP"
fi

# ── 3. Bring up the new stack ──────────────────────────────────────
say "Starting pi.service…"
systemctl daemon-reload
systemctl restart pi-prepare.service
systemctl restart pi.service

# ── 4. Wait for /healthz ───────────────────────────────────────────
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8788/healthz >/dev/null 2>&1; then
    say "Backend healthy after ${i}s"
    break
  fi
  sleep 1
done

curl -fsS http://127.0.0.1:8788/healthz || {
  say "Backend did not come up — check 'docker logs pi-backend'"
  exit 1
}

say "Cutover complete. Public URL: https://digi-setu.com"
say "If anything goes sideways, the legacy data lives under /srv/pi/legacy-backup/"
