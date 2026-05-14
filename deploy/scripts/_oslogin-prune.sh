#!/usr/bin/env bash
# _oslogin-prune.sh — sourceable helper that keeps the active gcloud
# account's OS Login profile under the 32 KiB cap.
#
# Why this exists
# ───────────────
# Every `gcloud compute ssh|scp` invocation generates a fresh SSH
# keypair on the runner (because ephemeral CI containers start with
# no ~/.ssh/google_compute_engine), then POSTs the public key to the
# active account's OS Login profile so the VM's sshd will accept the
# session. The keys are NEVER garbage-collected by Google. After
# enough CI runs the profile fills up and EVERY subsequent ssh/scp
# from that account fails with:
#
#     ERROR: (gcloud.compute.ssh) FAILED_PRECONDITION:
#     Login profile size exceeds 32 KiB.
#
# Once that triggers, no more deploys succeed until a human prunes
# manually via `gcloud compute os-login ssh-keys remove` per key. We
# saw this with `digi-setu-ci@digi-setu-dev.iam.gserviceaccount.com`
# at 49 stale keys (44 KiB) blocking both Bitbucket Pipelines and
# the GHA Windows/macOS installer-upload workflows.
#
# Strategy
# ────────
# At the start of every CI step that uses gcloud compute ssh/scp:
#   1. Compute the SHA-256 fingerprint of THIS runner's existing
#      pubkey at ~/.ssh/google_compute_engine.pub (if any), so we
#      know which key NOT to delete (it's the one this script's
#      subsequent ssh/scp calls will reuse).
#   2. List all keys on the active account's profile, delete every
#      one whose fingerprint != that "keep" fingerprint.
#   3. On a fresh runner (no .pub yet) there's nothing to keep, so
#      we delete everything; gcloud will add a single fresh key on
#      the first ssh call after this prune.
#
# Concurrency safety
# ──────────────────
# The GHA macos-arm + macos-intel jobs run in PARALLEL, both
# authenticated as the same CI service account, and each runner is
# fresh (no ~/.ssh/google_compute_engine.pub yet). Sequential
# Bitbucket Pipelines steps have the same problem because each
# step is a fresh container. When two such runners hit this helper
# in close succession:
#   1. Runner A's gcloud adds key K_A to the OS Login profile.
#   2. Runner B starts. Its keep_fp="" (fresh runner). It lists the
#      profile and sees K_A, which doesn't match keep_fp → REMOVES
#      K_A. Then its own gcloud adds K_B.
#   3. Runner A's NEXT gcloud command tries to ssh with K_A, but
#      K_A is no longer in the profile → "Permission denied
#      (publickey)". Even worse, OS Login → sshd propagation is
#      async (~10-30 s), so a runner that re-adds its own key can
#      still hit Permission denied for a window after the add.
#
# Guard: only prune when the profile actually approaches the 32 KiB
# cap. The cap fits ~60 SSH keys; we gate on PRUNE_FLOOR (default 20)
# so day-to-day runs with a handful of keys are a hard no-op. The
# safety value the helper provides (avoiding "Login profile size
# exceeds 32 KiB" lockouts) is intact — we just stop churning
# concurrent runners' keys when there's plenty of headroom.
#
# Locality
# ────────
# Safe to source on developer laptops too — your personal account's
# profile only contains your own key, and we never delete the key
# whose fingerprint matches ~/.ssh/google_compute_engine.pub.
# Doubles as protection if a human ever does run the helper directly.

# We deliberately don't `set -e` here because failures must NEVER
# abort the surrounding deploy — bloat is a degraded state, not a
# fatal one for this run (only the NEXT ssh would fail).

prune_oslogin_keys() {
  if ! command -v gcloud >/dev/null 2>&1; then
    return 0
  fi

  local keep_fp=""
  local pub_path="${HOME}/.ssh/google_compute_engine.pub"
  if [[ -r "${pub_path}" ]] && command -v python3 >/dev/null 2>&1; then
    # OS Login's profile fingerprint is sha256 of the public-key file
    # contents with a single trailing newline (verified empirically by
    # comparing `gcloud compute os-login ssh-keys add --format=json`'s
    # echoed `fingerprint` field against this hash on the same file).
    keep_fp="$(python3 - "${pub_path}" <<'PY'
import hashlib, sys
try:
    with open(sys.argv[1]) as fp:
        body = fp.read().strip() + "\n"
    print(hashlib.sha256(body.encode()).hexdigest())
except Exception:
    pass
PY
    )"
  fi

  local fps
  fps="$(gcloud compute os-login ssh-keys list \
            --format='value(value.fingerprint)' 2>/dev/null || true)"
  if [[ -z "${fps}" ]]; then
    return 0
  fi

  # Count first, prune only if we're approaching the 32 KiB cap.
  # Override via PRUNE_FLOOR env var if you need to force aggressive
  # cleanup (e.g. PRUNE_FLOOR=0 in a one-off recovery script).
  local total=0
  while IFS= read -r fp; do
    [[ -z "${fp}" ]] && continue
    total=$((total + 1))
  done <<< "${fps}"

  local floor="${PRUNE_FLOOR:-20}"
  if (( total < floor )); then
    printf '[oslogin-prune] total=%d floor=%d — no-op (well under 32 KiB cap)\n' \
      "${total}" "${floor}"
    return 0
  fi

  local removed=0 kept=0 failed=0
  while IFS= read -r fp; do
    [[ -z "${fp}" ]] && continue
    if [[ -n "${keep_fp}" && "${fp}" == "${keep_fp}" ]]; then
      kept=$((kept + 1))
      continue
    fi
    if gcloud compute os-login ssh-keys remove --key="${fp}" >/dev/null 2>&1; then
      removed=$((removed + 1))
    else
      failed=$((failed + 1))
    fi
  done <<< "${fps}"

  printf '[oslogin-prune] total=%d removed=%d kept=%d failed=%d%s\n' \
    "${total}" "${removed}" "${kept}" "${failed}" \
    "$( [[ -n "${keep_fp}" ]] && printf ' keep_fp=%.12s…' "${keep_fp}" || printf ' (no local pubkey)' )"

  # We just removed keys; OS Login → sshd propagation is async (~10-30 s).
  # Sleep briefly so the caller's first ssh attempt doesn't race the
  # profile update. Cheap insurance — only fires on the rare prune path,
  # not the no-op floor branch above.
  if (( removed > 0 )); then
    sleep 15
  fi
}
