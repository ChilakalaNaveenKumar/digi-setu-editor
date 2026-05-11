#!/usr/bin/env bash
# upload-installer.sh — push a built .dmg / .app artefact to the
# downloads directory on digi-setu-live so it's served by Caddy at
# https://digi-setu.com/downloads/<filename>.
#
# Usage:
#   scripts/upload-installer.sh PATH_TO_DMG [REMOTE_FILENAME]
#
# Example:
#   scripts/upload-installer.sh \
#       desktop/src-tauri/target/release/bundle/dmg/Digi\ Setu_0.1.0_aarch64.dmg \
#       Digi-Setu-0.1.0-arm64.dmg
#
# Behaviour:
#   1. gcloud compute scp the file to /tmp on the VM.
#   2. ssh: move to /srv/pi/downloads with chmod 0644 + chown root.
#   3. ssh: print the public URL + the SHA256 the user can verify.
#
# REMOTE_FILENAME defaults to the basename, normalised to remove
# spaces (Caddy serves whatever's on disk; spaces in URLs are ugly).

set -euo pipefail

# Order matters: PYTHON FIRST.
#
# Earlier we tried `sha256sum` first because it's the lowest-overhead
# binary on every box. It bit us on the Windows GHA runner: the
# msys2/Git-Bash build of `sha256sum` opens stdin in TEXT mode under
# certain Windows fdisk + Cygwin runtime combinations, which means
# random `\r\n` byte pairs inside an .exe / .msi binary get
# translated to `\n` before hashing. The result is a SHA that differs
# from the byte-identical file once it lands on the Linux VM (where
# `sha256sum` is always binary). We watched a 110 MB .exe transfer
# at 100% and STILL fail "SHA mismatch after upload" because of this
# exact bug.
#
# Python's `hashlib.sha256` always reads in binary mode regardless of
# platform, so it produces the same digest for the same byte stream
# on Windows, macOS, and Linux. Every GHA runner ships Python 3, so
# this branch fires on essentially every CI invocation.
#
# We keep the pure-shell fallbacks for Bitbucket Linux runners and
# dev laptops without Python (rare but possible), and explicitly
# pass `-b` to `sha256sum`/`shasum` to force binary mode wherever
# they're used so the same bug doesn't bite via the fallback path.
sha256_file() {
  local f="$1"
  local _py=""
  if command -v python3 >/dev/null 2>&1; then
    _py=python3
  elif command -v python >/dev/null 2>&1; then
    _py=python
  fi
  if [[ -n "$_py" ]]; then
    "$_py" - "$f" <<'PY'
import hashlib, sys
path = sys.argv[1]
h = hashlib.sha256()
with open(path, "rb") as fp:
    for chunk in iter(lambda: fp.read(1 << 20), b""):
        h.update(chunk)
print(h.hexdigest())
PY
    return 0
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -b "$f" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -b -a 256 "$f" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$f" | awk '{print $NF}'
  else
    echo "$0: need python, sha256sum, shasum, or openssl for SHA-256" >&2
    exit 127
  fi
}

PROJECT="${GCP_PROJECT:-digi-setu-dev}"
ZONE="${GCP_ZONE:-us-central1-a}"
VM="${GCP_VM:-digi-setu-live}"
REMOTE_DIR="/srv/pi/downloads"

# ── SSH transport selection ────────────────────────────────────────
# On Windows GHA runners, `gcloud compute ssh` shells out to PuTTY's
# `plink.exe`, which prompts interactively the first time it sees a
# new SSH host key:
#
#     Store key in cache? (y/n, Return cancels connection, i for more info)
#
# In a non-interactive runner that prompt blocks forever and the
# job times out (or, with the timeout we set, exits non-zero with
# `[plink.exe] exited with return code [1]`).
#
# Fix: route SSH through Google's Identity-Aware Proxy instead. With
# `--tunnel-through-iap` gcloud bypasses plink entirely and uses its
# own Python-based tunneller, which has no interactive prompts AND
# also removes the need for the runner to have inbound SSH from the
# public internet. The `--strict-host-key-checking=no` belt-and-
# suspenders auto-accepts the host key on any path that still goes
# through ssh/plink (e.g. if IAP is unavailable for some reason).
#
# `gcloud compute scp` and `gcloud compute ssh` accept the SAME
# transport flags. Earlier we tried `--ssh-flag=…` here but scp
# rejects it ("unrecognized arguments") since it has its own
# `--scp-flag`. Stick to flags both subcommands speak.
SSH_COMMON_ARGS=(
  --tunnel-through-iap
  --strict-host-key-checking=no
)

# ── OS Login key-bloat prune ───────────────────────────────────────
# Source the shared helper so this runs at the top of every CI step
# that touches `gcloud compute ssh|scp`. See _oslogin-prune.sh for
# the full rationale; tl;dr: the 32 KiB cap on the active account's
# OS Login profile is the single most common deploy failure mode.
# shellcheck disable=SC1091
source "$(dirname -- "${BASH_SOURCE[0]}")/_oslogin-prune.sh"
prune_oslogin_keys

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 PATH_TO_DMG [REMOTE_FILENAME]" >&2
  exit 64
fi

LOCAL="$1"
if [[ ! -f "$LOCAL" ]]; then
  echo "Not a file: $LOCAL" >&2
  exit 66
fi

# Default the remote name to the local basename with spaces → dashes.
REMOTE_NAME="${2:-$(basename "$LOCAL" | tr ' ' '-')}"

LOCAL_SHA="$(sha256_file "$LOCAL")"
LOCAL_SIZE_MB="$(du -m "$LOCAL" | awk '{print $1}')"

echo "[upload] Local:   $LOCAL"
echo "[upload]          $LOCAL_SIZE_MB MB · sha256=$LOCAL_SHA"
echo "[upload] Remote:  $VM:$REMOTE_DIR/$REMOTE_NAME"
echo

# Step 1: scp to /tmp (where the SSH user can write without sudo).
TMP_REMOTE="/tmp/${REMOTE_NAME}"
gcloud compute scp "$LOCAL" "${VM}:${TMP_REMOTE}" \
  --project "$PROJECT" --zone "$ZONE" --quiet \
  "${SSH_COMMON_ARGS[@]}"

# Step 2: move into /srv/pi/downloads with sudo, chmod, chown, then
# verify the SHA matches the one we computed locally.
gcloud compute ssh "$VM" --project "$PROJECT" --zone "$ZONE" --quiet \
  "${SSH_COMMON_ARGS[@]}" --command "
  set -euo pipefail
  sudo install -d -m 0755 -o 0 -g 0 ${REMOTE_DIR}
  sudo install -m 0644 -o 0 -g 0 ${TMP_REMOTE} ${REMOTE_DIR}/${REMOTE_NAME}
  rm -f ${TMP_REMOTE}
  REMOTE_SHA=\$(sha256sum ${REMOTE_DIR}/${REMOTE_NAME} | awk '{print \$1}')
  if [[ \"\$REMOTE_SHA\" != \"${LOCAL_SHA}\" ]]; then
    echo '[upload] ERROR: SHA mismatch after upload' >&2
    exit 1
  fi
  echo '[upload] OK — sha256 matches'
  echo \"Public URL: https://digi-setu.com/downloads/${REMOTE_NAME}\"
"
