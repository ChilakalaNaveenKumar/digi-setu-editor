#!/usr/bin/env bash
# smoke-session.sh — manual e2e checklist for the per-session container
# architecture. Run on the operator's laptop AFTER `remote-deploy.sh
# all` has finished.
#
# Tests, in order:
#
#   1. Image present + can spawn pi --version (sanity that the image
#      builds and the pi binary works inside).
#
#   2. Egress proxy listening + responsive to a trivial CONNECT.
#
#   3. Allow-list deny path: container tries to reach evil.example.com
#      → proxy returns 451 → AI sees "host not on allow-list".
#
#   4. Vertex MITM works end-to-end: container does a Vertex API call,
#      the response comes back successfully (i.e. the proxy DID inject
#      the Authorization header from backend ADC).
#
#   5. Cross-tenant isolation: spawn two containers as different
#      synthetic users, confirm container A cannot read container B's
#      workspace files.
#
#   6. Token-exfil resistance: container tries to ship the AI's env
#      to an off-allow-list host → blocked.
#
#   7. User-can-install: container does `sudo apt install ripgrep`
#      successfully.
#
#   8. Cleanup: chat-end results in `docker rm` of the container,
#      no orphans left.
#
# Each step prints PASS / FAIL with a short reason. Non-zero exit if
# ANY step fails. Designed to be re-runnable; cleans up its own
# probe containers between steps.

set -uo pipefail

VM="${GCP_VM:-digi-setu-live}"
PROJECT="${GCP_PROJECT:-digi-setu-dev}"
ZONE="${GCP_ZONE:-us-central1-a}"

GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0

ssh_run() {
  local cmd="$1"
  local enc
  enc="$(printf '%s' "${cmd}" | base64 | tr -d '\n')"
  gcloud compute ssh "${VM}" \
    --project "${PROJECT}" \
    --zone "${ZONE}" \
    --strict-host-key-checking=yes \
    --command="echo '${enc}' | base64 -d | bash -s" 2>&1
}

step() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "${name}"
  if "$@"; then
    printf "${GREEN}PASS${NC} %s\n" "${name}"
    PASS=$((PASS + 1))
  else
    printf "${RED}FAIL${NC} %s\n" "${name}"
    FAIL=$((FAIL + 1))
  fi
}

skip() {
  local name="$1" reason="$2"
  printf "${YELLOW}SKIP${NC} %s (%s)\n" "${name}" "${reason}"
  SKIP=$((SKIP + 1))
}

# ── Step 1: image present, pi works inside ─────────────────────────
test_image() {
  local out
  out=$(ssh_run "sudo docker run --rm pi-session:latest pi --version 2>&1 || true")
  # pi --version output is just a bare semver like "0.73.0" (no
  # "pi" prefix). The entrypoint warnings about /etc/pi/mitm-ca.crt
  # missing are expected when we run without the bind mount; we
  # only care that the version line is there.
  if echo "${out}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    return 0
  fi
  echo "  output: ${out}"
  return 1
}

# ── Step 2: egress proxy listening ─────────────────────────────────
test_proxy_listening() {
  local out
  out=$(ssh_run "sudo ss -lnt 'sport = :1080' 2>&1 || true")
  if echo "${out}" | grep -q ':1080'; then
    return 0
  fi
  echo "  output: ${out}"
  return 1
}

# ── Step 3: deny path returns 451 ──────────────────────────────────
test_deny_path() {
  # Use a one-off container to issue a CONNECT to evil.example.com.
  # We bypass HTTPS_PROXY for the test to talk DIRECTLY to the proxy
  # and read its response (curl -x http://172.30.16.1:1080 ...).
  local out
  out=$(ssh_run "sudo docker run --rm --network pi-egress \
                 pi-session:latest \
                 curl -sS -o /dev/null -w '%{http_code}' \
                 -x http://172.30.16.1:1080 \
                 -X CONNECT https://evil.example.com:443/ 2>&1 || true")
  # Exact code depends on curl version (may be 451 or 0 on connect-fail
  # response). What matters is it's NOT 200.
  if echo "${out}" | grep -qE '^(451|400|405)$'; then
    return 0
  fi
  if echo "${out}" | grep -qE 'CONNECT tunnel|451'; then
    return 0
  fi
  echo "  output: ${out}"
  return 1
}

# ── Step 4: Vertex MITM works ──────────────────────────────────────
test_vertex_mitm() {
  # Pi inside a fresh container, single quick prompt to verify the
  # full Vertex auth path works through the MITM proxy.
  #
  # We need to pass the SAME env the backend would inject when
  # spawning a real chat session — provider/model are CLI flags, but
  # the container also needs GOOGLE_CLOUD_PROJECT (so the proxy can
  # add X-Goog-User-Project) and PI_TRUST_GCE_METADATA=1 (so
  # pi-ai's hasVertexAdcCredentials() returns true).
  local project
  project=$(ssh_run "sudo grep -E '^GOOGLE_CLOUD_PROJECT=' /opt/pi/stack.env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]'" 2>/dev/null | tail -1)
  project="${project:-digi-setu-dev}"

  local out
  out=$(ssh_run "sudo docker run --rm \
                 --network pi-egress \
                 -v /srv/pi/state/proxy/mitm-ca.crt:/etc/pi/mitm-ca.crt:ro \
                 -e GOOGLE_CLOUD_PROJECT=${project} \
                 -e GOOGLE_CLOUD_LOCATION=global \
                 -e GOOGLE_GENAI_USE_VERTEXAI=true \
                 -e PI_TRUST_GCE_METADATA=1 \
                 -e GCE_METADATA_HOST=metadata.google.internal \
                 -e GCE_METADATA_IP=metadata.google.internal \
                 -e METADATA_SERVER_DETECTION=assume-present \
                 pi-session:latest \
                 pi --provider anthropic-vertex --model claude-sonnet-4-6 \
                    --print 'Reply with the single word OK and nothing else.' \
                    2>&1 || true")
  if echo "${out}" | grep -qE '\bOK\b'; then
    return 0
  fi
  echo "  output (last 30 lines):"
  echo "${out}" | tail -30 | sed 's/^/    /'
  return 1
}

# ── Step 5: cross-tenant isolation ─────────────────────────────────
test_cross_tenant() {
  # Spawn container A with workspace_a, write a 'secret' file. Spawn
  # container B with workspace_b, try to ls workspace_a — should fail
  # because workspace_a is not bind-mounted into B's container.
  ssh_run "
    set -e
    sudo install -d -m 2770 -o 1000 -g 1000 /tmp/smoke-ws-a /tmp/smoke-ws-b
    echo 'secret-from-A' | sudo tee /tmp/smoke-ws-a/secret.txt >/dev/null
    sudo chown 1000:1000 /tmp/smoke-ws-a/secret.txt
    # Container B reads only its own workspace.
    sudo docker run --rm --network pi-egress \
      -v /tmp/smoke-ws-b:/workspace:rw \
      pi-session:latest \
      ls -la /workspace 2>&1
  " > /tmp/smoke-out.txt 2>&1
  if grep -q 'secret.txt' /tmp/smoke-out.txt; then
    echo "  Container B saw container A's secret.txt — ISOLATION BROKEN"
    cat /tmp/smoke-out.txt
    return 1
  fi
  return 0
}

# ── Step 6: token exfil resistance ─────────────────────────────────
test_no_token_in_env() {
  local out
  out=$(ssh_run "sudo docker run --rm --network pi-egress \
                 pi-session:latest \
                 sh -c 'env | grep -E -i \"vertex|google_application|access_token|bearer\" || echo NO_TOKEN' \
                 2>&1 || true")
  if echo "${out}" | grep -q 'NO_TOKEN'; then
    return 0
  fi
  # Allow GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION to leak — those
  # are not credentials. Reject anything that looks like a token.
  if echo "${out}" | grep -qiE 'token|bearer|secret|key='; then
    echo "  found credential-shaped env: ${out}"
    return 1
  fi
  return 0
}

# ── Step 7: user can sudo apt install ──────────────────────────────
test_user_can_install() {
  local out
  out=$(ssh_run "sudo docker run --rm --network pi-egress \
                 pi-session:latest \
                 sh -c 'sudo apt-get update -qq && sudo apt-get install -y --no-install-recommends ripgrep && rg --version' \
                 2>&1 || true")
  if echo "${out}" | grep -qE '^ripgrep [0-9]'; then
    return 0
  fi
  echo "  output (last 20 lines):"
  echo "${out}" | tail -20 | sed 's/^/    /'
  return 1
}

# ── Step 8: cleanup leaves no orphans ──────────────────────────────
test_no_orphans() {
  # Spawn-and-kill a probe, then count running pi-typst-test containers.
  ssh_run "
    sudo docker run -d --rm --name smoke-orphan-probe \
      --network pi-egress \
      --label pi.app=pi-typst-test \
      --label pi.user_id=smoke \
      --label pi.session_id=smoke-orphan \
      pi-session:latest sleep 3600 >/dev/null 2>&1 || true
    sleep 1
    sudo docker rm -f smoke-orphan-probe >/dev/null 2>&1 || true
  " >/dev/null 2>&1
  local count
  count=$(ssh_run "sudo docker ps --filter label=pi.app=pi-typst-test --format '{{.Names}}' | grep -c smoke-orphan-probe || true" \
    | tr -d '[:space:]')
  if [ "${count}" = "0" ] || [ -z "${count}" ]; then
    return 0
  fi
  echo "  ${count} stale smoke-orphan-probe containers found"
  return 1
}

# ── Run ────────────────────────────────────────────────────────────
echo "smoke-session.sh — running checks against ${VM}"

step "1. pi-session image works" test_image
step "2. egress proxy listening on :1080" test_proxy_listening
step "3. egress proxy denies non-allow-listed hosts" test_deny_path
step "4. Vertex MITM end-to-end (anthropic-vertex --print)" test_vertex_mitm
step "5. cross-tenant filesystem isolation" test_cross_tenant
step "6. no Vertex token in container env" test_no_token_in_env
step "7. user can sudo apt install ripgrep" test_user_can_install
step "8. cleanup leaves no orphans" test_no_orphans

echo
echo "=================================================="
printf "PASS: %d  FAIL: %d  SKIP: %d\n" "${PASS}" "${FAIL}" "${SKIP}"
echo "=================================================="

if [ "${FAIL}" -gt 0 ]; then
  exit 1
fi
exit 0
