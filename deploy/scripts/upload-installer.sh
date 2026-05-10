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

# macOS has `shasum`; Linux CI and Windows Git Bash typically have
# `sha256sum` and/or `openssl`. Prefer the widest portable chain.
sha256_file() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$f" | awk '{print $NF}'
  else
    _py=""
    if command -v python3 >/dev/null 2>&1; then
      _py=python3
    elif command -v python >/dev/null 2>&1; then
      _py=python
    else
      echo "$0: need sha256sum, shasum, openssl, or python for SHA-256" >&2
      exit 127
    fi
    "$_py" - "$f" <<'PY'
import hashlib, sys
path = sys.argv[1]
h = hashlib.sha256()
with open(path, "rb") as fp:
    for chunk in iter(lambda: fp.read(1 << 20), b""):
        h.update(chunk)
print(h.hexdigest())
PY
  fi
}

PROJECT="${GCP_PROJECT:-digi-setu-dev}"
ZONE="${GCP_ZONE:-us-central1-a}"
VM="${GCP_VM:-digi-setu-live}"
REMOTE_DIR="/srv/pi/downloads"

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
  --project "$PROJECT" --zone "$ZONE" --quiet

# Step 2: move into /srv/pi/downloads with sudo, chmod, chown, then
# verify the SHA matches the one we computed locally.
gcloud compute ssh "$VM" --project "$PROJECT" --zone "$ZONE" --quiet --command "
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
