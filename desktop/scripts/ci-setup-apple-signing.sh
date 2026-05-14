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

    # ── DIAGNOSTIC (remove once .p12 import is reliable) ───────────
    # Lets us compare the bytes the runner sees against the bytes we
    # uploaded from a developer laptop (sha256 + size). Also tries
    # openssl pkcs12 as a parallel validator: if openssl can parse the
    # file but `security import` can't, the issue is Apple-specific
    # (cipher / curve / key-usage); if openssl ALSO chokes, the file
    # itself is corrupt or the password mismatches.
    echo "::group::p12 diagnostic"
    echo "APPLE_SIGN_P12_BASE64 length (chars): ${#APPLE_SIGN_P12_BASE64}"
    echo "APPLE_SIGN_P12_PASSWORD length (chars): ${#APPLE_SIGN_P12_PASSWORD}"
    echo "decoded p12 size (bytes): $(wc -c <"$P12" | tr -d ' ')"
    echo "decoded p12 sha256: $(shasum -a 256 "$P12" | awk '{print $1}')"
    echo "decoded p12 file(1): $(file "$P12")"
    echo "first 64 hex bytes of decoded p12:"
    xxd -l 64 "$P12" || head -c 64 "$P12" | xxd
    echo "openssl pkcs12 parse attempt:"
    if /usr/bin/openssl pkcs12 -in "$P12" -passin "pass:$APPLE_SIGN_P12_PASSWORD" -nokeys -info -noout 2>&1; then
        echo "openssl: OK"
    else
        echo "openssl: FAILED"
    fi
    echo "::endgroup::"
    # ── /DIAGNOSTIC ───────────────────────────────────────────────

    security create-keychain -p "$KEYCHAIN_PASS" "$KEYCHAIN"
    # 21600 s = 6 h. Generous enough for any single CI job; auto-locks
    # afterwards so a runner that hangs around doesn't expose the key.
    security set-keychain-settings -lut 21600 "$KEYCHAIN"
    security unlock-keychain -p "$KEYCHAIN_PASS" "$KEYCHAIN"

    # `-T /usr/bin/codesign` lets codesign use the imported key without
    # prompting for keychain access. Required for non-interactive CI.
    security import "$P12" -k "$KEYCHAIN" -P "$APPLE_SIGN_P12_PASSWORD" \
        -T /usr/bin/codesign

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

    # ── DIAGNOSTIC: dump everything we can see in the keychain ─────
    echo "::group::keychain inventory"
    echo "[all certs in build keychain]"
    security find-certificate -a "$KEYCHAIN" 2>&1 | grep -E '"alis"|"labl"' | head -40 || true
    echo
    echo "[identities, ALL — no -v filter]"
    security find-identity -p codesigning "$KEYCHAIN" 2>&1 || true
    echo
    echo "[identities, VALID-ONLY — -v filter]"
    security find-identity -v -p codesigning "$KEYCHAIN" 2>&1 || true
    echo
    echo "[identities, ALL keychains in search list]"
    security find-identity -p codesigning 2>&1 || true
    echo "::endgroup::"
    # ── /DIAGNOSTIC ───────────────────────────────────────────────

    # Use ALL keychains (not just our build keychain) so cert chain
    # validation can reach Apple's intermediate + root certs that
    # ship in the runner's System.keychain. Drop the -v filter
    # because GHA hosted runners often fail OCSP/CRL revocation
    # checks (network policy) and would mark the cert "invalid" even
    # though codesign itself will accept it (codesign re-runs its
    # own chain validation at sign time using cached/offline trust).
    identity="$(security find-identity -p codesigning "$KEYCHAIN" \
        | awk -F'"' '/Developer ID Application/{print $2; exit}')"

    if [[ -z "$identity" ]]; then
        echo "::error::no Developer ID Application identity found in imported .p12"
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
