# pi-autoscale — operator runbook

Off-VM autoscaler that resizes the `digi-setu-live` VM up and down based
on real memory utilisation + active session count, so you only pay for
the box size you actually need.

Cloud Scheduler hits a Cloud Function every 10 minutes. The function
fetches `GET /api/admin/load` from the backend, picks a target tier
from the ladder, and (when needed) does a `stop → setMachineType →
start` cycle on the VM. Total downtime per resize is ~60-90s; users see
a "reconnecting…" banner and resume from where they left off.

## What you get

- **5 tiers** from `e2-small` (2 GB, $12/mo) to `e2-standard-8` (32 GB,
  $195/mo). You can lock the ladder narrower via env vars.
- **Hysteresis**: scale up the moment memory crosses 70% OR active
  sessions exceed 1 per GB. Scale down only after 30 min + 15 min
  cooldown of comfortable headroom.
- **Cooldown** between resizes (default 15 min) so a noisy single
  prompt can't flap the VM size mid-conversation.
- **Operator override** — force a specific tier instantly for incident
  response, bypassing cooldown.
- **Dry-run mode** — log decisions without acting, while you verify the
  picker behaves the way you expect.

## Architecture

```
   ┌──────────────────┐  every 10 min   ┌────────────────────────┐
   │  Cloud Scheduler │ ───── OIDC ───► │  Cloud Function (Py)   │
   │  pi-autoscale-tick                  │  pi-autoscale          │
   └──────────────────┘                  └─────────┬──────────────┘
                                                    │ GET /api/admin/load
                                                    │   (Bearer token from
                                                    │    Secret Manager)
                                                    ▼
                                          ┌─────────────────────┐
                                          │ digi-setu-live (VM) │
                                          │   FastAPI backend   │
                                          └─────────┬───────────┘
                                                    │ if resize needed:
                                                    │   compute.instances.stop
                                                    │   compute.instances.setMachineType
                                                    │   compute.instances.start
                                                    ▼
                                              <60-90s downtime>
                                              users auto-reconnect
                                              pi resumes from partial-turn save
```

## One-time setup

### 1. Generate + store the admin bearer token

```bash
openssl rand -hex 32 > /tmp/admin_token.txt
# Push into Secret Manager (the Cloud Function reads it from here):
gcloud secrets create pi-admin-load-token --replication-policy=automatic \
  --project=$GCP_PROJECT_ID
gcloud secrets versions add pi-admin-load-token --data-file=/tmp/admin_token.txt \
  --project=$GCP_PROJECT_ID
# Push the SAME value into /opt/pi/stack.env on the VM:
ADMIN_LOAD_TOKEN=$(cat /tmp/admin_token.txt)
ssh $VM "echo 'ADMIN_LOAD_TOKEN=$ADMIN_LOAD_TOKEN' | sudo tee -a /opt/pi/stack.env"
ssh $VM "sudo systemctl restart pi.service"
rm /tmp/admin_token.txt
```

Smoke-test from your laptop:

```bash
curl -fsS -H "Authorization: Bearer $(cat /tmp/admin_token.txt)" \
  https://digi-setu.com/api/admin/load | jq
```

Expected response:

```json
{
  "ok": true,
  "active_sessions": 3,
  "mem_used_bytes":  1234567890,
  "mem_total_bytes": 2147483648,
  "mem_util": 0.5749,
  "machine_type": "e2-small"
}
```

### 2. Deploy the Cloud Function + Scheduler (DRY RUN first)

```bash
cd deploy/autoscale
GCP_PROJECT_ID=digi-setu-dev \
GCP_ZONE=us-central1-a \
GCP_INSTANCE=digi-setu-live \
BACKEND_URL=https://digi-setu.com \
DRY_RUN=true \
  ./deploy.sh
```

The script:
- Enables required GCP APIs.
- Deploys the function as Python 3.11 Gen 2 (no public access).
- Grants the function's runtime SA:
  - `roles/secretmanager.secretAccessor` on `pi-admin-load-token`.
  - `roles/compute.instanceAdmin.v1` project-wide (see "Tightening
    IAM" below for the least-privilege variant).
- Creates a dedicated scheduler SA + Cloud Scheduler job that hits the
  function on the chosen cadence (default every 10 min) with OIDC auth.

### 3. Validate the dry-run decisions

Force one tick now instead of waiting 10 min:

```bash
gcloud scheduler jobs run pi-autoscale-tick --location=us-central1
gcloud functions logs read pi-autoscale --region=us-central1 --limit=20
```

You should see JSON-formatted log lines like:

```json
{
  "current_machine_type": "e2-small",
  "target_machine_type":  "e2-small",
  "current_tier": 0, "target_tier": 0,
  "reason": "holding at tier 0 (e2-small)",
  "seconds_since_last_start": 14523.7,
  "dry_run": true,
  "action": "no_change"
}
```

Wait a few cycles; provoke load if you want (open 5-10 chats with long
prompts) and confirm the function recommends scaling up.

### 4. Flip DRY_RUN off

```bash
cd deploy/autoscale
DRY_RUN=false ./deploy.sh
```

Same script, redeploys the function with live writes enabled.

## Day-to-day operations

### Force a specific tier (incident response)

```bash
FN_URL=$(gcloud functions describe pi-autoscale --region=us-central1 \
  --format='value(serviceConfig.uri)')
gcloud auth print-identity-token | xargs -I{} curl -fsS \
  -H "Authorization: Bearer {}" \
  "$FN_URL/?force_tier=3&reason=user_complaint_2026_05_10"
```

Tier indexes:

| Index | Machine type    | Memory | Approx. monthly cost (us-central1) |
|-------|------------------|--------|-------------------------------------|
| 0     | `e2-small`       | 2 GB   | $12  |
| 1     | `e2-medium`      | 4 GB   | $24  |
| 2     | `e2-standard-2`  | 8 GB   | $48  |
| 3     | `e2-standard-4`  | 16 GB  | $97  |
| 4     | `e2-standard-8`  | 32 GB  | $195 |

`force_tier` BYPASSES the cooldown — use sparingly.

### Pin the box to a fixed size

```bash
# Edit deploy/autoscale/deploy.sh or pass envs:
AUTOSCALE_MIN_TIER=2 AUTOSCALE_MAX_TIER=2 DRY_RUN=false ./deploy.sh
```

Now the function refuses to leave tier 2 (`e2-standard-2`).

### Rotate the admin token

```bash
NEW=$(openssl rand -hex 32)
echo -n "$NEW" | gcloud secrets versions add pi-admin-load-token --data-file=-
ssh $VM "sudo sed -i 's|^ADMIN_LOAD_TOKEN=.*|ADMIN_LOAD_TOKEN=$NEW|' /opt/pi/stack.env"
ssh $VM "sudo systemctl restart pi.service"
# Force the function instance to re-resolve the secret. Bumping the
# function's revision via re-deploy is the cleanest invalidation:
cd deploy/autoscale && ./deploy.sh
```

### Pause autoscaling

```bash
gcloud scheduler jobs pause pi-autoscale-tick --location=us-central1
```

`gcloud scheduler jobs resume` to undo.

## Tightening IAM (recommended for prod)

`deploy.sh` grants `roles/compute.instanceAdmin.v1` project-wide for
brevity. For least privilege, replace that grant with a custom role
that only allows the four operations we use:

```bash
gcloud iam roles create pi_autoscaler \
  --project=$GCP_PROJECT_ID \
  --title="pi autoscaler" \
  --permissions=compute.instances.get,compute.instances.start,compute.instances.stop,compute.instances.setMachineType,compute.zoneOperations.get
# Then bind it ONLY on the instance, not the project. Note: GCP doesn't
# support per-instance role bindings via gcloud yet, so the binding is
# still project-scoped, but the custom role above is what makes this
# safe — the only thing the function can do anywhere in the project is
# poke compute.instances {get, start, stop, setMachineType}.
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$FN_SA" \
  --role="projects/$GCP_PROJECT_ID/roles/pi_autoscaler"
```

Then revoke the broad role:

```bash
gcloud projects remove-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$FN_SA" \
  --role="roles/compute.instanceAdmin.v1"
```

## How the picker decides

```
Tier picker (pure function — see _pick_tier in main.py):

  Inputs:
    sessions       int   active per-session containers
    mem_util       float current mem used / mem total, 0..1
    current_idx    int   tier index right now

  Output:
    target_idx     int   tier we want to be at

  Scale up when:
    mem_util > 0.70   OR   sessions > tier_mem_gib
    AND current_idx < AUTOSCALE_MAX_TIER

  Scale down when:
    cur_used_gib < prev_tier_mem * 0.70 * 0.70   (49% of prev tier)
    AND sessions <= prev_tier_mem * 0.70
    AND current_idx > AUTOSCALE_MIN_TIER

  Hold otherwise.
```

The 0.70 × 0.70 in the scale-down branch is on purpose: it requires
the smaller tier to be _comfortable_, not just _adequate_. Otherwise
we'd scale down to a box that immediately tripped the 70% scale-up
threshold and we'd flap. Tune in `main.py:TIERS` if your workload has
different shape.

## Cost model

| Component | Cost |
|-----------|------|
| Cloud Function (Gen 2, 256 MiB, max 2 instances) | ~$0/mo (free tier) |
| Cloud Scheduler (1 job, every 10 min = 144/day) | ~$0/mo (free tier ≤ 3 jobs) |
| Secret Manager (1 secret, ~144 accesses/day)    | <$0.01/mo |
| **Autoscaler total** | **~$0/mo** |

Savings vs. always-on `e2-standard-2`:

| Scenario | Without autoscale | With autoscale | Savings |
|---|---|---|---|
| Mostly idle, occasional bursts | $48/mo | $15-25/mo | ~50% |
| Frequent bursts | $48/mo | $30-40/mo | ~25% |
| Heavy concurrent load (50+ sessions) | $48/mo (overloaded) | $50-150/mo (right-sized) | negative — but you'd be OOM-killed without it |

## Known limitations

1. **Single VM = single point of failure.** Autoscale doesn't fix
   that. A zone outage takes everyone down for the duration. If you
   need HA, you need the Option B (Managed Instance Group + Filestore)
   architecture — bigger lift, but addresses this.
2. **60-90 sec downtime per resize.** WebSockets drop; users see a
   "Reconnecting…" banner. The partial-turn save we added earlier
   means no chat history is lost, but the in-flight tool call (`pip
   install`, `cargo build`) does get killed. Backend reloads from
   chat history when the user reconnects.
3. **VM cannot resize itself while running.** The function MUST run
   off-VM (Cloud Function / Cloud Scheduler), which is why this
   directory exists at all. Don't try to move it inside the backend
   container.
4. **State on local disk = no horizontal scale.** Registry, billing
   db, and chat history all live on the VM's persistent disk. The
   autoscaler resizes the SAME disk by attaching it to a different
   machine type, which is why the data survives. But you can't run
   two of these VMs in parallel without rethinking the storage layer.
