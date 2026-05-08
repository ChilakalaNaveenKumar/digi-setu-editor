#!/usr/bin/env bash
# provision-vm.sh — bring a fresh Debian/Ubuntu VM up to the baseline
# pi.service expects. Idempotent; safe to re-run.
#
# What it does:
#   1. apt-get install docker engine + compose plugin
#   2. ensure /srv/pi + /srv/caddy + /opt/pi exist with correct owners
#   3. install systemd units (pi + pi-prepare)
#
# Run this BEFORE scripts/remote-deploy.sh on a brand-new box. After
# this completes, the VM still has no /opt/pi/{docker-compose.yml,
# stack.env} — that's remote-deploy.sh's job.
#
# DRY_RUN=1 prints the commands without executing them.

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
say() { printf '\033[1;36m[provision]\033[0m %s\n' "$*"; }
run() { say "$*"; [[ "$DRY_RUN" == "1" ]] || eval "$@"; }

if [[ "$EUID" -ne 0 ]]; then
  echo "provision-vm.sh must run as root (sudo $0)" >&2
  exit 1
fi

# ── 1. Docker engine + compose plugin ──────────────────────────────
say "Installing docker engine + compose plugin (idempotent)…"
if ! command -v docker >/dev/null 2>&1; then
  run "curl -fsSL https://get.docker.com | sh"
fi
run "systemctl enable --now docker"

# ── 2. /srv layout ─────────────────────────────────────────────────
# uid 1100 inside the backend container = our `app` user. The host
# doesn't need an `app` user — we chown by NUMBER and the kernel only
# checks numeric IDs when enforcing bind-mount perms.
say "Materialising /srv/pi and /srv/caddy…"
run "install -d -m 0700 -o 0    -g 0    /srv/pi/state"
run "install -d -m 0700 -o 1100 -g 1100 /srv/pi/data"
run "install -d -m 0700 -o 1100 -g 1100 /srv/pi/data/workspaces"
run "install -d -m 0700 -o 1100 -g 1100 /srv/pi/data/chats"
run "install -d -m 0700 -o 1100 -g 1100 /srv/pi/data/shadows"
run "install -d -m 0755 -o 0    -g 0    /srv/pi/www"
run "install -d -m 0700 -o 0    -g 0    /srv/caddy/data"
run "install -d -m 0700 -o 0    -g 0    /srv/caddy/config"
run "install -d -m 0700 -o 0    -g 0    /opt/pi"

# ── 3. systemd units ───────────────────────────────────────────────
HERE="$(cd "$(dirname "$0")/.." && pwd)"
say "Installing systemd units from $HERE/systemd/…"
run "install -m 0644 \"$HERE/systemd/pi.service\"         /etc/systemd/system/pi.service"
run "install -m 0644 \"$HERE/systemd/pi-prepare.service\" /etc/systemd/system/pi-prepare.service"
run "systemctl daemon-reload"
run "systemctl enable pi-prepare.service"
run "systemctl enable pi.service"

say "Done. Next step: scripts/remote-deploy.sh all"
