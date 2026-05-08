#!/usr/bin/env bash
# backup-to-gcs.sh — nightly snapshot of /srv/pi/data → GCS.
#
# Captures everything that MUST survive a VM rebuild:
#   /srv/pi/data/registry.json   workspace + session catalogue (titles,
#                                pinned model, last-used)
#   /srv/pi/data/chats/          per-session JSONL chat history (pi
#                                replays this on respawn)
#   /srv/pi/data/billing.db      SQLite credit ledger + activity log
#   /srv/pi/data/users/          per-user preferences (permission_mode)
#   /srv/pi/data/shadows/        shadow-git per-workspace history
#   /srv/pi/data/workspaces/     workspace files THE USER CREATED
#                                (Typst sources, generated PDFs, etc.)
#
# Excludes (single source of truth: services/storage_exclusions.py):
#   uploads/            user-supplied attachments — they live on the
#                        user's own device; re-uploading is cheap
#   node_modules/       regenerable from package-lock
#   .cache/, __pycache__/, .venv/, .pytest_cache/
#   *.pyc, *.swp, .DS_Store, *.lock
#
# Hot-copy of billing.db via sqlite3 .backup so we don't grab a torn
# read mid-write. Everything else is content-addressed enough that
# rsync semantics are fine.
#
# Run via cron (suggested 03:17 UTC, off-peak):
#   17 3 * * *  /opt/pi/scripts/backup-to-gcs.sh
#
# Or one-shot for testing:
#   sudo /opt/pi/scripts/backup-to-gcs.sh
#
# Env knobs:
#   GCS_BACKUP_BUCKET   gs://… target bucket (no trailing slash).
#                       Default: gs://digi-setu-pi-backups
#   DATA_ROOT           Source path (default /srv/pi/data).
#   RETENTION_DAYS      Local snapshot retention before push (default 0
#                       = no local copies kept after upload).
#   DRY_RUN=1           Print commands; don't run them.

set -euo pipefail

BUCKET="${GCS_BACKUP_BUCKET:-gs://digi-setu-pi-backups}"
DATA_ROOT="${DATA_ROOT:-/srv/pi/data}"
DRY_RUN="${DRY_RUN:-0}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HOST="$(hostname -s)"
ARCHIVE_NAME="data-${HOST}-${STAMP}.tar.zst"
WORK_DIR="$(mktemp -d /tmp/pi-backup.XXXXXX)"
trap 'rm -rf "${WORK_DIR}"' EXIT

log()  { printf '\033[1;36m[backup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[backup]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[backup]\033[0m %s\n' "$*" >&2; exit 1; }

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+ %s\n' "$*"
  else
    printf '+ %s\n' "$*"
    "$@"
  fi
}

# ── 0. Sanity ──────────────────────────────────────────────────────
if [[ ! -d "${DATA_ROOT}" ]]; then
  fail "DATA_ROOT does not exist: ${DATA_ROOT}"
fi
command -v gsutil >/dev/null || fail "gsutil not on PATH (install google-cloud-sdk)"
command -v zstd   >/dev/null || fail "zstd not on PATH (apt-get install zstd)"

# ── 1. Hot-copy billing.db (atomic snapshot) ───────────────────────
# Plain `cp` would race against the backend's writer process. SQLite's
# online backup API takes a consistent snapshot even while writers are
# active. Skip silently if billing.db doesn't exist yet (fresh VM).
SNAPSHOT_DIR="${WORK_DIR}/snapshot"
mkdir -p "${SNAPSHOT_DIR}"

if [[ -f "${DATA_ROOT}/billing.db" ]]; then
  log "Hot-copying billing.db via sqlite3 .backup"
  if command -v sqlite3 >/dev/null; then
    run sqlite3 "${DATA_ROOT}/billing.db" ".backup '${SNAPSHOT_DIR}/billing.db'"
  else
    warn "sqlite3 not installed — falling back to cp (small risk of torn read)"
    run cp -a "${DATA_ROOT}/billing.db" "${SNAPSHOT_DIR}/billing.db"
  fi
fi

# ── 2. Build the tar.zst archive ───────────────────────────────────
# Excludes mirror services/storage_exclusions.py — keep them in sync.
# `--exclude=*/uploads` matches both `workspaces/*/workspace/uploads/`
# and any future top-level uploads dir.
log "Archiving ${DATA_ROOT} → ${WORK_DIR}/${ARCHIVE_NAME}"
ARCHIVE_PATH="${WORK_DIR}/${ARCHIVE_NAME}"

# Flags layout — keep the order stable so the diff is easy to read.
# `-I 'zstd -19 -T0'` = max compression, all cores. ~30s for 1 GiB.
TAR_FLAGS=(
  --create
  --file "${ARCHIVE_PATH}"
  --use-compress-program 'zstd -19 -T0'
  --exclude='*/uploads'
  --exclude='*/node_modules'
  --exclude='*/.cache'
  --exclude='*/__pycache__'
  --exclude='*/.venv'
  --exclude='*/.pytest_cache'
  --exclude='*.pyc'
  --exclude='*.swp'
  --exclude='.DS_Store'
  --exclude='*.lock'
)

# Source paths — explicit list so we never accidentally pick up
# something new the backend writes outside of /srv/pi/data.
run tar "${TAR_FLAGS[@]}" \
  -C "$(dirname "${DATA_ROOT}")" \
  "$(basename "${DATA_ROOT}")"

# Bolt the live billing.db snapshot in (it's outside DATA_ROOT in the
# work dir). Stored at billing.db.live so a restore knows it's the
# atomic copy and overrides whatever was inside data/.
if [[ -f "${SNAPSHOT_DIR}/billing.db" ]]; then
  run tar --append \
    --file "${ARCHIVE_PATH}" \
    --use-compress-program 'zstd -19 -T0' \
    -C "${SNAPSHOT_DIR}" \
    --transform='s,^,billing-snapshot/,' \
    billing.db
fi

ARCHIVE_BYTES="$(stat --printf='%s' "${ARCHIVE_PATH}" 2>/dev/null || echo '?')"
log "Archive size: ${ARCHIVE_BYTES} bytes"

# ── 3. Upload to GCS ───────────────────────────────────────────────
GCS_DEST="${BUCKET}/$(date -u +%Y/%m/%d)/${ARCHIVE_NAME}"
log "Uploading → ${GCS_DEST}"
run gsutil -q cp "${ARCHIVE_PATH}" "${GCS_DEST}"

# Latest pointer for fast disaster-recovery (`gsutil cp gs://…/latest.tar.zst .`).
run gsutil -q cp "${ARCHIVE_PATH}" "${BUCKET}/latest.tar.zst"

# ── 4. Done ────────────────────────────────────────────────────────
log "Backup complete. Verify with:"
log "  gsutil ls -lh ${BUCKET}/$(date -u +%Y/%m/%d)/"
log "Restore recipe:"
log "  gsutil cp ${BUCKET}/latest.tar.zst /tmp/data.tar.zst"
log "  sudo systemctl stop pi"
log "  sudo tar --use-compress-program=zstd -xf /tmp/data.tar.zst -C /srv/pi/"
log "  sudo cp /srv/pi/data/billing-snapshot/billing.db /srv/pi/data/billing.db"
log "  sudo rm -rf /srv/pi/data/billing-snapshot"
log "  sudo systemctl start pi"
