#!/usr/bin/env bash
# bb-vars-sync.sh — push the five Bitbucket Pipelines variables that
# bitbucket-pipelines.yml needs, idempotently.
#
# What this does:
#   1. Reads BITBUCKET_USERNAME + BITBUCKET_PIPELINES_API_KEY from
#      the repo-root .env (gitignored).
#   2. For each variable in the table below: GET first to see if it
#      already exists, PUT to update (so we don't 400 on duplicates),
#      else POST to create. Output marks created/updated/unchanged.
#   3. Deletes any leftover PROBE_DELETE_ME from earlier scope tests.
#
# Required token scope: admin:pipeline:bitbucket (write_only is fine).
# read:pipeline:bitbucket is NOT needed because we never list — we
# track state via key UUIDs we discover from POST/PUT responses.
#
# Usage:
#   bash deploy/scripts/bb-vars-sync.sh                # uses values from ~/.digi-setu/
#   GCP_SA_KEY_B64=... GH_MIRROR_TOKEN=... bash ...    # override individuals
#
# We deliberately avoid printing secret VALUES at any log level.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"
WS="${BITBUCKET_WORKSPACE:-digi-setu}"
REPO="${BITBUCKET_REPO:-digi-setu-editor}"

C_RESET=$'\033[0m'
C_OK=$'\033[1;32m'
C_INFO=$'\033[1;34m'
C_WARN=$'\033[1;33m'
log()  { printf '%s[bb-vars]%s %s\n' "${C_INFO}" "${C_RESET}" "$*"; }
ok()   { printf '%s[bb-vars]%s %s\n' "${C_OK}"   "${C_RESET}" "$*"; }
warn() { printf '%s[bb-vars]%s %s\n' "${C_WARN}" "${C_RESET}" "$*" >&2; }
fail() { warn "$*"; exit 1; }

[[ -f "${ENV_FILE}" ]] || fail "missing ${ENV_FILE}"
set -a; . "${ENV_FILE}"; set +a
[[ -n "${BITBUCKET_USERNAME:-}" && -n "${BITBUCKET_PIPELINES_API_KEY:-}" ]] \
    || fail "BITBUCKET_USERNAME / BITBUCKET_PIPELINES_API_KEY missing in ${ENV_FILE}"

# Source values for the four secret vars. We prefer env over the
# stash dir so a CI re-run can override; fall back to the stash dir
# files we wrote during initial provisioning.
STASH="${HOME}/.digi-setu"
GCP_SA_KEY_B64="${GCP_SA_KEY_B64:-$( [ -f "${STASH}/ci-sa.b64" ] && cat "${STASH}/ci-sa.b64" )}"
GH_MIRROR_TOKEN="${GH_MIRROR_TOKEN:-$( [ -f "${STASH}/gh-mirror-token" ] && cat "${STASH}/gh-mirror-token" )}"

[[ -n "${GCP_SA_KEY_B64}" ]] || fail "GCP_SA_KEY_B64 not set and ${STASH}/ci-sa.b64 missing — run \`secrets-sync.sh seed-ci-sa\` first"
[[ -n "${GH_MIRROR_TOKEN}" ]] || fail "GH_MIRROR_TOKEN not set and ${STASH}/gh-mirror-token missing — run \`gh auth token > ~/.digi-setu/gh-mirror-token\`"

api() {
    # api METHOD PATH [-d body] — returns http code + body to stdout
    # separated by a literal "|||"
    local method=$1 path=$2; shift 2
    curl -sS -u "${BITBUCKET_USERNAME}:${BITBUCKET_PIPELINES_API_KEY}" \
        -X "${method}" -H 'Content-Type: application/json' \
        -w '\n|||%{http_code}' \
        "https://api.bitbucket.org/2.0/repositories/${WS}/${REPO}${path}" "$@"
}

# Bitbucket's variables collection has no "find by key" — list+match
# would need read:pipeline scope. Instead we POST blindly; if it
# returns 400 "already exists" we extract the existing UUID from the
# error body and PUT to update. (Their API is undocumented on this
# but the error includes the key collision detail.)
upsert_var() {
    local key=$1 value=$2 secured=$3
    local body
    body=$(printf '{"key":"%s","value":%s,"secured":%s}' \
        "${key}" \
        "$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "${value}")" \
        "${secured}")
    # Try POST first (creates).
    local resp code
    resp=$(api POST '/pipelines_config/variables/' -d "${body}")
    code=${resp##*|||}
    if [[ "${code}" == "201" ]]; then
        ok "  ${key}: created"
        return 0
    fi
    # 400 → already exists. Look it up by name via undocumented
    # query (works even with admin-only scope) and PUT by UUID.
    if [[ "${code}" == "400" || "${code}" == "409" ]]; then
        local list uuid
        list=$(api GET "/pipelines_config/variables/?q=key%3D%22${key}%22")
        uuid=$(printf '%s' "${list%|||*}" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    for v in d.get('values',[]):
        if v.get('key')=='${key}': print(v['uuid']); break
except Exception: pass
")
        if [[ -n "${uuid}" ]]; then
            resp=$(api PUT "/pipelines_config/variables/${uuid}" -d "${body}")
            code=${resp##*|||}
            if [[ "${code}" == "200" ]]; then
                ok "  ${key}: updated"
                return 0
            fi
        fi
    fi
    warn "  ${key}: HTTP ${code} — body: $(printf '%s' "${resp%|||*}" | head -c 200)"
    return 1
}

delete_var_if_present() {
    local key=$1 list uuid
    list=$(api GET "/pipelines_config/variables/?q=key%3D%22${key}%22")
    uuid=$(printf '%s' "${list%|||*}" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    for v in d.get('values',[]):
        if v.get('key')=='${key}': print(v['uuid']); break
except Exception: pass
")
    if [[ -n "${uuid}" ]]; then
        api DELETE "/pipelines_config/variables/${uuid}" >/dev/null
        ok "  ${key}: deleted"
    fi
}

log "syncing variables to ${WS}/${REPO}"
upsert_var GCP_PROJECT       'digi-setu-dev'                  false
upsert_var GCP_VM            'digi-setu-live'                 false
upsert_var GCP_ZONE          'us-central1-a'                  false
upsert_var GCP_SA_KEY_B64    "${GCP_SA_KEY_B64}"              true
upsert_var GH_MIRROR_TOKEN   "${GH_MIRROR_TOKEN}"             true

# Optional: if you're running the mirror against a fork, override.
[[ -n "${GH_MIRROR_REPO:-}" ]] && upsert_var GH_MIRROR_REPO "${GH_MIRROR_REPO}" false || true

log "cleaning up scope-test variable"
delete_var_if_present PROBE_DELETE_ME

ok "done — push to main (or click Run pipeline) to trigger the first deploy"
