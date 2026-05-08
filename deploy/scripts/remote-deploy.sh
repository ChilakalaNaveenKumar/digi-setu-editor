#!/usr/bin/env bash
# remote-deploy.sh — laptop-side orchestrator for the pi-typst-test
# hosted deployment to digi-setu-live (the existing VM in
# digi-setu-dev/us-central1-a that previously hosted typst-agent).
#
# Pipeline:
#
#   1. Cloud Build the backend image → Artifact Registry
#      us-central1-docker.pkg.dev/digi-setu-dev/digi-setu/pi-backend
#      tags both :<git-sha> and :latest.
#
#   2. Build the Vue 3 SPA inside a deterministic Node container,
#      stream the resulting `dist/` to /srv/pi/www on the VM.
#
#   3. `gcloud compute scp` the deploy bundle (compose + caddy +
#      systemd) to /opt/pi/ on the VM.
#
#   4. ssh: install systemd units, run pi-prepare.service, docker
#      login to AR via the VM's metadata-server token, docker compose
#      pull + up -d, restart pi.service.
#
# Usage:
#   scripts/remote-deploy.sh                 # full deploy (no cutover)
#   scripts/remote-deploy.sh backend         # only backend image + roll
#   scripts/remote-deploy.sh frontend        # only the SPA
#   scripts/remote-deploy.sh stack           # only compose/caddy/systemd
#   scripts/remote-deploy.sh cutover         # stop typst-agent, start pi
#   scripts/remote-deploy.sh logs            # tail backend + caddy logs
#   scripts/remote-deploy.sh ssh             # interactive shell on the VM
#   DRY_RUN=1 scripts/remote-deploy.sh ...   # print commands, don't run
#
# Required tools on the operator's machine:
#   - gcloud (authenticated against digi-setu-dev)
#   - docker (only used for the local SPA build container)

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────
PROJECT="${GCP_PROJECT:-digi-setu-dev}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
VM="${GCP_VM:-digi-setu-live}"
AR_HOST="${AR_HOST:-us-central1-docker.pkg.dev}"
AR_REPO="${AR_REPO:-digi-setu}"
BACKEND_IMAGE="${AR_HOST}/${PROJECT}/${AR_REPO}/pi-backend"
REMOTE_ROOT="${REMOTE_ROOT:-/opt/pi}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M)}"

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_DIR="${REPO_ROOT}/deploy"

TARGET="${1:-all}"
DRY_RUN="${DRY_RUN:-0}"

# ── Helpers ────────────────────────────────────────────────────────
log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[deploy]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[deploy]\033[0m %s\n' "$*" >&2; exit 1; }

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+ %s\n' "$*"
  else
    printf '+ %s\n' "$*"
    "$@"
  fi
}

ssh_remote() {
  # OS Login + project SSH keys do not populate ~/.ssh for raw `ssh
  # ubuntu@<external-ip>` — always hop through `gcloud compute ssh`.
  if [[ "$#" -ne 1 ]]; then
    fail "ssh_remote expects exactly one shell-string argument"
  fi
  local cmd="$1"
  local enc
  enc="$(printf '%s' "${cmd}" | base64 | tr -d '\n')"
  run gcloud compute ssh "${VM}" \
    --project "${PROJECT}" \
    --zone "${ZONE}" \
    --strict-host-key-checking=yes \
    --command="echo '${enc}' | base64 -d | bash -s"
}

scp_remote() {
  local src="$1" dst="$2"
  run gcloud compute scp --recurse \
    --project "${PROJECT}" \
    --zone "${ZONE}" \
    --strict-host-key-checking=yes \
    "${src}" "${VM}:${dst}"
}

# ── Step 1: backend image via Cloud Build ─────────────────────────
build_backend() {
  log "submitting backend image ${BACKEND_IMAGE}:${TAG} to Cloud Build"
  cd "${REPO_ROOT}"
  run gcloud builds submit \
    --project "${PROJECT}" \
    --region "${REGION}" \
    --config /dev/stdin \
    --substitutions "_TAG=${TAG}" \
    "${REPO_ROOT}" <<'YAML'
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - --file
      - deploy/Dockerfile.backend
      - --tag
      - ${_BACKEND_IMAGE}:${_TAG}
      - --tag
      - ${_BACKEND_IMAGE}:latest
      - --cache-from
      - ${_BACKEND_IMAGE}:latest
      - .
images:
  - ${_BACKEND_IMAGE}:${_TAG}
  - ${_BACKEND_IMAGE}:latest
substitutions:
  _BACKEND_IMAGE: us-central1-docker.pkg.dev/digi-setu-dev/digi-setu/pi-backend
  _TAG: latest
options:
  machineType: E2_HIGHCPU_8
  logging: CLOUD_LOGGING_ONLY
timeout: 2400s
YAML
}

# ── Step 2: frontend SPA build (local, container) ─────────────────
build_frontend() {
  log "building Vue SPA via deploy/Dockerfile.frontend"
  cd "${REPO_ROOT}"
  run docker build \
    -t pi-frontend:${TAG} \
    -t pi-frontend:latest \
    -f deploy/Dockerfile.frontend \
    "${REPO_ROOT}"
}

# ── Step 3: ensure remote layout exists (idempotent) ──────────────
ensure_remote_dirs() {
  ssh_remote "set -e
sudo install -d -m 0700 /opt/pi
sudo install -d -m 0755 /opt/pi/caddy
sudo install -d -m 0755 /opt/pi/systemd
sudo install -d -m 0755 /opt/pi/nftables
sudo install -d -m 0755 /opt/pi/scripts
U=\$(id -un); G=\$(id -gn)
sudo chown -R \"\${U}:\${G}\" /opt/pi

# /srv layout the pi-prepare.service later re-asserts.
sudo install -d -m 0700 -o 0    -g 0    /srv/pi/state
sudo install -d -m 0700 -o 1100 -g 1100 /srv/pi/data
sudo install -d -m 0700 -o 1100 -g 1100 /srv/pi/data/workspaces
sudo install -d -m 0700 -o 1100 -g 1100 /srv/pi/data/chats
sudo install -d -m 0700 -o 1100 -g 1100 /srv/pi/data/shadows
sudo install -d -m 0755 -o 0    -g 0    /srv/pi/www
sudo install -d -m 0700 -o 0    -g 0    /srv/caddy/data /srv/caddy/config
"
}

# ── Step 4: push compose + caddy + systemd to VM ──────────────────
push_stack() {
  log "pushing compose stack → ${VM}:${REMOTE_ROOT}"
  ensure_remote_dirs
  scp_remote "${DEPLOY_DIR}/docker-compose.yml"                  "${REMOTE_ROOT}/docker-compose.yml"
  scp_remote "${DEPLOY_DIR}/caddy/Caddyfile"                     "${REMOTE_ROOT}/caddy/Caddyfile"
  scp_remote "${DEPLOY_DIR}/caddy/Dockerfile"                    "${REMOTE_ROOT}/caddy/Dockerfile"
  scp_remote "${DEPLOY_DIR}/systemd/pi.service"                  "${REMOTE_ROOT}/systemd/pi.service"
  scp_remote "${DEPLOY_DIR}/systemd/pi-prepare.service"          "${REMOTE_ROOT}/systemd/pi-prepare.service"
  scp_remote "${DEPLOY_DIR}/systemd/pi-firewall.service"         "${REMOTE_ROOT}/systemd/pi-firewall.service"
  scp_remote "${DEPLOY_DIR}/nftables/pi-egress.nft"              "${REMOTE_ROOT}/nftables/pi-egress.nft"
  scp_remote "${DEPLOY_DIR}/scripts/cutover-from-typst-agent.sh" "${REMOTE_ROOT}/scripts/cutover-from-typst-agent.sh"
  scp_remote "${DEPLOY_DIR}/scripts/backup-to-gcs.sh"            "${REMOTE_ROOT}/scripts/backup-to-gcs.sh"

  # stack.env — only push if the operator generated it locally. Otherwise
  # we expect it to already exist on the VM (rotated via gcloud secrets).
  if [[ -f "${DEPLOY_DIR}/stack.env" ]]; then
    log "pushing local stack.env (mode 0600 on remote)"
    scp_remote "${DEPLOY_DIR}/stack.env" "${REMOTE_ROOT}/stack.env"
    ssh_remote "sudo chown root:root ${REMOTE_ROOT}/stack.env && sudo chmod 0600 ${REMOTE_ROOT}/stack.env"
  elif ! ssh_remote "test -f ${REMOTE_ROOT}/stack.env" >/dev/null 2>&1; then
    log "stack.env missing on VM — seeding from example (EDIT IT BEFORE NEXT RESTART)"
    scp_remote "${DEPLOY_DIR}/stack.env.example" "${REMOTE_ROOT}/stack.env"
    ssh_remote "sudo chown root:root ${REMOTE_ROOT}/stack.env && sudo chmod 0600 ${REMOTE_ROOT}/stack.env"
  fi

  ssh_remote "set -e
# Install systemd units.
sudo install -m 0644 ${REMOTE_ROOT}/systemd/pi.service          /etc/systemd/system/pi.service
sudo install -m 0644 ${REMOTE_ROOT}/systemd/pi-prepare.service  /etc/systemd/system/pi-prepare.service
sudo install -m 0644 ${REMOTE_ROOT}/systemd/pi-firewall.service /etc/systemd/system/pi-firewall.service

# Install nftables ruleset (drop the metadata server for uid 1100).
sudo install -d -m 0755 /etc/nftables.d
sudo install -m 0644 ${REMOTE_ROOT}/nftables/pi-egress.nft /etc/nftables.d/pi-egress.nft

# Make sure nftables is installed (firewall unit needs the binary).
if ! command -v nft >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends nftables
fi

# Make scripts executable.
sudo chmod +x ${REMOTE_ROOT}/scripts/cutover-from-typst-agent.sh
sudo chmod +x ${REMOTE_ROOT}/scripts/backup-to-gcs.sh

sudo systemctl daemon-reload
sudo systemctl enable pi-prepare.service pi-firewall.service pi.service

# Start the firewall NOW so the metadata-server hole is closed even
# before pi.service (re)starts. nftables rules apply immediately.
sudo systemctl restart pi-firewall.service
sudo nft list ruleset | grep -A 6 'table inet pi_egress' | head -10
"
}

# ── Step 5: stream the Vue dist to /srv/pi/www ────────────────────
push_frontend() {
  log "pushing Vue SPA → ${VM}:/srv/pi/www"
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+ docker run --rm pi-frontend | ssh tar -x → /srv/pi/www\n'
    return 0
  fi
  printf '+ streaming dist/ → %s:/srv/pi/www (tar over gcloud ssh)\n' "${VM}"
  docker run --rm pi-frontend:${TAG} | gcloud compute ssh "${VM}" \
    --project "${PROJECT}" \
    --zone "${ZONE}" \
    --strict-host-key-checking=yes \
    --command='sudo install -d -m 0755 -o root -g root /srv/pi/www && sudo find /srv/pi/www -mindepth 1 -delete && sudo tar xf - -C /srv/pi/www'
}

# ── Step 6: pull the new image + reload the stack ─────────────────
roll_stack() {
  log "rolling docker compose on ${VM} (image tag ${TAG})"
  ssh_remote "set -e
cd ${REMOTE_ROOT}
test -f ./stack.env || { echo 'ERROR: ${REMOTE_ROOT}/stack.env missing — populate it before rolling' >&2; exit 1; }

# Pin BACKEND_IMAGE to the freshly-pushed tag so this rollout is
# deterministic. Subsequent reloads can flip back to :latest if you
# prefer rolling tags.
sudo sed -i 's|^BACKEND_IMAGE=.*|BACKEND_IMAGE=${BACKEND_IMAGE}:${TAG}|' ./stack.env

# AR pull auth via the VM's attached service-account token.
TOK=\$(curl -fsS -H 'Metadata-Flavor: Google' \\
  'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token' \\
  | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"access_token\"])')
echo \"\${TOK}\" | sudo docker login -u oauth2accesstoken --password-stdin https://${AR_HOST}

sudo systemctl restart pi-prepare.service
sudo systemctl restart pi.service
sleep 5
sudo systemctl status --no-pager pi.service | sed -n '1,12p'

# Caddyfile is bind-mounted — `up -d` does NOT detect that change on
# its own. Reload Caddy in-place so config edits go live without
# dropping in-flight TLS connections.
if sudo docker ps --format '{{.Names}}' | grep -q '^pi-caddy$'; then
  sudo docker exec pi-caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || \\
    sudo docker compose --env-file ${REMOTE_ROOT}/stack.env -f ${REMOTE_ROOT}/docker-compose.yml restart caddy
fi
"
}

cutover() {
  log "running cutover-from-typst-agent.sh on ${VM} (stops typst-agent.service, starts pi.service)"
  ssh_remote "sudo bash ${REMOTE_ROOT}/scripts/cutover-from-typst-agent.sh"
}

health_check() {
  log "waiting on https://digi-setu.com/healthz"
  for _ in $(seq 1 60); do
    if curl -fsS https://digi-setu.com/healthz >/dev/null 2>&1; then
      log "✓ healthy"
      return 0
    fi
    sleep 5
  done
  warn "health endpoint did not return 200 within 5 minutes"
  return 1
}

logs() {
  ssh_remote "sudo docker logs --tail 100 pi-backend; echo === caddy ===; sudo docker logs --tail 60 pi-caddy"
}

ssh_into() {
  exec gcloud compute ssh "${VM}" --project "${PROJECT}" --zone "${ZONE}"
}

# ── Dispatch ───────────────────────────────────────────────────────
case "${TARGET}" in
  all)
    build_backend
    build_frontend
    push_stack
    push_frontend
    roll_stack
    health_check || true
    ;;
  backend)
    build_backend
    push_stack
    roll_stack
    health_check || true
    ;;
  frontend)
    build_frontend
    push_frontend
    log "Caddy serves a read-only mount of /srv/pi/www — new bundle is live immediately."
    ;;
  stack)
    push_stack
    roll_stack
    ;;
  cutover)
    cutover
    health_check || true
    ;;
  logs)
    logs
    ;;
  ssh)
    ssh_into
    ;;
  health)
    health_check
    ;;
  *)
    cat >&2 <<EOF
Unknown target: ${TARGET}
Usage: scripts/remote-deploy.sh [all|backend|frontend|stack|cutover|logs|ssh|health]
EOF
    exit 64
    ;;
esac
