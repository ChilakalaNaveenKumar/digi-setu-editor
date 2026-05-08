# DEPLOY — pi-typst-test → digi-setu.com

Single-page runbook. Every command is copy-pasteable.
For the *why* behind each piece read `deploy/README.md`; this doc
is for the operator who already knows the architecture and just
wants the sequence.

> **Before you cut traffic over to the new stack**, read
> [`deploy/HARDENING.md`](./HARDENING.md) end-to-end and tick every
> box. That doc covers everything OUTSIDE the repo (Cloudflare,
> Clerk, Stripe, GCP IAM, SSH, GCS bucket, registrar). The repo-side
> hardening is already wired into this runbook.

---

## 0. Prerequisites — verify ONCE

```bash
# gcloud signed in to the right user + project
gcloud auth list
gcloud config set project digi-setu-dev
gcloud config set compute/zone us-central1-a

# Application Default Credentials (used by Cloud Build + remote-deploy.sh)
gcloud auth application-default login

# Verify the VM exists
gcloud compute instances describe digi-setu-live \
  --project digi-setu-dev --zone us-central1-a \
  --format='value(name,status)'
# → digi-setu-live  RUNNING
```

### Verify the Vertex SA binding (single most common breakage)

```bash
# Find the SA actually attached to the VM
SA=$(gcloud compute instances describe digi-setu-live \
       --project digi-setu-dev --zone us-central1-a \
       --format='value(serviceAccounts[0].email)')
echo "VM SA = ${SA}"

# Confirm it has aiplatform.user on the Vertex billing project
gcloud projects get-iam-policy frontend-472812 \
  --flatten='bindings[].members' \
  --filter="bindings.role:roles/aiplatform.user AND bindings.members:serviceAccount:${SA}" \
  --format='value(bindings.role)'
# → roles/aiplatform.user   (anything else = grant it)

# Grant if missing
gcloud projects add-iam-policy-binding frontend-472812 \
  --member="serviceAccount:${SA}" \
  --role='roles/aiplatform.user'
```

### Verify Artifact Registry repo exists

```bash
gcloud artifacts repositories describe digi-setu \
  --project digi-setu-dev --location us-central1 \
  --format='value(name,format)'
# → projects/digi-setu-dev/.../digi-setu  DOCKER

# Create only if missing (typst-agent already created it)
gcloud artifacts repositories create digi-setu \
  --project digi-setu-dev --location us-central1 \
  --repository-format=docker
```

### Create the GCS backup bucket (first deploy only)

```bash
# Multi-region bucket so we survive a single-region outage. IA storage
# class because we read the archive only on disaster recovery.
gsutil mb -p digi-setu-dev -c NEARLINE -l us \
  gs://digi-setu-pi-backups

# 90-day retention — anything older is auto-deleted
cat > /tmp/lifecycle.json <<'JSON'
{
  "lifecycle": {
    "rule": [
      { "action": {"type": "Delete"},
        "condition": {"age": 90} }
    ]
  }
}
JSON
gsutil lifecycle set /tmp/lifecycle.json gs://digi-setu-pi-backups

# Grant the VM SA permission to write to the bucket
SA=$(gcloud compute instances describe digi-setu-live \
       --project digi-setu-dev --zone us-central1-a \
       --format='value(serviceAccounts[0].email)')
gsutil iam ch "serviceAccount:${SA}:roles/storage.objectAdmin" \
  gs://digi-setu-pi-backups
```

---

## 1. Populate `deploy/stack.env` (one-time, then forever)

The file already exists locally (`deploy/stack.env`, gitignored). It's
pre-filled with everything except `CLERK_WEBHOOK_SECRET`, which you
add after creating the webhook in Clerk:

* Clerk dashboard → **Webhooks** → **Add endpoint**
  - URL: `https://digi-setu.com/api/auth/webhook`
  - Events: tick `user.deleted`
  - Copy the *Signing Secret* → paste into `CLERK_WEBHOOK_SECRET=` in
    `deploy/stack.env`

While you're in Clerk, double-check:
* **Domains** → `digi-setu.com` is added (CNAME `clerk.digi-setu.com →
  frontend-api.clerk.com` already in your zone, since the publishable
  key embeds it).
* **Customization → Account portal → Redirects**:
  - After sign-up fallback: `https://digi-setu.com/sessions`
  - After sign-in fallback: `https://digi-setu.com/sessions`
  - After logo click:       `https://digi-setu.com/`

The `/sessions` route is wired in the SPA (alias to the picker).

---

## 2. Push to Bitbucket

The deploy works either way (Cloud Build tarballs the local source
tree), but the image tag is `git rev-parse --short HEAD`, so for
traceability commit + push first.

```bash
cd "$(dirname "$0")/.."   # repo root
git status                # 91 changes expected
git add -A
git commit -m "feat: pi-typst-test ready for production deploy"
git push origin main
```

---

## 3. Provision the VM (skip if already done — typst-agent already provisioned it)

```bash
# Push the deploy bundle and run provision-vm.sh (idempotent)
gcloud compute scp --recurse deploy/ digi-setu-live:~/pi-deploy/ \
  --project digi-setu-dev --zone us-central1-a

gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo bash ~/pi-deploy/scripts/provision-vm.sh'
```

This installs docker if missing, creates the `app` user (uid 1100),
materialises `/srv/pi/{state,data,www}` + `/srv/caddy`, and enables
(but does not start) `pi-prepare.service` + `pi.service`.

---

## 4. Push stack files (compose, Caddyfile, systemd, scripts, stack.env)

> **One-time DNS prereq for the desktop relay (added 2026-05-08).**
> The Caddyfile now serves `api.digi-setu.com` (the desktop client's
> cloud-relay endpoint). Before this push, add the subdomain in
> Cloudflare DNS:
>
> 1. Cloudflare dashboard → `digi-setu.com` zone → **DNS** tab.
> 2. **Add record**:
>    - Type: `CNAME`
>    - Name: `api`
>    - Target: `digi-setu.com`  (so it follows the apex automatically)
>    - Proxy status: **DNS only (grey cloud)** — Caddy must terminate
>      TLS itself for the `wss://` upgrade. Orange-cloud proxy mode
>      strips the `Upgrade` header on the free plan.
>    - TTL: Auto.
> 3. Wait ~30 s for propagation. Verify:
>    ```bash
>    dig +short api.digi-setu.com
>    # → should return the same IP as digi-setu.com
>    ```
> 4. The existing `CLOUDFLARE_API_TOKEN` in `stack.env` is zone-scoped
>    so it already covers `api.digi-setu.com` — no token rotation
>    needed.
>
> After the next `remote-deploy.sh stack` + `systemctl reload pi`,
> Caddy issues a fresh Let's Encrypt cert for `api.digi-setu.com` via
> the DNS-01 challenge. First request to `https://api.digi-setu.com/v1/health`
> may take ~30 s while the cert is being signed.

```bash
deploy/scripts/remote-deploy.sh stack
```

This SCPs `docker-compose.yml`, `caddy/Caddyfile`, `caddy/Dockerfile`,
both systemd units, the cutover script, AND `deploy/stack.env`
(detected automatically because it exists locally; chmod 0600 root on
the VM). Reloads systemd but does NOT start `pi.service` yet.

Verify the file landed correctly:

```bash
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo ls -la /opt/pi/ && sudo head -15 /opt/pi/stack.env'
```

---

## 5. Build + push the SPA bundle

```bash
deploy/scripts/remote-deploy.sh frontend
```

Builds the Vue 3 SPA inside `deploy/Dockerfile.frontend` locally,
tar-streams `dist/` over `gcloud ssh` into `/srv/pi/www`. Caddy serves
it RO from there.

---

## 6. Build + roll the backend image (Cloud Build → AR → VM)

```bash
deploy/scripts/remote-deploy.sh backend
```

Submits Cloud Build (`E2_HIGHCPU_8`, ~6 min for a clean build, ~90 s
with cache hits), tags the image `:<git-sha>` and `:latest`, pulls on
the VM, restarts `pi.service`. Sleeps 5 s and prints `systemctl
status` so you can see if anything blew up.

---

## 7. Smoke-test BEFORE cutover (typst-agent still serves the public)

`pi-backend` listens on `127.0.0.1:8788`. Caddy isn't bound yet
(typst-agent holds :443). Probe the new backend directly through SSH:

```bash
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'curl -fsS http://127.0.0.1:8788/healthz; echo; \
             curl -fsS http://127.0.0.1:8788/api/config | head'
```

Expect `{"status":"ok"}` and a JSON config blob with `auth_required: true`.

Tail the backend logs while doing it (separate terminal):

```bash
deploy/scripts/remote-deploy.sh logs
```

---

## 8. Cut over (~5 second blip on the public site)

```bash
deploy/scripts/remote-deploy.sh cutover
```

Inside the VM:
1. `systemctl stop typst-agent.service` (legacy stack releases :443).
2. `cp -a /srv/typst-agent/users → /srv/pi/legacy-backup/typst-agent-users-<stamp>/`
3. `systemctl restart pi-prepare.service && systemctl restart pi.service`.
4. Caddy comes up, Cloudflare DNS-01 issues a fresh cert (already in
   `/srv/caddy/data` from typst-agent's stack — cert reuse is automatic).
5. Polls `/healthz` for up to 60 s.

Verify on real DNS:

```bash
curl -fsS https://digi-setu.com/healthz   # → {"status":"ok"}
curl -fsS https://digi-setu.com/api/config | jq .auth_required
# → true
```

Click around in the browser:
- Visit `https://digi-setu.com/` → bounces to Clerk's hosted sign-in.
- Sign in with Google → redirects back to `https://digi-setu.com/sessions`.
- Create a chat → ask "Compile hello world in Typst" → PDF preview renders.
- `/activity` shows the cost of that prompt.
- `/pricing` shows three plans with check-icons.

---

## 9. Wire the nightly GCS backup (one-time)

```bash
# Push the backup script to /opt/pi/scripts/
gcloud compute scp deploy/scripts/backup-to-gcs.sh \
  digi-setu-live:/tmp/backup-to-gcs.sh \
  --project digi-setu-dev --zone us-central1-a

gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo install -m 0755 -o root -g root /tmp/backup-to-gcs.sh /opt/pi/scripts/backup-to-gcs.sh && \
             sudo apt-get install -y zstd sqlite3 && \
             sudo /opt/pi/scripts/backup-to-gcs.sh'
# Should print "Backup complete." and "Verify with: gsutil ls -lh ..."

# Install the cron entry (03:17 UTC daily)
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'echo "17 3 * * * root /opt/pi/scripts/backup-to-gcs.sh >> /var/log/pi-backup.log 2>&1" | \
             sudo tee /etc/cron.d/pi-backup && sudo chmod 0644 /etc/cron.d/pi-backup'

# Verify
gsutil ls -lh gs://digi-setu-pi-backups/
```

---

## 10. Verify the security posture is what you think it is

The egress firewall is now wired automatically by `remote-deploy.sh
stack` — verify it ran:

```bash
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo systemctl status pi-firewall --no-pager | sed -n "1,5p" && \
             sudo nft list ruleset | grep -A 6 pi_egress'
# Expect: Active: active (exited)  + the chain with three drop rules
```

Now confirm the metadata server is actually unreachable from inside
the container — this is the IAM-token-theft hole:

```bash
# From INSIDE the container, as the AI's bash subprocess will run.
# We exec curl and expect a TIMEOUT (not a 200 OK), which proves
# the kernel rule blocks the packet.
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo docker exec --user app pi-backend \
               curl -m 3 -fsS http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token \
               -H "Metadata-Flavor: Google" 2>&1 ; echo "exit=$?"'
# Expect: curl: (28) Connection timed out  exit=28      ← rule worked
# If you see: an actual access_token in the output                  ← rule did NOT load
# If you see: exit=22 with "Metadata-Flavor required"               ← rule did NOT load
```

That single test answers the question "can the AI steal our Vertex
IAM token by curling the metadata server" — **with the firewall on,
no; without it, yes**.

```bash
# 10b. Stripe webhook end-to-end test (Stripe CLI on your laptop)
stripe listen --forward-to https://digi-setu.com/api/billing/webhook
# Then in Stripe dashboard → Developers → Webhooks → Send test event

# 10c. Clerk webhook end-to-end test
# Clerk dashboard → Webhooks → your endpoint → Send Example
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo docker logs --tail 30 pi-backend 2>&1 | grep -i webhook'
# Should see  "auth-webhook ok ignored=user.created"
```

## Threat model after v1.1 (dual-uid sandbox is live)

The dual-uid sandbox shipped in v1.1 — pi (and every bash subprocess
the AI spawns) now runs as `uid 1000` while the backend stays at
`uid 1100`. Filesystem permissions on `/srv/pi/data/` enforce the
boundary the kernel can't be tricked out of:

| Path | Mode/Owner | Sandbox can… |
|------|-----------|--------------|
| `/srv/pi/data/billing.db` | 0600 1100:1100 | NOTHING (EACCES on read) |
| `/srv/pi/data/registry.json` | 0600 1100:1100 | NOTHING |
| `/srv/pi/data/users/` | 0700 1100:1100 | NOTHING (can't even traverse) |
| `/srv/pi/data/workspaces/` | 0710 1100:1000 | cd-by-uuid only (no `ls`) |
| `/srv/pi/data/workspaces/<wsid>/` | 2770 1000:1000 | rwx (own this) |
| `/srv/pi/data/chats/<sid>/` | 2770 1000:1000 | rwx (own this) |

The 0710 mode on parent dirs is the key: `--x` lets the sandbox
`cd <known-uuid>` but not `ls` to discover others. Combined with
uuid4 wsids (122 bits of entropy), enumerating other users'
workspaces is computationally infeasible.

For the full threat model + verification commands see
[`HARDENING.md` § 11](./HARDENING.md#11-dual-uid-sandbox-v11--what-it-does-and-how-to-verify).

### What v1.1 still cannot defend against

The remaining architectural gap (tracked as Phase-5+ in HARDENING.md):

**Same sandbox uid for every workspace.** All sessions on the same
container share `uid 1000`. If a hostile prompt somehow obtains a
specific other workspace's uuid (note: 122-bit uuid4, infeasible to
guess), it COULD `cd /srv/pi/data/workspaces/<that-uuid>` and read
the files, because mode 2770 grants the owner uid full rwx and the
owner uid is shared. Closing this requires either dynamic per-
workspace user creation or per-session bubblewrap namespaces —
significant operational complexity for a closed-beta deployment.

**Phase 5 plan (full per-tenant isolation, ~1 week of work)**:

1. ~~Add a host-side `pi-tenant` user (uid 1000), mode 0700.~~ **DONE in v1.1**
2. ~~Wrap every `bash` call from `pi --mode rpc` with `runuser -u pi-tenant`.~~ **DONE in v1.1** (`setpriv --reuid 1000`)
3. ~~Move `/srv/pi/data/{billing.db,registry.json,users/}` to file-mode-isolated locations.~~ **DONE in v1.1** (file modes 0600/0700 owned by 1100, sandbox is uid 1000)
4. **Per-session bubblewrap namespace** so each pi spawn sees ONLY its workspace bind-mount. Closes the cross-workspace gap above.
5. **Per-tenant uid offsets** (uid = 100000 + hash(user_id)) so even within the bubblewrap, two tenants never share an effective uid.

Until then, **this is suitable for a closed beta**. The 122-bit
uuid entropy makes the cross-workspace gap a defense-in-depth
concern rather than a practical exploit, but a public launch
should ship the bubblewrap layer first.

---

## Quick reference

| What | Command |
|------|---------|
| Push compose/caddy/systemd | `deploy/scripts/remote-deploy.sh stack` |
| Push frontend SPA only | `deploy/scripts/remote-deploy.sh frontend` |
| Build + roll backend image | `deploy/scripts/remote-deploy.sh backend` |
| Cut over from typst-agent | `deploy/scripts/remote-deploy.sh cutover` |
| Tail logs | `deploy/scripts/remote-deploy.sh logs` |
| SSH to the VM | `deploy/scripts/remote-deploy.sh ssh` |
| Reload after stack.env edit | `gcloud compute ssh digi-setu-live --command 'sudo systemctl reload pi'` |
| Hard restart | `gcloud compute ssh digi-setu-live --command 'sudo systemctl restart pi'` |
| Run a backup now | `gcloud compute ssh digi-setu-live --command 'sudo /opt/pi/scripts/backup-to-gcs.sh'` |
| Restore from latest backup | see footer of `backup-to-gcs.sh` |

---

## Common breakages

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Vertex 403 on first prompt | SA missing `aiplatform.user` on `frontend-472812` | Run the `add-iam-policy-binding` from §0 |
| Caddy stuck "obtaining TLS" | Cloudflare token wrong scope / wrong zone | Recreate token with **Zone / DNS / Edit** for `digi-setu.com`, paste into `stack.env`, `systemctl reload pi` |
| `pi.service` won't start | Stray quote in `stack.env` | `journalctl -u pi.service -n 50`; fix the bad line; `systemctl restart pi-prepare && systemctl restart pi` |
| WebSocket 502 mid-stream | Caddy buffering | Confirm `/ws/*` is on `stream_proxy` snippet (it is by default) |
| OOM-killed backend | pi keeps chat history in memory | `gcloud compute instances set-machine-type digi-setu-live --machine-type=e2-standard-4` |
| Clerk webhook 401 | `CLERK_WEBHOOK_SECRET` empty or mismatched | Copy fresh secret from Clerk dashboard, edit `stack.env`, reload pi |
| Stripe webhook 400 (signature) | `STRIPE_WEBHOOK_SECRET` mismatch | Same: copy, paste, reload |
| `typst: command not found` in chat | Image is from before the typst install was added to Dockerfile | `deploy/scripts/remote-deploy.sh backend` to rebuild the image |
| Doc renders with wrong fonts (everything looks like Linux Libertine) | `TYPST_FONT_PATHS` not loaded | `docker exec pi-backend env \| grep TYPST_FONT_PATHS` should print `/usr/local/share/fonts/digi-setu:/usr/local/share/fonts:/usr/share/fonts` |
| `@preview/cetz` import takes 30 s every time | Package cache not pinned to bind-mount | `docker exec pi-backend env \| grep TYPST_PACKAGE_CACHE_PATH` should print `/srv/pi/data/typst-packages` |
| Metadata server reachable from container (`curl http://169.254.169.254/...` returns a token) | Firewall didn't load | `sudo systemctl status pi-firewall`; check `/etc/nftables.d/pi-egress.nft` exists; `sudo systemctl restart pi-firewall` |
