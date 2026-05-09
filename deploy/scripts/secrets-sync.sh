#!/usr/bin/env bash
# secrets-sync.sh — single source of truth for production secrets.
#
# WHY THIS EXISTS:
#   Before this script, secrets lived in two scary places: the
#   developer's `deploy/stack.env` on disk (mode 0600 but still
#   plaintext on a laptop) and on the VM at /opt/pi/stack.env. Rotation
#   meant SSH-and-vi, with no audit log. This script puts the canonical
#   copy in Google Secret Manager (project: digi-setu-dev) and gives
#   you four operations: push, pull, list, materialize.
#
# Operations:
#
#   secrets-sync.sh push [KEY...]
#       Read each KEY from local stack.env and add a new version of
#       the matching GSM secret. With no KEY args, pushes every
#       secret listed in MANAGED_KEYS below. Idempotent; if the GSM
#       value already matches the local one, no new version is
#       created (saves your $0.06/secret/month and keeps the version
#       history readable).
#
#   secrets-sync.sh pull KEY
#       Print the current GSM value for KEY to stdout. Useful in
#       shell pipelines (`KEY=$(./secrets-sync.sh pull CLERK_SECRET_KEY)`).
#
#   secrets-sync.sh pull-all > /tmp/stack.env
#       Materialize every managed secret to a stack.env-shaped file
#       on stdout. The file you'd previously sit on a USB stick.
#
#   secrets-sync.sh list
#       Show which managed secrets exist in GSM and their newest
#       version + create-time. Doesn't print values.
#
#   secrets-sync.sh seed-iam
#       Grant the VM's attached service account
#       digi-setu-live@digi-setu-dev.iam.gserviceaccount.com the
#       roles/secretmanager.secretAccessor role on every managed
#       secret. Idempotent. Run this after creating new secrets.
#
# The script never prints secret VALUES to terminal logs except in
# `pull` / `pull-all` (which are explicitly value-returning). Even
# `push` prints "ok / unchanged / created" without echoing the value.

set -euo pipefail

PROJECT="${GCP_PROJECT:-digi-setu-dev}"
VM_SA="${VM_SA:-digi-setu-live@digi-setu-dev.iam.gserviceaccount.com}"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
STACK_ENV="${STACK_ENV:-${REPO_ROOT}/deploy/stack.env}"

# The exhaustive list of secrets we manage from this script. Adding
# a new secret = add it here + push it. Anything not in this list
# stays plain-config in stack.env (price IDs, image refs, etc.) so
# the cost + audit overhead of GSM only kicks in for actual secrets.
MANAGED_KEYS=(
    CLOUDFLARE_API_TOKEN
    GEMINI_API_KEY
    CLERK_SECRET_KEY
    CLERK_WEBHOOK_SECRET
    STRIPE_SECRET_KEY
    STRIPE_WEBHOOK_SECRET
    # Desktop-build-only: baked into the .app at compile time so
    # Finder-launched bundles ship with prod Clerk creds. The release
    # script (desktop/scripts/release.sh) pulls these via `pull`.
    CLERK_PUBLISHABLE_KEY_PROD
    CLERK_SECRET_KEY_PROD
)

log()  { printf '\033[1;34m[secrets]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[secrets]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[secrets]\033[0m %s\n' "$*" >&2; exit 1; }

require_gcloud() {
    command -v gcloud >/dev/null 2>&1 || fail "gcloud not on PATH"
    local active
    active=$(gcloud config get-value account 2>/dev/null || true)
    [[ -n "${active}" ]] || fail "no active gcloud account; run 'gcloud auth login'"
}

# Read a single KEY from stack.env, stripping surrounding quotes.
# Returns empty when the key is absent (caller decides if that's
# fatal). Doesn't source the file because stack.env can contain
# values with spaces / shell metachars that would break in a
# `set -a` context.
local_value() {
    local key="$1"
    [[ -f "${STACK_ENV}" ]] || return 0
    local line
    line=$(grep -E "^${key}=" "${STACK_ENV}" | tail -n 1 || true)
    [[ -z "${line}" ]] && return 0
    line="${line#${key}=}"
    line="${line#\"}"; line="${line%\"}"
    line="${line#\'}"; line="${line%\'}"
    printf '%s' "${line}"
}

gsm_value() {
    local key="$1"
    gcloud secrets versions access latest \
        --project "${PROJECT}" \
        --secret "${key}" 2>/dev/null || true
}

ensure_secret() {
    local key="$1"
    if ! gcloud secrets describe "${key}" \
        --project "${PROJECT}" >/dev/null 2>&1; then
        log "creating GSM secret: ${key}"
        gcloud secrets create "${key}" \
            --project "${PROJECT}" \
            --replication-policy automatic >/dev/null
    fi
}

push_one() {
    local key="$1"
    local local_v gsm_v
    local_v=$(local_value "${key}")
    if [[ -z "${local_v}" ]]; then
        warn "skip ${key} — not in ${STACK_ENV}"
        return 0
    fi
    ensure_secret "${key}"
    gsm_v=$(gsm_value "${key}")
    if [[ "${local_v}" == "${gsm_v}" ]]; then
        log "${key}: unchanged"
        return 0
    fi
    # Pipe via /dev/stdin so we never write the secret to a file.
    printf '%s' "${local_v}" | gcloud secrets versions add "${key}" \
        --project "${PROJECT}" \
        --data-file=- >/dev/null
    log "${key}: new version added"
}

pull_one() {
    local key="$1"
    local v
    v=$(gsm_value "${key}")
    [[ -z "${v}" ]] && fail "secret ${key} not found in GSM project ${PROJECT}"
    printf '%s\n' "${v}"
}

pull_all() {
    require_gcloud
    printf '# Auto-materialized from Google Secret Manager (%s)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '# Do NOT commit this file. Regenerate via:\n'
    printf '#   deploy/scripts/secrets-sync.sh pull-all > /tmp/stack.env\n\n'
    local k v
    for k in "${MANAGED_KEYS[@]}"; do
        v=$(gsm_value "${k}")
        if [[ -z "${v}" ]]; then
            warn "missing in GSM, skipping: ${k}"
            continue
        fi
        # No quoting around the value — stack.env is read as a docker
        # compose env_file which doesn't interpret shell quoting. If
        # the value happens to contain a literal newline (PEM keys),
        # GSM stores them faithfully and so should we.
        printf '%s=%s\n' "${k}" "${v}"
    done
}

list_secrets() {
    require_gcloud
    log "managed secrets in project ${PROJECT}:"
    printf '%-32s  %-12s  %s\n' KEY VERSION CREATE_TIME
    local k version_info
    for k in "${MANAGED_KEYS[@]}"; do
        version_info=$(gcloud secrets versions list "${k}" \
            --project "${PROJECT}" \
            --filter "state=ENABLED" \
            --sort-by ~createTime \
            --limit 1 \
            --format "value(name,createTime)" 2>/dev/null || true)
        if [[ -z "${version_info}" ]]; then
            printf '%-32s  %-12s  %s\n' "${k}" "—" "(missing)"
        else
            local ver ctime
            ver=$(printf '%s' "${version_info}" | awk '{print $1}')
            ctime=$(printf '%s' "${version_info}" | awk '{print $2}')
            printf '%-32s  %-12s  %s\n' "${k}" "v${ver}" "${ctime}"
        fi
    done
}

seed_iam() {
    require_gcloud
    log "granting roles/secretmanager.secretAccessor to ${VM_SA}"
    local k
    for k in "${MANAGED_KEYS[@]}"; do
        if gcloud secrets describe "${k}" --project "${PROJECT}" >/dev/null 2>&1; then
            gcloud secrets add-iam-policy-binding "${k}" \
                --project "${PROJECT}" \
                --member "serviceAccount:${VM_SA}" \
                --role roles/secretmanager.secretAccessor \
                --condition=None \
                >/dev/null 2>&1 && log "${k}: granted" || warn "${k}: grant failed"
        else
            warn "${k}: secret missing, skip"
        fi
    done
}

# ─────────────────────────────────────────────────────────────────────
# CI service account provisioning (Bitbucket Pipelines + GHA)
#
# Bitbucket Pipelines + GitHub Actions need a service account with
# these roles to run the full release pipeline:
#
#   roles/cloudbuild.builds.editor          submit Cloud Build jobs
#   roles/artifactregistry.writer            push pi-backend / pi-session images
#   roles/secretmanager.secretAccessor       hydrate build.rs's CLERK_*_PROD
#   roles/iap.tunnelResourceAccessor         tunnel for `gcloud compute scp`
#   roles/compute.osLogin                    ssh into digi-setu-live as a user
#   roles/iam.serviceAccountUser             impersonate the VM SA for IAP
#
# We separate this from the VM SA because (a) we never want to export
# a key for the SA the VM itself runs as — that would be a privilege
# escalation if the key ever leaks, and (b) the CI account can be
# rotated independently.
#
# The function is fully idempotent: running it twice is a no-op.
# It prints the freshly-generated key to stdout (base64-encoded) so
# you can pipe straight into `pbcopy` and paste into Bitbucket's
# "GCP_SA_KEY_B64" variable.
seed_ci_sa() {
    require_gcloud
    local name="${CI_SA_NAME:-digi-setu-ci}"
    local email="${name}@${PROJECT}.iam.gserviceaccount.com"
    local roles=(
        # cloudbuild.builds.builder is a superset of .editor — it
        # also covers the staging bucket reads, log writes, and AR
        # uploads that `gcloud builds submit` does behind the scenes.
        roles/cloudbuild.builds.builder
        # Required separately because `gcloud builds submit` checks
        # serviceusage.services.use on the project before it touches
        # the staging bucket. Builder doesn't include it.
        roles/serviceusage.serviceUsageConsumer
        # The Cloud Build staging bucket (gs://PROJECT_cloudbuild)
        # holds the source tarball; we need read+write on it.
        roles/storage.objectAdmin
        # Cloud Build streams logs to GCL — without this the build
        # still works but `gcloud builds submit` can't tail logs.
        roles/logging.logWriter
        # Push pi-backend / pi-session images to AR after the build.
        roles/artifactregistry.writer
        # Hydrate build.rs's compile-time CLERK_*_PROD from GSM.
        roles/secretmanager.secretAccessor
        # Tunnel the `gcloud compute scp / ssh` traffic through IAP.
        roles/iap.tunnelResourceAccessor
        # remote-deploy.sh's roll_stack step ssh'es into the VM and
        # runs `sudo systemctl restart pi.service` + `sudo docker pull`.
        # That requires sudo over OS Login → roles/compute.osAdminLogin
        # (osLogin alone is read-only). The VM's PAM is configured to
        # grant sudo to anyone with osAdminLogin.
        roles/compute.osAdminLogin
        # Lets the SA impersonate the VM SA when needed (used by
        # gcloud compute ssh + the docker login over metadata).
        roles/iam.serviceAccountUser
    )
    if gcloud iam service-accounts describe "${email}" --project "${PROJECT}" >/dev/null 2>&1; then
        log "service account ${email} exists; will (re)assert role bindings only"
    else
        log "creating service account ${email}"
        gcloud iam service-accounts create "${name}" \
            --project "${PROJECT}" \
            --display-name "Digi Setu CI (Bitbucket Pipelines + GHA)" >/dev/null
    fi
    local r
    for r in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "${PROJECT}" \
            --member "serviceAccount:${email}" \
            --role "${r}" \
            --condition=None \
            >/dev/null && log "  ${r}: bound" || warn "  ${r}: bind failed"
    done
    # Generate a fresh JSON key and emit it base64-encoded so the dev
    # can paste straight into Bitbucket's repo variables UI without
    # newlines / quoting issues. We delete the on-disk copy so the
    # only persisted record of the key is whatever the operator does
    # with stdout.
    local keyfile
    keyfile=$(mktemp)
    gcloud iam service-accounts keys create "${keyfile}" \
        --iam-account "${email}" --project "${PROJECT}" >/dev/null
    log "fresh key for ${email} (base64 below; paste into GCP_SA_KEY_B64):"
    echo
    base64 < "${keyfile}" | tr -d '\n'
    echo
    rm -f "${keyfile}"
    echo
    log "next step: paste the value above into:"
    log "  Bitbucket → Repo settings → Pipelines → Variables → GCP_SA_KEY_B64 (Secured)"
    log "  GitHub    → Repo settings → Secrets & variables → Actions → GCP_SA_KEY"
    log "    (for GHA, base64-decode first: \`echo \$KEY_B64 | base64 -d\` then paste)"
}

usage() {
    cat <<'USAGE' >&2
Usage:
  secrets-sync.sh push [KEY...]      Push managed keys from stack.env to GSM.
  secrets-sync.sh pull KEY           Print one secret value to stdout.
  secrets-sync.sh pull-all           Print stack.env-shaped output to stdout.
  secrets-sync.sh list               Show which secrets exist + version info.
  secrets-sync.sh seed-iam           Grant the VM SA secretAccessor on each.
  secrets-sync.sh seed-ci-sa         Provision the CI service account
                                     (Bitbucket Pipelines / GHA) and
                                     emit a fresh base64 key on stdout.

Env overrides:
  GCP_PROJECT (default digi-setu-dev)
  STACK_ENV   (default deploy/stack.env)
  VM_SA       (default digi-setu-live@digi-setu-dev.iam.gserviceaccount.com)
USAGE
    exit 64
}

cmd="${1:-}"
[[ -z "${cmd}" ]] && usage
shift || true

case "${cmd}" in
    push)
        require_gcloud
        if [[ "$#" -eq 0 ]]; then
            for k in "${MANAGED_KEYS[@]}"; do push_one "${k}"; done
        else
            for k in "$@"; do push_one "${k}"; done
        fi
        ;;
    pull)
        require_gcloud
        [[ "$#" -ge 1 ]] || fail "pull KEY"
        pull_one "$1"
        ;;
    pull-all)
        pull_all
        ;;
    list)
        list_secrets
        ;;
    seed-iam)
        seed_iam
        ;;
    seed-ci-sa)
        seed_ci_sa
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        fail "unknown command: ${cmd} (try 'help')"
        ;;
esac
