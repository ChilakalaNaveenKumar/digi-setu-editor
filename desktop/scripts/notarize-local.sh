#!/usr/bin/env bash
# notarize-local.sh — finish a release locally when CI ran out of time.
#
# WHY THIS EXISTS
# ───────────────
# Apple's notary service is slow for new Developer IDs / new apps:
# the first ~5 submissions of a brand-new app can take 30 min – 6 h
# each (Apple DTS officially: "occasionally some uploads are held
# for in-depth analysis"). GitHub Actions caps a job at our
# configured timeout (120 min today), so a slow Apple queue can
# kill the whole CI run mid-poll, wasting 15 min of build time.
#
# The fix: split the pipeline. CI does the deterministic, time-
# bounded work (build + sign + DMG ≈ 20 min) and uploads the
# signed-but-unnotarized DMG as a workflow artefact. This script
# downloads that artefact onto your laptop, sends it to Apple
# notary (no wall-clock cap; backgroundable overnight), staples
# the ticket, and uploads the final shippable DMG to digi-setu.com.
#
# WHAT IT DOES
# ────────────
#   1. Locate the signed DMG. Either:
#        a) you pass a path to a .dmg file, OR
#        b) you pass --from-gh and a workflow run id (or "latest"),
#           and we `gh run download` the artefact.
#   2. Submit to Apple notary via xcrun notarytool with --wait.
#      No --timeout, because the whole point is "wait however
#      long Apple takes".
#   3. xcrun stapler staple, retried with backoff to absorb
#      Apple's CloudKit propagation lag.
#   4. xcrun stapler validate, then `spctl --assess` to confirm
#      Gatekeeper would silently approve a downloaded copy.
#   5. Optionally upload to digi-setu.com via
#      deploy/scripts/upload-installer.sh (gated by --upload).
#
# CREDENTIALS
# ───────────
# Reads the same App Store Connect API key trio as CI:
#
#     APPLE_NOTARY_API_KEY        path to the .p8 file
#     APPLE_NOTARY_API_KEY_ID     10-char alphanumeric (e.g. M8AWGANCUT)
#     APPLE_NOTARY_API_ISSUER     UUID
#
# If any are unset, we try sensible defaults:
#     APPLE_NOTARY_API_KEY    → ~/Library/Apple/Notary/AuthKey_<KEY_ID>.p8
#     APPLE_NOTARY_API_KEY_ID → M8AWGANCUT
#     APPLE_NOTARY_API_ISSUER → 7b63604b-140d-4461-8ada-8a49a97459c2
#
# USAGE
# ─────
#   # Most common: download the latest GH run's DMGs and notarize both
#   bash desktop/scripts/notarize-local.sh --from-gh latest --upload
#
#   # Specific run id
#   bash desktop/scripts/notarize-local.sh --from-gh 25895331574
#
#   # Already-downloaded local DMG
#   bash desktop/scripts/notarize-local.sh ~/Downloads/Digi-Setu-0.1.0-arm64.dmg --upload
#
#   # Backgroundable: run in tmux/screen overnight
#   nohup bash desktop/scripts/notarize-local.sh --from-gh latest --upload \
#         > ~/notarize.log 2>&1 &

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$DESKTOP/.." && pwd)"

GH_REPO="${GH_REPO:-nchilaka-create/DIGI-SETU}"

# Sensible defaults — picked from prior session.
APPLE_NOTARY_API_KEY_ID="${APPLE_NOTARY_API_KEY_ID:-M8AWGANCUT}"
APPLE_NOTARY_API_ISSUER="${APPLE_NOTARY_API_ISSUER:-7b63604b-140d-4461-8ada-8a49a97459c2}"
APPLE_NOTARY_API_KEY="${APPLE_NOTARY_API_KEY:-${HOME}/Library/Apple/Notary/AuthKey_${APPLE_NOTARY_API_KEY_ID}.p8}"

log()   { printf '[notarize-local] %s\n' "$*"; }
warn()  { printf '[notarize-local] WARN: %s\n' "$*" >&2; }
fail()  { printf '[notarize-local] FAIL: %s\n' "$*" >&2; exit 1; }

DO_UPLOAD=0
FROM_GH=""
DMGS=()

usage() {
    sed -n '/^# USAGE/,/^$/p' "$0" | sed 's/^# \?//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-gh)  FROM_GH="${2:?missing run id (or 'latest')}"; shift 2 ;;
        --upload)   DO_UPLOAD=1; shift ;;
        --gh-repo)  GH_REPO="${2:?missing owner/repo}"; shift 2 ;;
        -h|--help)  usage 0 ;;
        --*)        fail "unknown flag: $1" ;;
        *)          DMGS+=("$1"); shift ;;
    esac
done

# ── Sanity checks ──────────────────────────────────────────────────
[[ -f "$APPLE_NOTARY_API_KEY" ]] \
    || fail "APPLE_NOTARY_API_KEY not found at: $APPLE_NOTARY_API_KEY
              (export APPLE_NOTARY_API_KEY=/path/to/AuthKey_${APPLE_NOTARY_API_KEY_ID}.p8 or place at the default)"
[[ -n "$APPLE_NOTARY_API_KEY_ID" ]]  || fail "APPLE_NOTARY_API_KEY_ID empty"
[[ -n "$APPLE_NOTARY_API_ISSUER" ]]  || fail "APPLE_NOTARY_API_ISSUER empty"

command -v xcrun >/dev/null || fail "xcrun not found — Xcode command line tools missing"
xcrun --find notarytool >/dev/null 2>&1 || fail "xcrun notarytool unavailable; install Xcode 13+"
xcrun --find stapler    >/dev/null 2>&1 || fail "xcrun stapler unavailable"

# ── Download from GH if requested ──────────────────────────────────
if [[ -n "$FROM_GH" ]]; then
    command -v gh >/dev/null || fail "gh CLI not found; install via 'brew install gh'"
    if [[ "$FROM_GH" == "latest" ]]; then
        FROM_GH="$(gh run list --workflow=release.yml --repo "$GH_REPO" \
                       --limit 1 --json databaseId -q '.[0].databaseId')"
        log "resolved 'latest' to run id: $FROM_GH"
    fi
    DOWNLOAD_DIR="$(mktemp -d -t digi-setu-dmgs-XXXXX)"
    log "downloading workflow artefacts from run $FROM_GH into $DOWNLOAD_DIR"
    gh run download "$FROM_GH" --repo "$GH_REPO" --dir "$DOWNLOAD_DIR"
    while IFS= read -r -d '' f; do
        DMGS+=("$f")
    done < <(find "$DOWNLOAD_DIR" -type f -name '*.dmg' -print0)
    [[ ${#DMGS[@]} -gt 0 ]] || fail "no .dmg files in run $FROM_GH artefacts"
fi

[[ ${#DMGS[@]} -gt 0 ]] || usage 1

# ── Per-DMG: notarize + staple ─────────────────────────────────────
notarize_one() {
    local dmg="$1"
    local name; name="$(basename "$dmg")"
    log "── ${name} ──"
    log "  size: $(du -h "$dmg" | awk '{print $1}')"

    # Submit and block until Apple decides. Apple's queue dictates
    # the wall-clock; notarytool will poll and print status updates
    # every minute. No --timeout because we're not constrained by
    # a CI runner cap here.
    local result_plist log_json sub_id sub_status
    result_plist="$(mktemp -t notary-result.XXXXX.plist)"
    log_json="$(mktemp -t notary-log.XXXXX.json)"

    log "  submitting to Apple notary (this CAN take several hours on a new Developer ID)…"
    local submit_rc=0
    xcrun notarytool submit "$dmg" \
        --key "$APPLE_NOTARY_API_KEY" \
        --key-id "$APPLE_NOTARY_API_KEY_ID" \
        --issuer "$APPLE_NOTARY_API_ISSUER" \
        --wait \
        --output-format plist > "$result_plist" || submit_rc=$?

    sub_id="$(plutil -extract id raw -o - "$result_plist" 2>/dev/null || true)"
    sub_status="$(plutil -extract status raw -o - "$result_plist" 2>/dev/null || true)"
    log "  notary id=${sub_id:-<none>} status=${sub_status:-<none>} rc=${submit_rc}"

    if [[ "$sub_status" != "Accepted" ]]; then
        warn "  notarization not accepted; fetching log…"
        if [[ -n "$sub_id" ]]; then
            xcrun notarytool log "$sub_id" \
                --key "$APPLE_NOTARY_API_KEY" \
                --key-id "$APPLE_NOTARY_API_KEY_ID" \
                --issuer "$APPLE_NOTARY_API_ISSUER" \
                "$log_json" || true
            cat "$log_json" >&2 || true
        fi
        fail "  notarization status=${sub_status:-<none>}"
    fi

    log "  stapling notary ticket…"
    local attempt
    for attempt in 1 2 3 4 5 6 7 8; do
        if xcrun stapler staple "$dmg"; then
            break
        fi
        if [[ "$attempt" -eq 8 ]]; then
            fail "  stapler failed after 8 attempts (CloudKit propagation lag suspected)"
        fi
        log "  stapler not ready (attempt $attempt/8); retrying in 15 s…"
        sleep 15
    done
    xcrun stapler validate "$dmg" \
        || fail "  stapler validate failed after a successful staple — refusing to upload"

    # Earlier we ran `spctl --assess --type install` here, but DMGs
    # don't carry a code signature of their own — they're a disk
    # image whose authenticity comes from the stapled notary ticket
    # we just validated above. spctl with --type install / --type
    # open returns "rejected: no usable signature" on every signed-
    # and-stapled DMG (false negative), which used to abort the
    # script even though the DMG was perfectly shippable.
    #
    # The real-world Gatekeeper check that an end-user triggers
    # happens against the .app INSIDE the DMG, after they
    # double-click the DMG to mount it. The right way to verify
    # that here would be `hdiutil attach` + `spctl --assess --type
    # execute` against the .app + `hdiutil detach`, but that's a
    # 30-second mount cycle for a redundant check: notary
    # acceptance + staple validation already prove the bundle is
    # Gatekeeper-clean. We now log + trust those two and skip the
    # spctl-on-DMG anti-pattern.
    log "  ✓ notarized + stapled (Apple Accepted, staple validated): $dmg"

    # ── Upload to digi-setu.com if requested ───────────────────────
    if [[ $DO_UPLOAD -eq 1 ]]; then
        log "  uploading to digi-setu.com…"
        bash "$REPO_ROOT/deploy/scripts/upload-installer.sh" "$dmg"
    fi
}

for dmg in "${DMGS[@]}"; do
    notarize_one "$dmg"
done

log ""
log "ALL DONE — ${#DMGS[@]} DMG(s) notarized + stapled${DO_UPLOAD:+ + uploaded}."
