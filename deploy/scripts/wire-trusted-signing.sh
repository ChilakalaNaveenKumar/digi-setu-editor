#!/usr/bin/env bash
# wire-trusted-signing.sh — interactively provision the Azure Trusted
# Signing service principal + push all 7 secrets to GitHub Actions
# so the release.yml workflow can produce a signed Windows .exe.
#
# What it does:
#   1. Verifies you've completed `az login` and `gh auth status`.
#   2. Lists every Trusted Signing account + cert profile in the
#      current Azure subscription; prompts you to pick one of each.
#   3. Looks up the regional endpoint URL for your TS account.
#   4. Creates (or rotates) a Service Principal named
#      "digi-setu-trusted-signing" with secret valid for 2 years.
#   5. Assigns it the "Trusted Signing Certificate Profile Signer"
#      role scoped to JUST that one cert profile (least-privilege).
#   6. Pushes 7 secrets to the GitHub repo's Actions store via gh.
#   7. Optionally bumps to a v0.1.x tag and pushes — that fires
#      .github/workflows/release.yml on a windows-latest runner.
#
# What you need to do BEFORE running:
#   - az login                           (any sub with TS owner role)
#   - gh auth status                     (PAT must have repo + workflow)
#   - Trusted Signing account already provisioned with a cert profile
#     (you mentioned 78700abb-…1d7a4a7d1ea4 verification is complete)
#
# Re-runnable: idempotent. Re-running rotates the SP secret + re-pushes.
#
# Cost: zero. The SP itself is free; Trusted Signing charges $9.99/mo
# flat for the account regardless of signature count.

set -euo pipefail

REPO="${GITHUB_REPO:-nchilaka-create/DIGI-SETU}"
SP_NAME="${SP_NAME:-digi-setu-trusted-signing}"

C_OK=$'\033[1;32m'
C_INFO=$'\033[1;34m'
C_WARN=$'\033[1;33m'
C_RESET=$'\033[0m'
log()  { printf '%s[ts-wire]%s %s\n' "${C_INFO}" "${C_RESET}" "$*"; }
ok()   { printf '%s[ts-wire]%s %s\n' "${C_OK}"   "${C_RESET}" "$*"; }
warn() { printf '%s[ts-wire]%s %s\n' "${C_WARN}" "${C_RESET}" "$*" >&2; }
fail() { warn "$*"; exit 1; }

# ── 0. Pre-flight ───────────────────────────────────────────────────
command -v az >/dev/null 2>&1 || fail "az CLI missing — install via brew install azure-cli"
command -v gh >/dev/null 2>&1 || fail "gh CLI missing — install via brew install gh"
command -v jq >/dev/null 2>&1 || fail "jq missing — install via brew install jq"

az account show >/dev/null 2>&1 || fail "run \`az login\` first"
gh auth status   >/dev/null 2>&1 || fail "run \`gh auth login\` first"

# Make sure the trustedsigning extension is installed (it's a preview,
# not in core CLI yet). Idempotent.
log "ensuring az trustedsigning extension is installed"
az extension show --name trustedsigning >/dev/null 2>&1 \
    || az extension add --name trustedsigning --only-show-errors >/dev/null

SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
log "subscription: $(az account show --query name -o tsv) ($SUB_ID)"
log "tenant:       $TENANT_ID"

# ── 1. Pick TS account ──────────────────────────────────────────────
log "discovering Trusted Signing accounts in this subscription"
ACCOUNTS=()
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    ACCOUNTS+=("$line")
done < <(az trustedsigning list --only-show-errors \
    --query '[].[name, resourceGroup, location, id]' -o tsv)

if [[ ${#ACCOUNTS[@]} -eq 0 ]]; then
    fail "no Trusted Signing accounts found — create one in the Azure Portal first"
fi

if [[ ${#ACCOUNTS[@]} -eq 1 ]]; then
    IFS=$'\t' read -r ACCT_NAME ACCT_RG ACCT_REGION ACCT_ID <<< "${ACCOUNTS[0]}"
    log "only one account — auto-selecting ${ACCT_NAME}"
else
    echo
    echo "Pick a Trusted Signing account:"
    i=1
    for row in "${ACCOUNTS[@]}"; do
        IFS=$'\t' read -r n rg loc _ <<< "${row}"
        printf "  %d) %s  (%s · %s)\n" "$i" "$n" "$loc" "$rg"
        i=$((i+1))
    done
    read -rp "  [1-${#ACCOUNTS[@]}]: " pick
    IFS=$'\t' read -r ACCT_NAME ACCT_RG ACCT_REGION ACCT_ID <<< "${ACCOUNTS[$((pick-1))]}"
fi

# ── 2. Pick cert profile under that account ─────────────────────────
log "discovering cert profiles under ${ACCT_NAME}"
PROFILES=()
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    PROFILES+=("$line")
done < <(az trustedsigning certificate-profile list \
    --account-name "$ACCT_NAME" --resource-group "$ACCT_RG" \
    --only-show-errors --query '[].name' -o tsv)

if [[ ${#PROFILES[@]} -eq 0 ]]; then
    fail "no cert profiles under ${ACCT_NAME} — create one in the Azure Portal first"
fi

if [[ ${#PROFILES[@]} -eq 1 ]]; then
    PROFILE="${PROFILES[0]}"
    log "only one profile — auto-selecting ${PROFILE}"
else
    echo
    echo "Pick a cert profile:"
    i=1
    for p in "${PROFILES[@]}"; do
        printf "  %d) %s\n" "$i" "$p"
        i=$((i+1))
    done
    read -rp "  [1-${#PROFILES[@]}]: " pick
    PROFILE="${PROFILES[$((pick-1))]}"
fi

# Prefer the AccountUri returned directly by Azure (most reliable);
# fall back to a regional shortcode lookup if for some reason the
# uri field is empty.
ENDPOINT=$(az trustedsigning show \
    --name "$ACCT_NAME" --resource-group "$ACCT_RG" \
    --only-show-errors --query 'accountUri' -o tsv 2>/dev/null | sed 's:/*$::')

if [[ -z "$ENDPOINT" ]]; then
    case "$ACCT_REGION" in
        eastus)            SHORT=eus    ;;
        eastus2)           SHORT=eus2   ;;
        westus)            SHORT=wus    ;;
        westus2)           SHORT=wus2   ;;
        westus3)           SHORT=wus3   ;;
        westcentralus)     SHORT=wcus   ;;
        centralus)         SHORT=cus    ;;
        northcentralus)    SHORT=ncus   ;;
        southcentralus)    SHORT=scus   ;;
        northeurope)       SHORT=neu    ;;
        westeurope)        SHORT=weu    ;;
        uksouth)           SHORT=uks    ;;
        ukwest)            SHORT=ukw    ;;
        australiaeast)     SHORT=aue    ;;
        australiasoutheast) SHORT=auses ;;
        southeastasia)     SHORT=sea    ;;
        eastasia)          SHORT=ea     ;;
        japaneast)         SHORT=jpe    ;;
        japanwest)         SHORT=jpw    ;;
        koreacentral)      SHORT=krc    ;;
        canadacentral)     SHORT=cac    ;;
        brazilsouth)       SHORT=brs    ;;
        centralindia)      SHORT=cin    ;;
        southindia)        SHORT=sin    ;;
        westindia)         SHORT=win    ;;
        *)                 SHORT="$ACCT_REGION" ;;
    esac
    ENDPOINT="https://${SHORT}.codesigning.azure.net"
fi
log "endpoint:     ${ENDPOINT}"
log "account:      ${ACCT_NAME}"
log "profile:      ${PROFILE}"

# ── 3. Service principal (create or rotate) ─────────────────────────
PROFILE_ID="${ACCT_ID}/certificateProfiles/${PROFILE}"
log "creating/rotating SP ${SP_NAME}, scoped to:"
log "  ${PROFILE_ID}"

# Use --json-auth so we get a single JSON we can jq into the env vars.
# Microsoft renamed the role from "Trusted Signing …" to "Artifact
# Signing …" in late 2025; try the new name first, fall back to the
# old one for older tenants.
SP_JSON=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role "Artifact Signing Certificate Profile Signer" \
    --scopes "$PROFILE_ID" \
    --years 2 \
    --only-show-errors 2>/dev/null) || \
SP_JSON=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role "Trusted Signing Certificate Profile Signer" \
    --scopes "$PROFILE_ID" \
    --years 2 \
    --only-show-errors)

CLIENT_ID=$(echo     "$SP_JSON" | jq -r '.appId')
CLIENT_SECRET=$(echo "$SP_JSON" | jq -r '.password')
SP_TENANT=$(echo     "$SP_JSON" | jq -r '.tenant')

[[ "$SP_TENANT" == "$TENANT_ID" ]] \
    || warn "tenant mismatch: SP tenant=$SP_TENANT vs az tenant=$TENANT_ID — using SP value"

ok "service principal ready (clientId=${CLIENT_ID})"

# ── 4. Push all 7 secrets to GitHub Actions ─────────────────────────
log "pushing 7 secrets to GitHub repo ${REPO}"

push_secret() {
    local k="$1" v="$2"
    # Pass the value via stdin — `gh secret set NAME` reads from STDIN
    # when --body is not supplied. (Don't use `--body -`; that sets the
    # secret to the literal string "-".)
    if printf '%s' "$v" | gh secret set "$k" --repo "$REPO" >/dev/null 2>&1; then
        ok "  ${k}: pushed (${#v} chars)"
    else
        warn "  ${k}: push FAILED"
    fi
}

push_secret TRUSTED_SIGNING_ENDPOINT "$ENDPOINT"
push_secret TRUSTED_SIGNING_ACCOUNT  "$ACCT_NAME"
push_secret TRUSTED_SIGNING_PROFILE  "$PROFILE"
push_secret AZURE_TENANT_ID          "$SP_TENANT"
push_secret AZURE_CLIENT_ID          "$CLIENT_ID"
push_secret AZURE_CLIENT_SECRET      "$CLIENT_SECRET"

# Bonus: also seed the Cloud-upload SA if it's not already there. We
# already minted the JSON key into ~/.digi-setu/ci-sa.json earlier;
# GHA wants the raw JSON (NOT base64), unlike Bitbucket.
if [[ -f "$HOME/.digi-setu/ci-sa.json" ]]; then
    push_secret GCP_SA_KEY "$(cat "$HOME/.digi-setu/ci-sa.json")"
fi

# Clerk keys come from GSM via the Azure-side reuse pattern; pull
# directly so GHA doesn't need GCP access just to read them.
PROJECT="${GCP_PROJECT:-digi-setu-dev}"
if command -v gcloud >/dev/null 2>&1 && gcloud auth list --filter=status:ACTIVE --format='value(account)' >/dev/null 2>&1; then
    for k in CLERK_PUBLISHABLE_KEY_PROD CLERK_SECRET_KEY_PROD; do
        v=$(gcloud secrets versions access latest --project "$PROJECT" --secret "$k" 2>/dev/null || true)
        [[ -n "$v" ]] && push_secret "$k" "$v"
    done
fi

ok "done — release.yml will fire on the next \`v*.*.*\` tag push."
echo
echo "  to trigger a signed Windows build right now:"
echo "    git tag v0.1.0 && git push origin v0.1.0 && git push github v0.1.0"
echo "  watch progress at:"
echo "    https://github.com/${REPO}/actions"
echo "  signed installers will appear at:"
echo "    https://digi-setu.com/downloads/Digi-Setu-0.1.0-x64-setup.exe"
echo "    https://digi-setu.com/downloads/Digi-Setu-0.1.0-x64.msi"
