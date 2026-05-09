# Digi Setu — hosted deployment

Deploys the FastAPI + Vue + pi stack to **digi-setu.com**, replacing
the legacy `typst-agent` stack on the same VM (`digi-setu-live` in
`digi-setu-dev/us-central1-a`). Same domain, same Cloudflare zone,
same Artifact Registry, same systemd shape — cutover is a
`scripts/remote-deploy.sh cutover` away.

> **Status:** auth wired (Clerk), structure-complete. None of the
> `gcloud` push commands have been run yet — populate `stack.env`
> with real Clerk + Cloudflare values first, then `remote-deploy.sh
> all`.

## Layout

```
deploy/
├── Dockerfile.backend          # Python 3.11 + Node 22 + pi + patches → uvicorn
├── Dockerfile.frontend         # Node 22 → static dist/ (extracted, not run)
├── docker-compose.yml          # backend + caddy (host networking)
├── stack.env.example           # template for /opt/pi/stack.env
├── .dockerignore
├── caddy/
│   ├── Caddyfile               # TLS + SPA + reverse proxy /api + /ws
│   └── Dockerfile              # caddy + caddy-dns/cloudflare module
├── systemd/
│   ├── pi.service              # compose pull/build/up
│   └── pi-prepare.service      # one-shot /srv layout
└── scripts/
    ├── provision-vm.sh                    # docker + systemd + /srv layout (run once per VM)
    ├── remote-deploy.sh                   # build/push/roll from a laptop (laptop-side)
    └── cutover-from-typst-agent.sh        # stop typst-agent, start pi (run on the VM)
```

## Architecture

```
                  ┌────────────────────────────────────────────────┐
  Cloudflare DNS  │ digi-setu-live (us-central1-a)                 │
  digi-setu.com → │                                                │
                  │  ┌──── caddy (host net, :80/:443) ─────────┐   │
                  │  │    TLS via Cloudflare DNS-01            │   │
                  │  │    /            → /srv/pi/www (SPA)     │   │
                  │  │    /api/*       → 127.0.0.1:8788        │   │
                  │  │    /ws/*        → 127.0.0.1:8788 (WS)   │   │
                  │  └──────────────────────────────────────────┘   │
                  │                       ▲                         │
                  │  ┌──── pi-backend (host net, :8788) ──────┐    │
                  │  │    FastAPI (uvicorn, app:app)           │    │
                  │  │    spawns one `pi --mode rpc` per chat  │    │
                  │  │    cwd = /srv/pi/data/workspaces/<wsid> │    │
                  │  │    persists JSONL  /srv/pi/data/chats/  │    │
                  │  │    shadow git      /srv/pi/data/shadows │    │
                  │  └──────────────────────────────────────────┘   │
                  │                       │                         │
                  │  /srv/pi/state  (0700 root)  auth.db, jwt key   │
                  │  /srv/pi/data   (0700 1100)  per-user folders   │
                  │  /srv/pi/www    (0755 root)  SPA bundle         │
                  └────────────────────────────────────────────────┘
                                          │
                                          ▼
                          Vertex AI (anthropic-vertex)
                          via the VM's compute SA + ADC
                          (no JSON key file in the image)
```

## What "v1" means here

* **One container, one user.** Backend runs as uid 1100 (`app`); pi
  inherits that uid for now. Workspace isolation comes from the
  per-workspace `cwd` we hand `pi --mode rpc`.
* **No multi-tenant uid sandbox yet.** Phase 5 swaps the workspace
  cwd execve for a `runuser -u pi-tenant-<uid>` drop the same way
  `typst-agent/sandbox.py` does. Until then a clever prompt could
  still escape the workspace folder via `cd /; ls`.
* **Auth is opt-in.** If `CLERK_SECRET_KEY` is unset the backend serves
  open access (every request resolves to `user_id="dev"` — fine for the
  cutover smoke test, NOT fine for public traffic). Setting all three
  `CLERK_*` vars flips on the route guard. See "Clerk setup" below.
* **Storage is local disk on the VM.** No GCS hydrate/dehydrate
  (over-engineered for a single VM). Persistent disk on
  `digi-setu-live` already covers the durability story; we'll move
  to GCS only if we go multi-instance.

  **When we DO add GCS sync** (multi-VM / multi-region story), the
  always-excluded list lives in
  `web/backend/services/storage_exclusions.py`. Both the rsync sync
  job and the tar dehydration step must call `rsync_excludes()` /
  `tar_excludes()` from that module — never hardcode their own
  exclusion list.

  Most importantly: **`uploads/` is excluded by design**. User
  attachments are backed by the user's own device — if the workspace
  is restored from backup, the user re-uploads what they need. We do
  not eat the GCS storage bill for re-uploadable PDFs / PNGs /
  videos, and we don't risk leaking copies into long-term cold
  storage that's harder to GDPR-delete than the live disk.

  **Files that MUST be in every backup** (never add to the exclusion
  list):

  * `data/chats/`     — chat history JSONL (Pi reads this on respawn
                        to seed the new model with prior turns).
  * `data/registry.json` — workspace + session catalogue (titles,
                        pinned model, last-used timestamps).
  * `data/billing.db` — credit ledger SQLite. Holds the durable
                        `cost_events` table the Activity view reads
                        from + monthly spend totals + plan
                        assignments. Lose it and you lose the user's
                        spend tracking and audit trail across the
                        restart, even though Stripe keeps the source-
                        of-truth subscription state.
  * `data/users/`     — per-user preferences (current `permission_mode`).

## Threat model (until v1.1's runuser sandbox lands)

| Path on host                    | Mode  | Owner          | Who can read              |
|---------------------------------|------:|----------------|---------------------------|
| `/app` (in container)           | 0750  | root:app       | backend + AI subprocess   |
| `/opt/pi/stack.env`             | 0600  | root:root      | systemd only              |
| `/srv/pi/state/`                | 0700  | root:root      | systemd only (mounts in)  |
| `/srv/pi/data/workspaces/<id>/` | 0700  | 1100:1100      | backend + AI (via cwd)    |
| `/srv/pi/data/chats/<sid>/`     | 0700  | 1100:1100      | backend (history endpoint)|
| `/srv/pi/www`                   | 0755  | root:root      | caddy (RO)                |

**Known v1 holes (closed in v1.1 with runuser):**

* `bash` inside any workspace can `cat /srv/pi/data/registry.json`
  and learn other workspace IDs (it can't *visit* them — they're
  separate workspace cwds — but the metadata leaks). Phase 5 moves
  the registry into `/srv/pi/state` and stops bind-mounting it into
  workspaces.
* `bash` can spam `ls /` and see the OS layout (no information
  disclosure beyond "this is a Debian container").

### Defence-in-depth layers (live in v1)

The web-mode policy (`backend/services/policy.py`) blocks dangerous
shell commands at the application layer, the system prompt teaches
the agent to refuse infrastructure questions, and the secret
scrubber strips known token shapes from the outbound stream. None
of those is enough on its own — a determined attacker disables the
agent's cooperation. The host layer below is what actually keeps
the AI inside its lane:

1. **Block egress to the GCE metadata server from the workspace
   user.** The metadata server hands out the VM's IAM token to
   anything that can `curl http://169.254.169.254/`; if an AI ever
   reaches it the attacker owns the project. We block egress to
   that subnet for uid 1100 (the workspace user) using nftables:

   ```bash
   sudo apt-get install -y nftables
   sudo tee /etc/nftables.conf >/dev/null <<'EOF'
   table inet pi_egress {
       chain output {
           type filter hook output priority filter; policy accept;
           # Workspace uid 1100 (the AI's bash) can't reach
           # cloud-metadata or any link-local target.
           skuid 1100 ip daddr 169.254.0.0/16 drop
           skuid 1100 ip6 daddr fe80::/10     drop
       }
   }
   EOF
   sudo systemctl enable --now nftables
   ```

   The backend (uid `app`, ≠ 1100) keeps metadata access — that's
   how anthropic-vertex picks up Application Default Credentials.

2. **Filesystem permissions stop transitive `cat` of operator
   secrets.** The table above already shows mode 0700 / 0600 on
   `/srv/pi/state` and `/opt/pi/stack.env`. As long as the
   container doesn't run with `--privileged` and the bind-mounts
   honour those modes, an AI bash subprocess (uid 1100) cannot
   read them even with full shell access.

3. **No `apt`/`pip --user`/`npm install -g` from the workspace
   user.** The application-layer policy refuses these patterns;
   the OS layer enforces it because uid 1100 has no write access
   to system dirs (`/usr`, `/etc`) anyway. Workspace-local installs
   into the cwd are fine and don't escalate.

4. **No outbound port ≥ 1024 LISTEN from the workspace user.**
   Caddy + the backend already bind on the host (uid 0 / `app`);
   blocking new listeners from uid 1100 closes the netcat /
   reverse-shell exfiltration vector:

   ```nftables
   add rule inet pi_egress output skuid 1100 \
       tcp dport != { 80, 443, 22 } reject
   ```

   Add this if you observe any exfil attempts in `journalctl
   -u nftables`. We don't ship it on by default because it makes
   `pip install` / `npm install` (which talks to registries on
   443, fine) brittle in unusual setups.

The complete list of blocked bash patterns lives in
`backend/services/policy.py:_BASH_RULES`. The list of secret
shapes the outbound scrubber recognises is in
`backend/services/policy.py:_SECRET_PATTERNS`. Neither is "secret"
— attackers will probe both — they're documented so an operator
can tune false positives without reading source.

### Per-session safety limits

These three guards kick in *between* prompts to bound the blast
radius of a runaway turn:

| Guard               | Default | Env var                    | What it stops |
|---------------------|---------|----------------------------|---------------|
| Workspace disk cap  | 100 MB  | `WORKSPACE_DISK_QUOTA_MB`  | Agent fills the disk via `for i in {1..1e6}; do echo …`. The next prompt is rejected with a clear "delete files first" message. |
| Per-prompt timeout  | 15 min  | `PROMPT_TIMEOUT_SECONDS`   | Tool loop / hung bash command. The pi subprocess is killed and the user gets a "your prompt timed out" notice; tokens already consumed are still billed (this is how every LLM provider handles it). |
| Multi-tab guard     | always  | (none — code-level)        | Same chat opened in two tabs would race on the JSONL log. The older tab is closed with WS code 4409 and the SPA renders "Continued in another tab". |

The watchdog is implemented in `routes/chat_ws.py:prompt_watchdog`;
the disk cap in `services/disk_usage.py`; the multi-tab guard in
`services/session_locks.py`. None of these need external
infrastructure — they're per-process / per-VM and rebuild from
scratch on restart, which is fine because they're stateless safety
nets, not durable state.

**Known gap (deferred to v1.1): WS reconnect on network drop.**
Today, if a client's laptop sleeps mid-stream, the half-finished
response is lost. Token usage was already charged. There's no
resume protocol. Fix design: client buffers an `Idempotency-Id`
per prompt; on reconnect it sends `{type: "resume", req_id: …}`
and the server replays from the JSONL log starting at that id.
This is a half-day of work but needs a careful design pass on
"what counts as the same prompt" (re-paying for it would be
a bug). Tracked in TODO: `Phase-6/ws-resume`.

## Ordered runbook (when we're ready to deploy)

> Skip steps 0–2 if `digi-setu-live` already has docker + the
> typst-agent stack installed (it does, today) — pi.service is a
> drop-in alongside.

### 0. Provision the VM (idempotent, run once per fresh box)

```bash
gcloud compute scp -r deploy/ digi-setu-live:~/pi-deploy/ \
  --project digi-setu-dev --zone us-central1-a
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo bash ~/pi-deploy/scripts/provision-vm.sh'
```

This installs docker + compose, materialises `/srv/pi/{state,data,www}`
and `/srv/caddy`, and enables (but does not start) pi-prepare +
pi.service.

### 1. Populate `/opt/pi/stack.env`

```bash
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a
sudo cp /opt/pi/stack.env.example /opt/pi/stack.env  # or rsync deploy/stack.env
sudo chmod 0600 /opt/pi/stack.env
sudo nano /opt/pi/stack.env
```

Required (for a public deploy):

* `ACME_EMAIL`               — Let's Encrypt account
* `CLOUDFLARE_API_TOKEN`     — Cloudflare zone token (Edit zone DNS for
                               `digi-setu.com`)
* `GOOGLE_CLOUD_PROJECT`     — Vertex AI billing project (`digi-setu-dev`)
* `OAUTH_REDIRECT_BASE`      — `https://digi-setu.com`
* `CLERK_PUBLISHABLE_KEY`    — `pk_live_…` (frontend boot key)
* `CLERK_SECRET_KEY`         — `sk_live_…` (backend JWT verify)
* `CLERK_WEBHOOK_SECRET`     — `whsec_…` (signs the user.deleted webhook)

### 1a. Clerk setup (one-time, ≈ 5 min)

Clerk hosts the entire sign-in surface (Google SSO, magic links, MFA,
self-service profile + delete). The backend only verifies the JWT it
signs and reacts to the `user.deleted` webhook.

1. Create an app at <https://dashboard.clerk.com> → **Applications →
   Create application**. Pick **Email** + **Google** as sign-in methods.
2. Open **API Keys** and copy:
   * **Publishable key** → `CLERK_PUBLISHABLE_KEY` in `stack.env`
   * **Secret key**      → `CLERK_SECRET_KEY` in `stack.env`
3. Open **Webhooks → Add endpoint**:
   * URL    : `https://digi-setu.com/api/auth/webhook`
   * Events : check **`user.deleted`** (only one we react to today)
   * Copy the **Signing secret** → `CLERK_WEBHOOK_SECRET`
4. Open **Domains** and add `digi-setu.com` so cookies are issued for
   the production hostname.
5. (Optional but recommended) **JWT Templates → New template** named
   `default`, leave the claims as-is — Clerk's session token already
   includes `sub` (user id) which is all the backend cares about.

What lives where on the Clerk dashboard, mapped to user complaints:

| Original feedback                            | Clerk surface that fixes it          |
|----------------------------------------------|---------------------------------------|
| "How can I delete an account?"               | `<UserProfile />` → Security → Delete |
| "Profile picture doesn't open profile"       | `<UserButton />` (mounted in Picker)  |
| "Email deletion request not allowed in EU"   | Self-service in-app delete (no email)|

### 1c. Stripe billing (paid plans, optional but expected)

Stripe handles all paid subscriptions for v1. Deploy without it and
the SPA hides the Upgrade buttons; Free tier still works.

Currency limitation worth knowing up front: Stripe Subscriptions don't
deliver to India yet (Stripe's own docs flag it as "subscription
billing not available"). When the first non-US paying user asks, we'll
add Razorpay alongside or move everything to Paddle / Lemon Squeezy as
a Merchant of Record. v1 ships USD-only.

1. Create a Stripe account at <https://dashboard.stripe.com>; switch
   to **test mode** for staging, **live mode** for production.
2. **Developers → API keys**:
   * **Secret key** (`sk_live_…` / `sk_test_…`) → `STRIPE_SECRET_KEY`
3. **Products → Add product** — three monthly USD plans:

   | Plan label | Monthly price | Plan id env var       |
   |------------|--------------:|------------------------|
   | Starter    |        $20.00 | `STRIPE_PRICE_STARTER` |
   | Pro        |       $100.00 | `STRIPE_PRICE_PRO`     |
   | Max        |       $200.00 | `STRIPE_PRICE_MAX`     |

   Copy each resulting `price_…` id into `stack.env`. The plan
   *credits* (the dollar value of compute the user gets) live on the
   server side in `BILLING_*_CREDIT_USD`; price and credit don't
   have to match (we set them 1:1 to mirror Claude.ai's mental model).
4. **Developers → Webhooks → Add endpoint**:
   * URL    : `https://digi-setu.com/api/billing/webhook`
   * Events : tick `checkout.session.completed`,
     `customer.subscription.updated`, `customer.subscription.deleted`
   * Copy the **Signing secret** → `STRIPE_WEBHOOK_SECRET`
5. **Settings → Billing → Customer portal**: enable the portal and
   tick the plans you want users to be able to switch between. The
   "Manage subscription" button in the SPA opens this hosted portal.
6. (Optional) Set `BILLING_DEFAULT_PLAN=max` while developing so the
   "test mode" fallback gives every user every model — the production
   default is `free` so this never bleeds into the public site.

Smoke test after rolling:

```bash
# Status (public, no auth needed)
curl -s https://digi-setu.com/api/billing/status | jq '.enabled, .plans[].id'
# Should print  true  and  "free" "starter" "pro" "max"

# Trigger a checkout session via the SPA (signed in), expect a
# redirect to a Stripe-hosted checkout page. Pay with one of Stripe's
# test cards (4242 4242 4242 4242, any future date, any CVC) — the
# webhook will fire and CreditLedger.set_plan promotes the user.
```

### 1d. Verify the webhook is live

Once `stack.env` is populated and the stack is up, trigger a test
event from Clerk → **Webhooks → Send example** and tail the backend:

```bash
sudo journalctl -u pi.service -f | grep auth-webhook
```

A successful delivery prints `"ok": true, "ignored": "user.created"`
(harmless event we don't act on); a signature failure prints
`signature verify failed: …` — re-check `CLERK_WEBHOOK_SECRET`.

### 2. First build + roll (typst-agent still serves the public)

```bash
deploy/scripts/remote-deploy.sh stack       # push compose + caddy + systemd
deploy/scripts/remote-deploy.sh frontend    # build + push SPA
deploy/scripts/remote-deploy.sh backend     # Cloud Build + roll backend image
```

While DNS still points at typst-agent, hit pi.service directly with
`--resolve` to confirm health. Caddy isn't bound to :443 yet (typst-agent
holds it), so probe the backend port directly via SSH:

```bash
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'curl -fsS http://127.0.0.1:8788/healthz'
```

### 3. Cut over

```bash
deploy/scripts/remote-deploy.sh cutover
```

`cutover-from-typst-agent.sh` stops + disables `typst-agent.service`,
snapshots `/srv/typst-agent/users/` to `/srv/pi/legacy-backup/`, then
starts `pi.service`. DNS doesn't change.

### 4. Verify

```bash
curl https://digi-setu.com/healthz                # → {"status":"ok"}
deploy/scripts/remote-deploy.sh logs              # tail backend + caddy
```

Smoke a full chat from the SPA: visit https://digi-setu.com/, click
"+ New chat", ask the agent to compile a small Typst doc, verify
the PDF preview renders.

## Routine ops

```bash
# Iterate on backend code
deploy/scripts/remote-deploy.sh backend

# Iterate on the SPA only (no backend rebuild)
deploy/scripts/remote-deploy.sh frontend

# Tail logs
deploy/scripts/remote-deploy.sh logs

# Reload after editing /opt/pi/stack.env (rolls images, no downtime)
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo systemctl reload pi'

# Hard rebuild (e.g. after a Node version bump in Dockerfile.backend)
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command 'sudo systemctl restart pi'
```

## Rolling JWT signing keys

```bash
NEW=$(openssl rand -hex 64)
gcloud compute ssh digi-setu-live --project digi-setu-dev --zone us-central1-a \
  --command "sudo sed -i 's|^JWT_SECRET=.*|JWT_SECRET=${NEW}|' /opt/pi/stack.env && sudo systemctl reload pi"
```

All currently-issued tokens become invalid on reload. The SPA's auth
store auto-redirects to the login page on the first 401.

## Troubleshooting

* **Vertex returns 403** — the VM's compute service account isn't
  granted `roles/aiplatform.user` on `GOOGLE_CLOUD_PROJECT`. Fix:
  Console → IAM → grant the role to the *exact* SA attached to the
  `digi-setu-live` VM.

* **Caddy stuck on TLS issue** — `docker logs pi-caddy` will surface
  `acme_dns` errors. The Cloudflare token must have **Zone / DNS /
  Edit** scoped to the `digi-setu.com` zone. Cloudflare DNS records
  can stay proxied (orange cloud); DNS-01 doesn't care.

* **Stack won't restart after stack.env edit** —
  `journalctl -u pi.service` will surface the compose error. Most
  often a missing `=` or a stray quote in `stack.env`. systemd's
  EnvironmentFile parser is strict.

* **WebSocket 502s during a long agent turn** — Caddy is buffering
  somewhere. Check `(stream_proxy)` is being applied to `/ws/*` and
  that `flush_interval -1` + 24h timeouts are present.

* **Backend OOM-killed by the kernel** — pi keeps the entire chat
  history in memory. The default `digi-setu-live` size is fine for
  ≤100 concurrent chats; bump VM RAM before public launch.
