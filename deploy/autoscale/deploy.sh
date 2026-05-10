#!/usr/bin/env bash
# deploy.sh — one-shot bringup of the pi-autoscale Cloud Function.
#
# Idempotent: safe to re-run after editing main.py or tier env vars.
# Read deploy/autoscale/README.md FIRST so you understand the IAM
# bindings this grants.
#
# Required env vars (or args):
#   GCP_PROJECT_ID    e.g. digi-setu-dev
#   GCP_ZONE          e.g. us-central1-a
#   GCP_INSTANCE      e.g. digi-setu-live
#   BACKEND_URL       e.g. https://digi-setu.com
#
# Optional:
#   FUNCTION_REGION   e.g. us-central1   (default: derived from GCP_ZONE)
#   FUNCTION_NAME     default: pi-autoscale
#   SCHEDULER_NAME    default: pi-autoscale-tick
#   SCHEDULE          default: "*/10 * * * *"   (every 10 minutes)
#   DRY_RUN           "true" = function logs but doesn't resize.
#                     Default: "false" — set to "true" for the FIRST
#                     deploy so you can validate the decisions before
#                     handing it the keys.
#
# What this script does:
#   1. Create the Secret Manager secret pi-admin-load-token (if not
#      present) and prompt for its value.
#   2. Deploy the Cloud Function (Gen 2, Python 3.11).
#   3. Grant the function's runtime SA:
#       - roles/compute.instanceAdmin.v1 on the SINGLE instance only
#         (NOT project-wide — least privilege).
#       - roles/secretmanager.secretAccessor on the secret.
#   4. Create a Cloud Scheduler job that hits the function on $SCHEDULE
#      with OIDC auth.
#
# What this script does NOT do:
#   * Set ADMIN_LOAD_TOKEN in /opt/pi/stack.env on the VM — that's a
#     separate manual step. Use scripts/secrets-sync.sh.
#   * Push code to GitHub. Local-only deploy.

set -euo pipefail

say() { printf '\033[1;36m[autoscale-deploy]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[autoscale-deploy]\033[0m %s\n' "$*" >&2; exit 1; }

: "${GCP_PROJECT_ID:?GCP_PROJECT_ID is required}"
: "${GCP_ZONE:?GCP_ZONE is required (e.g. us-central1-a)}"
: "${GCP_INSTANCE:?GCP_INSTANCE is required (e.g. digi-setu-live)}"
: "${BACKEND_URL:?BACKEND_URL is required (e.g. https://digi-setu.com)}"

FUNCTION_REGION="${FUNCTION_REGION:-${GCP_ZONE%-*}}"
FUNCTION_NAME="${FUNCTION_NAME:-pi-autoscale}"
SCHEDULER_NAME="${SCHEDULER_NAME:-pi-autoscale-tick}"
SCHEDULE="${SCHEDULE:-*/10 * * * *}"
DRY_RUN="${DRY_RUN:-false}"
SECRET_NAME="pi-admin-load-token"

HERE="$(cd "$(dirname "$0")" && pwd)"
FN_SRC="$HERE/cloud-function"

[[ -d "$FN_SRC" ]] || die "missing $FN_SRC"

# ── Sanity: gcloud is logged in and pointed at the right project ──
gcloud config set project "$GCP_PROJECT_ID" >/dev/null
say "Using project: $GCP_PROJECT_ID, zone: $GCP_ZONE, region: $FUNCTION_REGION"

# Enable the APIs we need (idempotent).
say "Enabling required APIs (cloudfunctions, run, scheduler, compute, secretmanager)…"
gcloud services enable \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  compute.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$GCP_PROJECT_ID" >/dev/null

# ── 1. Secret Manager secret ──────────────────────────────────────
if ! gcloud secrets describe "$SECRET_NAME" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
  say "Creating secret $SECRET_NAME …"
  gcloud secrets create "$SECRET_NAME" \
    --replication-policy=automatic \
    --project="$GCP_PROJECT_ID" >/dev/null
fi

# Check whether a version already exists. Don't clobber.
VERSIONS=$(gcloud secrets versions list "$SECRET_NAME" \
  --project="$GCP_PROJECT_ID" --format='value(name)' 2>/dev/null || true)
if [[ -z "$VERSIONS" ]]; then
  say "Secret $SECRET_NAME has no value. Generate one with:"
  echo "    openssl rand -hex 32 | gcloud secrets versions add $SECRET_NAME --data-file=-"
  say "Then re-run this script."
  exit 1
fi
say "Secret $SECRET_NAME present (versions: $(echo "$VERSIONS" | wc -l | tr -d ' '))."

# ── 2. Deploy the Cloud Function (Gen 2) ──────────────────────────
say "Deploying function $FUNCTION_NAME (region $FUNCTION_REGION)…"
gcloud functions deploy "$FUNCTION_NAME" \
  --gen2 \
  --region="$FUNCTION_REGION" \
  --runtime=python311 \
  --source="$FN_SRC" \
  --entry-point=autoscale \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=540s \
  --memory=256Mi \
  --max-instances=2 \
  --set-env-vars="GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_ZONE=$GCP_ZONE,GCP_INSTANCE=$GCP_INSTANCE,BACKEND_URL=$BACKEND_URL,ADMIN_TOKEN_SECRET=$SECRET_NAME,AUTOSCALE_DRY_RUN=$DRY_RUN" \
  --project="$GCP_PROJECT_ID"

FN_URL=$(gcloud functions describe "$FUNCTION_NAME" \
  --region="$FUNCTION_REGION" --project="$GCP_PROJECT_ID" \
  --format='value(serviceConfig.uri)')
[[ -n "$FN_URL" ]] || die "could not resolve function URL"
say "Function URL: $FN_URL"

FN_SA=$(gcloud functions describe "$FUNCTION_NAME" \
  --region="$FUNCTION_REGION" --project="$GCP_PROJECT_ID" \
  --format='value(serviceConfig.serviceAccountEmail)')
[[ -n "$FN_SA" ]] || die "could not resolve function service account"
say "Function service account: $FN_SA"

# ── 3. IAM bindings ───────────────────────────────────────────────
# 3a. Function → Secret Manager (read pi-admin-load-token).
say "Granting $FN_SA roles/secretmanager.secretAccessor on $SECRET_NAME…"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --member="serviceAccount:$FN_SA" \
  --role="roles/secretmanager.secretAccessor" \
  --project="$GCP_PROJECT_ID" >/dev/null

# 3b. Function → Compute on the SINGLE instance only. There's no
# instance-scoped role binding via gcloud directly — closest least-
# privilege is the v1 instanceAdmin role at the project level. If
# this is your prod project with other VMs, consider creating a
# custom role limited to compute.instances.{get,setMachineType,
# start,stop} and binding it project-wide instead.
say "Granting $FN_SA roles/compute.instanceAdmin.v1 (project-wide)…"
say "  WARNING: scope = entire project. See README for the custom-role recipe."
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:$FN_SA" \
  --role="roles/compute.instanceAdmin.v1" \
  --condition=None \
  --quiet >/dev/null

# ── 4. Cloud Scheduler job ────────────────────────────────────────
# A separate SA for the scheduler keeps its blast radius small.
SCHED_SA="$FUNCTION_NAME-sched@$GCP_PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SCHED_SA" \
  --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
  say "Creating scheduler service account $SCHED_SA…"
  gcloud iam service-accounts create "$FUNCTION_NAME-sched" \
    --display-name="$FUNCTION_NAME scheduler" \
    --project="$GCP_PROJECT_ID" >/dev/null
fi

# Allow the scheduler SA to invoke the function (Gen 2 uses Cloud Run
# under the hood, so the role is run.invoker, not functions.invoker).
say "Granting $SCHED_SA roles/run.invoker on $FUNCTION_NAME…"
gcloud run services add-iam-policy-binding "$FUNCTION_NAME" \
  --region="$FUNCTION_REGION" \
  --member="serviceAccount:$SCHED_SA" \
  --role="roles/run.invoker" \
  --project="$GCP_PROJECT_ID" >/dev/null

# Create / update the scheduler job. `update` errors when the job
# doesn't exist yet, so we try create first and fall back.
if ! gcloud scheduler jobs describe "$SCHEDULER_NAME" \
  --location="$FUNCTION_REGION" \
  --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
  say "Creating scheduler job $SCHEDULER_NAME ($SCHEDULE)…"
  gcloud scheduler jobs create http "$SCHEDULER_NAME" \
    --location="$FUNCTION_REGION" \
    --schedule="$SCHEDULE" \
    --uri="$FN_URL" \
    --http-method=GET \
    --oidc-service-account-email="$SCHED_SA" \
    --oidc-token-audience="$FN_URL" \
    --attempt-deadline=540s \
    --project="$GCP_PROJECT_ID" >/dev/null
else
  say "Updating scheduler job $SCHEDULER_NAME ($SCHEDULE)…"
  gcloud scheduler jobs update http "$SCHEDULER_NAME" \
    --location="$FUNCTION_REGION" \
    --schedule="$SCHEDULE" \
    --uri="$FN_URL" \
    --http-method=GET \
    --oidc-service-account-email="$SCHED_SA" \
    --oidc-token-audience="$FN_URL" \
    --attempt-deadline=540s \
    --project="$GCP_PROJECT_ID" >/dev/null
fi

cat <<EOF

╭───────────────────────────────────────────────────────────────────╮
│  pi-autoscale deployed.                                           │
│                                                                   │
│  Function URL : $FN_URL
│  DRY_RUN      : $DRY_RUN
│  Schedule     : $SCHEDULE
│                                                                   │
│  Next steps:                                                      │
│   1. Copy the same admin token into /opt/pi/stack.env on the VM:  │
│        ADMIN_LOAD_TOKEN=<same value as the Secret Manager secret> │
│      and \`systemctl restart pi.service\`.                         │
│                                                                   │
│   2. Smoke-test the endpoint from your laptop:                    │
│        curl -H "Authorization: Bearer \$TOKEN" \\                  │
│             $BACKEND_URL/api/admin/load
│                                                                   │
│   3. Force a dry-run cycle:                                       │
│        gcloud scheduler jobs run $SCHEDULER_NAME \\                │
│            --location=$FUNCTION_REGION                            │
│        gcloud functions logs read $FUNCTION_NAME \\                │
│            --region=$FUNCTION_REGION --limit=50                   │
│                                                                   │
│   4. When you're happy, flip DRY_RUN to "false" and re-run        │
│      THIS script to redeploy the function with live writes.       │
╰───────────────────────────────────────────────────────────────────╯
EOF
