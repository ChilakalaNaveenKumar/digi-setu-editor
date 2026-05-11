#!/usr/bin/env bash
# setup-cold-storage.sh — one-shot provision of the cold-tier bucket
# and IAM grants. Idempotent — safe to re-run.
#
# What this gives you:
#   * gs://digi-setu-cold (Coldline, regional us-central1, uniform IAM)
#   * roles/storage.objectAdmin for the digi-setu-live VM service account
#   * Lifecycle rule: archive transitions to ARCHIVE storage at 365 d
#     (cheaper still for the long tail nobody opens)
#   * 7-day undelete window — operator can restore an accidentally-
#     deleted workspace with `gsutil cp -A` from the noncurrent versions
#
# Run once after creating a new project. After that the nightly
# pi-cold-archive timer (deploy/systemd/pi-cold-archive.{service,timer})
# uses the bucket transparently.
#
# Companion script to the live snapshot policy (we attach a separate
# hourly disk-snapshot policy via gcloud directly — see the README in
# this dir).

set -euo pipefail

PROJECT="${GCP_PROJECT:-digi-setu-dev}"
REGION="${GCP_REGION:-us-central1}"
BUCKET="${COLD_BUCKET:-digi-setu-cold}"
VM="${GCP_VM:-digi-setu-live}"
ZONE="${GCP_ZONE:-us-central1-a}"

log() { printf '\033[1;34m[cold-storage]\033[0m %s\n' "$*"; }

# ── 1. Bucket ──────────────────────────────────────────────────────
if gcloud storage buckets describe "gs://${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "bucket gs://${BUCKET} already exists, skipping create"
else
  log "creating gs://${BUCKET} (Coldline, ${REGION}, uniform IAM)"
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --default-storage-class=COLDLINE \
    --uniform-bucket-level-access \
    --public-access-prevention
fi

# ── 2. Lifecycle: bump to ARCHIVE class after 365 days ─────────────
# COLDLINE: $0.004/GB-mo, 90-day min storage. Workspaces unopened a
# year are almost certainly never coming back, so push them to
# ARCHIVE ($0.0012/GB-mo) for another 4× cost reduction. Read on
# thaw is identical from the API surface (same blob, same name); the
# only difference is a slightly higher per-operation fee, which is
# trivial since each thaw is a one-shot read.
log "applying lifecycle rule (COLDLINE → ARCHIVE @ 365d)"
TMPF=$(mktemp)
trap 'rm -f "${TMPF}"' EXIT
cat > "${TMPF}" <<'JSON'
{
  "rule": [
    {
      "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
      "condition": {"age": 365, "matchesStorageClass": ["COLDLINE"]}
    }
  ]
}
JSON
gcloud storage buckets update "gs://${BUCKET}" \
  --project="${PROJECT}" \
  --lifecycle-file="${TMPF}"

# ── 3. Versioning + 7-day soft-delete on noncurrent objects ────────
# So an operator's `gsutil rm` (or a buggy reaper) can be undone
# within a week. Costs ~zero extra in steady state because writes
# are rare.
log "enabling object versioning + 7-day soft-delete"
gcloud storage buckets update "gs://${BUCKET}" \
  --project="${PROJECT}" \
  --versioning \
  --soft-delete-duration=7d

# ── 4. IAM grant for the VM SA ─────────────────────────────────────
VM_SA=$(gcloud compute instances describe "${VM}" \
  --project="${PROJECT}" --zone="${ZONE}" \
  --format='value(serviceAccounts[0].email)')
log "granting storage.objectAdmin to ${VM_SA}"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --project="${PROJECT}" \
  --member="serviceAccount:${VM_SA}" \
  --role="roles/storage.objectAdmin" \
  --condition=None >/dev/null

# ── 5. Snapshot schedule on the data disk (paired feature) ─────────
# The cold tier handles long-tail archival; the snapshot policy
# handles disaster recovery. Together they're the durability story.
# This block is idempotent: trying to re-create an existing policy
# returns ALREADY_EXISTS which we swallow.
POLICY="${SNAPSHOT_POLICY_NAME:-pi-data-hourly}"
log "ensuring snapshot policy ${POLICY} exists + attached"
gcloud compute resource-policies create snapshot-schedule "${POLICY}" \
  --project="${PROJECT}" --region="${REGION}" \
  --hourly-schedule=1 \
  --start-time=00:00 \
  --max-retention-days=7 \
  --on-source-disk-delete=keep-auto-snapshots \
  --storage-location="${REGION}" 2>&1 | grep -v "already exists" || true
gcloud compute disks add-resource-policies "${VM}" \
  --project="${PROJECT}" --zone="${ZONE}" \
  --resource-policies="${POLICY}" 2>&1 | grep -v "already" || true

log "done"
echo
echo "  Bucket:        gs://${BUCKET}"
echo "  Storage class: COLDLINE → ARCHIVE @ 365d"
echo "  IAM grant:     ${VM_SA} = storage.objectAdmin"
echo "  Snapshots:     hourly, 7-day retention on ${VM}"
echo
echo "Next: deploy/scripts/remote-deploy.sh stack    # installs the timer"
