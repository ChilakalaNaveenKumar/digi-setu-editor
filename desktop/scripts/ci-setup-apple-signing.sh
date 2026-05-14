#!/usr/bin/env bash
# ci-setup-apple-signing.sh
#
# CI-side bootstrap that prepares a macOS runner for Developer ID
# code-signing and Apple notarization. Designed for GitHub-hosted
# `macos-15` runners (VM is wiped post-job, so no manual cleanup
# needed) and the GHA `release.yml` workflow that drives them.
#
# Two independent blocks:
#
#   1. Code-signing (.p12 → ephemeral keychain)
#      Inputs:  APPLE_SIGN_P12_BASE64        secret, base64 of the
#                                            password-protected .p12
#                                            exported from the
#                                            developer's local
#                                            Keychain Access via
#                                            `security export -t
#                                            identities -f pkcs12`.
#               APPLE_SIGN_P12_PASSWORD      secret, the password
#                                            used at export time.
#      Outputs (via $GITHUB_ENV):
#               APPLE_SIGNING_IDENTITY       e.g.
#                  "Developer ID Application: DIGI-SETU, LLC (R99AT2ZKP2)"
#               BUILD_KEYCHAIN_PATH          for any later step that
#                                            wants to inspect or
#                                            unlock the keychain.
#
#   2. Notarization (.p8 → on-disk file, path exported)
#      Inputs:  APPLE_NOTARY_API_KEY_BASE64  secret, base64 of the
#                                            App Store Connect API
#                                            .p8 file (single-use
#                                            download from
#                                            appstoreconnect.apple.com
#                                            → Users and Access →
#                                            Integrations → Team Keys).
#               APPLE_NOTARY_API_KEY_ID      secret, 10-char Key ID.
#               APPLE_NOTARY_API_ISSUER      secret, UUID Issuer ID.
#      Outputs (via $GITHUB_ENV):
#               APPLE_NOTARY_API_KEY         absolute path to the
#                                            decoded .p8 (consumed by
#                                            release.sh's
#                                            notarize_dmg_mac()).
#               APPLE_NOTARY_API_KEY_ID      passed through.
#               APPLE_NOTARY_API_ISSUER      passed through.
#
# Each block is independent — missing secrets just skip that block,
# so PR builds (which can't read repo secrets) and developer dry-runs
# still succeed; they just produce ad-hoc-signed, un-notarized DMGs
# (the same artefact the build produced before signing was wired in).
#
# Why a fresh keychain instead of importing into the runner's default
# `login.keychain-db`:
#   * Reproducibility — every build starts from a known-empty keychain;
#     no surprises from leftover identities a previous job may have
#     dropped.
#   * Concurrency — multiple parallel macOS jobs on the same self-hosted
#     runner each get their own keychain ($RUNNER_TEMP is per-job).
#   * Forensics — if a build fails, the keychain we created is named
#     deterministically and easy to inspect.
#
# Self-hosted runners: nothing in this script persists state outside
# $RUNNER_TEMP (which the GHA runner wipes between jobs). On a self-
# hosted box where $RUNNER_TEMP survives, the very first `security
# delete-keychain` call below scrubs any prior keychain.

set -euo pipefail

WORK="${RUNNER_TEMP:-/tmp}"

write_env() {
    # Forward a key=value to subsequent steps via $GITHUB_ENV. Falls
    # back to a plain export when not running under GHA so this script
    # is also useful from a local shell for end-to-end testing.
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        echo "$1=$2" >> "$GITHUB_ENV"
    else
        export "$1=$2"
        echo "$1=$2"
    fi
}

# ── 1. Code-signing identity ─────────────────────────────────────
if [[ -n "${APPLE_SIGN_P12_BASE64:-}" ]]; then
    [[ -n "${APPLE_SIGN_P12_PASSWORD:-}" ]] || {
        echo "::error::APPLE_SIGN_P12_BASE64 set but APPLE_SIGN_P12_PASSWORD is empty"
        exit 1
    }

    KEYCHAIN="${WORK}/digi-setu-build.keychain-db"
    P12="${WORK}/digi-setu-signing.p12"
    KEYCHAIN_PASS="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)"

    # Belt-and-braces wipe in case a prior self-hosted run left state.
    security delete-keychain "$KEYCHAIN" 2>/dev/null || true
    rm -f "$P12"

    printf '%s' "$APPLE_SIGN_P12_BASE64" | base64 --decode > "$P12"
    chmod 600 "$P12"

    security create-keychain -p "$KEYCHAIN_PASS" "$KEYCHAIN"
    # 21600 s = 6 h. Generous enough for any single CI job; auto-locks
    # afterwards so a runner that hangs around doesn't expose the key.
    security set-keychain-settings -lut 21600 "$KEYCHAIN"
    security unlock-keychain -p "$KEYCHAIN_PASS" "$KEYCHAIN"

    # `-T /usr/bin/codesign` lets codesign use the imported key without
    # prompting. `-A` ALSO lets every other tool — notably `security
    # find-identity` itself — read the cert/key. Without -A, the
    # access-control list on the imported key restricts read access
    # to codesign only, so `find-identity` reports 0 identities even
    # though the key + cert ARE in the keychain. We're in an
    # ephemeral, single-job-scoped keychain with no other secrets,
    # so "allow any" carries zero practical risk.
    security import "$P12" -k "$KEYCHAIN" -P "$APPLE_SIGN_P12_PASSWORD" \
        -T /usr/bin/codesign -A

    # Required on macOS 10.12+ — without this, codesign hits a
    # "User Interaction Is Not Allowed" UI prompt the first time it
    # tries to use the key.
    security set-key-partition-list \
        -S apple-tool:,apple:,codesign: \
        -s -k "$KEYCHAIN_PASS" "$KEYCHAIN" >/dev/null

    # Prepend our keychain to the user's search list so codesign finds
    # the new identity ahead of anything else.
    existing="$(security list-keychains -d user | tr -d '"' | xargs)"
    # shellcheck disable=SC2086
    security list-keychains -d user -s "$KEYCHAIN" $existing
    security default-keychain -s "$KEYCHAIN"

    # Search across ALL keychains in the user search list (we put our
    # build keychain at the front a few lines above), NOT just the
    # build keychain in isolation. find-identity with an explicit
    # `$KEYCHAIN` arg restricts cert-chain validation to just that
    # keychain, and on GHA hosted runners the chain validator wants
    # to reach Apple's trust roots in other keychains — even with
    # the intermediate present in the build keychain, the explicit-
    # keychain query reports 0 identities. Searching across the
    # search list gives the validator everything it needs.
    identity="$(security find-identity -p codesigning \
        | awk -F'"' '/Developer ID Application/{print $2; exit}')"

    if [[ -z "$identity" ]]; then
        echo "::error::no Developer ID Application identity found"
        echo "[full identity dump for debugging]" >&2
        security find-identity -p codesigning "$KEYCHAIN" >&2
        security find-identity -p codesigning >&2
        exit 1
    fi

    echo "::notice::APPLE_SIGNING_IDENTITY=$identity"

    # Wipe the .p12 from disk now that the cert + key live in the
    # keychain. The keychain itself is the only persistent artefact.
    rm -f "$P12"

    write_env APPLE_SIGNING_IDENTITY "$identity"
    write_env BUILD_KEYCHAIN_PATH "$KEYCHAIN"
else
    echo "::notice::APPLE_SIGN_P12_BASE64 not set; build will fall back to ad-hoc signature"
fi

# ── 2. Notarization API key ──────────────────────────────────────
if [[ -n "${APPLE_NOTARY_API_KEY_BASE64:-}" ]]; then
    [[ -n "${APPLE_NOTARY_API_KEY_ID:-}" ]] || {
        echo "::error::APPLE_NOTARY_API_KEY_BASE64 set but APPLE_NOTARY_API_KEY_ID is empty"
        exit 1
    }
    [[ -n "${APPLE_NOTARY_API_ISSUER:-}" ]] || {
        echo "::error::APPLE_NOTARY_API_KEY_BASE64 set but APPLE_NOTARY_API_ISSUER is empty"
        exit 1
    }

    P8="${WORK}/AuthKey_${APPLE_NOTARY_API_KEY_ID}.p8"
    rm -f "$P8"
    printf '%s' "$APPLE_NOTARY_API_KEY_BASE64" | base64 --decode > "$P8"
    chmod 600 "$P8"

    echo "::notice::APPLE_NOTARY_API_KEY=$P8 (key id $APPLE_NOTARY_API_KEY_ID)"

    write_env APPLE_NOTARY_API_KEY "$P8"
    # Pass through so release.sh sees the same names regardless of
    # whether the operator ran this script or set them by hand.
    write_env APPLE_NOTARY_API_KEY_ID "$APPLE_NOTARY_API_KEY_ID"
    write_env APPLE_NOTARY_API_ISSUER "$APPLE_NOTARY_API_ISSUER"
else
    echo "::notice::APPLE_NOTARY_API_KEY_BASE64 not set; build will skip notarization"
fi
