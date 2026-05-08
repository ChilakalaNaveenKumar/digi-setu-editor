  # HARDENING.md — operator checklist for digi-setu.com

  Last reviewed: 2026-05-07. Read top-to-bottom **once** the day you cut over,
  then re-run the audit on the first of every month.

  This file covers everything that lives **outside** the repo: Cloudflare DNS
  / WAF, Clerk's hosted dashboard, Stripe's dashboard, GCP IAM bindings, the
  VM's SSH config, and the GCS backup bucket. The repo-side hardening (env
  scrubbing, `cap_drop`, CSP, `nftables` egress firewall, `read_only: true`
  rootfs) is already wired into the deploy pipeline — see `DEPLOY.md` for
  what gets installed automatically.

  ---

  ## How to use this file

  Each section has a **"Why it matters"** sentence (so you know what blast
  radius the misconfig has) and a **checklist**. Tick a box in your head as
  you click through each dashboard. Anything you can't verify gets a
  Linear / GitHub issue, NOT a "I'll come back to it" — secrets accumulate
  because of "I'll come back to it".

  Three rules I learned the hard way:

  1. **Never paste a secret into chat / Notion / Linear / GitHub.** Use
     1Password (or your team's secret manager). The only place the
     production secrets live is `/opt/pi/stack.env` on the VM (mode 0600
     root) and your local `deploy/stack.env` (git-ignored).
  2. **Rotate on every offboarding.** When a team member leaves, the
     keys they touched (Clerk SK, Stripe SK, Cloudflare token, GCP key)
     all rotate that day — no exceptions, no "they were only an
     operator". Treat the day-1 cutover keys as expired the moment
     someone else touches them.
  3. **Least-privilege everywhere.** If a key/role/grant doesn't need
     a permission for the next 30 days, it shouldn't have it for the
     next 30 minutes either.

  ---

  ## 1. Cloudflare (DNS + edge)

  **Why it matters:** Cloudflare is our outermost shell. Every request to
  `digi-setu.com` hits Cloudflare before our VM. A misconfigured edge means
  every other layer below is irrelevant.

  ### 1a. SSL/TLS

  - [ ] **SSL/TLS → Overview → Mode:** `Full (strict)`.
        Anything less than `Full (strict)` allows MITM between Cloudflare
        and our VM (Caddy already issues a real Let's Encrypt cert via
        DNS-01, so `strict` works out of the box).
  - [ ] **SSL/TLS → Edge Certificates → Always Use HTTPS:** `On`.
  - [ ] **SSL/TLS → Edge Certificates → Min TLS Version:** `TLS 1.2` (raise
        to `TLS 1.3` once you've confirmed no legacy mobile clients hit you).
  - [ ] **SSL/TLS → Edge Certificates → Opportunistic Encryption:** `On`.
  - [ ] **SSL/TLS → Edge Certificates → Automatic HTTPS Rewrites:** `On`.
  - [ ] **SSL/TLS → Edge Certificates → HSTS:**
        - Enable: `On`
        - Max Age: `12 months`
        - Apply HSTS policy to subdomains: `On`
        - Preload: `On` (then submit at <https://hstspreload.org> after
          24h to lock you onto the Chromium preload list — irreversible
          for ~6 months, do this only after you're 100% sure HTTPS works
          on every subdomain).
  - [ ] **SSL/TLS → Edge Certificates → No-Browser Errors:** `On`.

  ### 1b. WAF + bot protection (free tier is enough for v1)

  - [ ] **Security → WAF → Managed Rules:** Cloudflare Managed Ruleset =
        `On` (action: Managed Challenge for high, Block for critical).
  - [ ] **Security → Bots → Bot Fight Mode:** `On`.
  - [ ] **Security → Settings → Security Level:** `Medium` is fine; bump
        to `High` if you start seeing curl-based scraping.
  - [ ] **Security → Settings → Browser Integrity Check:** `On`.
  - [ ] **Security → Settings → Challenge Passage:** `30 minutes`.

  ### 1c. Rate limiting (custom rules — free tier gives you 1)

  Use the one free rule for the most-abused endpoint:

  - [ ] **Security → WAF → Rate limiting rules → Create:**
        - Name: `pi-auth-burst`
        - If: `(http.request.uri.path contains "/api/auth")`
        - Then: `Block` for `60 seconds` if more than `30` requests in
          `10 seconds` per IP.
        - Why: Clerk JWT validation is the cheapest path to DOS us
          (every request hits it). Anything north of 3 req/s/IP is
          either retry-loop-bug or scrape.

  Premium tier? Add:

  - [ ] `pi-ws-flood`: `(http.request.uri.path contains "/ws/")` →
        `60 conn/min/IP` (block 5 min). Counters multi-tab abuse.
  - [ ] `pi-stripe-webhook-only-stripe`: `(http.request.uri.path eq
        "/api/billing/webhook")` → block any IP **not** on Stripe's
        webhook IP allow-list. Stripe publishes the list at
        <https://docs.stripe.com/ips>.

  ### 1d. Caching + page rules

  Caching anything our backend serves is a footgun (auth-protected
  responses cached on the edge would be served to the wrong user).

  - [ ] **Caching → Configuration → Caching Level:** `Standard`.
  - [ ] **Rules → Page Rules → Create:** URL pattern
        `https://digi-setu.com/api/*`, action: **Cache Level → Bypass**.
  - [ ] **Rules → Page Rules → Create:** URL pattern
        `https://digi-setu.com/ws/*`, action: **Cache Level → Bypass**
        (WebSocket upgrade headers).

  ### 1e. API tokens

  The repo uses **one** Cloudflare token: `CLOUDFLARE_API_TOKEN` in
  `stack.env`, scoped to `Edit zone DNS` for the `digi-setu.com` zone
  ONLY. Caddy uses it for the ACME DNS-01 challenge.

  - [ ] **My Profile → API Tokens:** confirm only ONE token has
        non-expired access to `digi-setu.com`. Rotate every 90 days.
  - [ ] Token TTL: set to 1 year max (Cloudflare allows infinite by
        default, override it).
  - [ ] After cutover: revoke any old `Global API Key` style token —
        those have full account access and can't be scoped.

  ---

  ## 2. Clerk (auth)

  **Why it matters:** Clerk is the only thing standing between an attacker
  and a valid user_id. A leaked Clerk SK lets someone forge a session for
  any user, run prompts on their dime, and read their workspace files
  through our API.

  ### 2a. Production instance setup

  - [ ] **Domains → Add custom domain:** `digi-setu.com` (NOT the
        accounts.dev placeholder). Verify the CNAME on Cloudflare.
  - [ ] **Customization → Account portal URL:** `https://accounts.digi-setu.com`
        (the CNAME Clerk gave you when you added the custom domain).
  - [ ] **Sessions → Multi-session handling:** `Single session` (one
        active session per user; enabling multi-session means a
        compromised stolen device keeps a session even after the user
        signs in elsewhere).
  - [ ] **Sessions → Session token lifetime:** `60 minutes`. Default
        7 days is too long for a paid product.
  - [ ] **Sessions → Inactivity timeout:** `30 minutes`.

  ### 2b. Bot / abuse protection

  - [ ] **Restrictions → Bot detection:** `On`.
  - [ ] **Restrictions → Block disposable email addresses:** `On`.
  - [ ] **Restrictions → Allowlist disposable email domains:** add ONLY
        domains you actually need to support. Default: empty.

  ### 2c. MFA + admin protection

  - [ ] **User & authentication → Multi-factor:** enable `Authenticator
        app (TOTP)` and `SMS code`. Enforce for **owner-tier** users
        (the operator).
  - [ ] **Application → Permissions → Roles:** confirm `admin` role
        exists and is assigned ONLY to the email(s) in your
        `ADMIN_EMAILS` env (the backend re-checks this — Clerk-side
        consistency just makes the dashboard match reality).

  ### 2d. Webhook signing

  - [ ] **Webhooks → Endpoints → digi-setu.com:** signing secret =
        the `CLERK_WEBHOOK_SECRET` value in `stack.env`. Confirm the
        endpoint URL is `https://digi-setu.com/api/auth/webhook`.
  - [ ] **Webhooks → Endpoints → Subscribed events:** ONLY the events
        the backend actually consumes. Today: `user.created`,
        `user.updated`, `user.deleted`, `session.created`,
        `session.ended`. Anything else is wasted attack surface.
  - [ ] **Webhooks → Filter by IP:** Clerk doesn't publish a stable IP
        allow-list, so SVIX signature verification is the only
        defense — don't disable it (the backend already enforces the
        signature in `routes/auth.py`, this is a config-drift check).

  ### 2e. API keys

  - [ ] Production keys (`pk_live_…`, `sk_live_…`) live ONLY in
        `/opt/pi/stack.env` on the VM and the operator's password
        manager. Never in:
        - `pi-typst-test/web/backend/.env` (laptop dev → use test keys
          there)
        - GitHub Actions logs / artifacts
        - Slack / chat
  - [ ] Rotate the SK every 90 days OR after any operator role change.
        Steps: Clerk dashboard → API Keys → Revoke old → Issue new →
        update `stack.env` → `bash scripts/remote-deploy.sh stack` →
        `bash scripts/remote-deploy.sh restart`.

  ---

  ## 3. Stripe (billing)

  **Why it matters:** A leaked Stripe SK lets an attacker grant any user
  unlimited credits, refund every paying customer, or worse — create
  arbitrary charges against attached customer cards.

  ### 3a. API keys — use Restricted, not Standard, in production

  Stripe's `sk_live_…` Standard key has every permission. The backend
  needs ONLY a tight subset (read customer, create checkout session,
  read webhook). Replace it:

  - [ ] **Developers → API Keys → Create restricted key:**
        - Name: `pi-typst-prod-backend`
        - Customers: `Read + Write`
        - Subscriptions: `Read + Write`
        - Checkout Sessions: `Read + Write`
        - Webhooks: `Read`
        - **All other resources: `None`** (default — leave as-is)
  - [ ] Replace `STRIPE_SECRET_KEY` in `stack.env` with the restricted
        `rk_live_…` key. Re-deploy.
  - [ ] Revoke the original Standard `sk_live_…`.

  ### 3b. Webhook signing + endpoint allow-list

  - [ ] **Developers → Webhooks → digi-setu.com:** signing secret =
        the `STRIPE_WEBHOOK_SECRET` in `stack.env`. URL =
        `https://digi-setu.com/api/billing/webhook`.
  - [ ] **Subscribed events:** ONLY what the backend handles —
        `checkout.session.completed`, `customer.subscription.created`,
        `customer.subscription.updated`, `customer.subscription.deleted`,
        `invoice.payment_succeeded`, `invoice.payment_failed`. Add
        nothing else.
  - [ ] If you have premium Cloudflare: filter `/api/billing/webhook`
        to Stripe's IP allow-list (<https://docs.stripe.com/ips>).
        Free tier: signature verification in `routes/billing.py` is
        the only defense, which is fine.

  ### 3c. Test vs. live separation

  - [ ] Confirm `STRIPE_PUBLISHABLE_KEY` in production starts with
        `pk_live_…` (not `pk_test_…`). Caught a deploy of a test key
        once — checkouts silently 200'd but never charged.
  - [ ] Confirm `STRIPE_PRICE_*` IDs in `stack.env` are LIVE-mode
        price IDs (Stripe dashboard, top-right toggle = `Live`). The
        UI is identical to test mode price IDs.

  ### 3d. Radar (fraud)

  - [ ] **Radar → Rules → All:** enable Stripe's default "Block if
        risk_score > 75" rule.
  - [ ] **Radar → Settings → 3D Secure:** `Recommended` or `Required`
        for non-US cards. Reduces chargebacks at the cost of a small
        conversion dip.

  ---

  ## 4. GCP IAM (least privilege)

  **Why it matters:** The VM's default compute SA is the most
  over-permissioned default in cloud security. By default it can read
  every GCS bucket in the project and use Vertex AI freely. We've
  scoped it down — but a future operator can break this with one
  click.

  ### 4a. The compute service account

  - [ ] **IAM & Admin → Service Accounts → digi-setu-live (compute SA):**
        - Project `frontend-472812` (Vertex billing project):
          - `roles/aiplatform.user` ONLY.
          - NOT `roles/owner`, NOT `roles/editor`, NOT
            `roles/iam.serviceAccountUser`.
        - Project `digi-setu-dev` (Artifact Registry project):
          - `roles/artifactregistry.reader` ONLY.
        - Project `digi-setu-dev` (GCS backup project, if same as AR):
          - `roles/storage.objectAdmin` on `gs://digi-setu-pi-backups`
            ONLY (NOT bucket-list permission, NOT project-wide).
  - [ ] **VM → Edit → Service Account:** confirm the VM is using the
        scoped SA above, NOT `compute@developer.gserviceaccount.com`.
  - [ ] **VM → Edit → API & Identity Management → Cloud API access
        scopes:** `Allow full access to all Cloud APIs` is the
        recommended default per Google docs (the SA's IAM bindings
        are what actually gate access). Don't mix scopes + IAM —
        scopes are legacy.

  ### 4b. Cloud Build SA

  Used only by `gcloud builds submit` from the operator laptop.

  - [ ] **IAM & Admin → Service Accounts → cloudbuild-sa:**
        - `roles/cloudbuild.builds.builder` (default)
        - `roles/artifactregistry.writer` on `digi-setu-dev` ONLY.
        - NOT `roles/aiplatform.*`, NOT `roles/storage.*`.

  ### 4c. Operator IAM hygiene

  - [ ] You (the operator email) should hold `roles/owner` on
        `digi-setu-dev` AND `frontend-472812` — that's expected.
  - [ ] No-one else should have a non-`viewer` role until you've
        formally onboarded them.
  - [ ] **Admin → Audit Logs:** confirm `Data Read`, `Data Write`,
        and `Admin Activity` are all enabled for `cloudresourcemanager`,
        `iam`, `aiplatform`, `storage`. Free, gives you a forensic
        trail if something goes sideways.

  ---

  ## 5. VM (digi-setu-live) — SSH + OS

  **Why it matters:** SSH to the VM = root on the VM = read every
  user's chat history + `billing.db` + `stack.env`. SSH lockdown is
  not optional.

  ### 5a. SSH

  - [ ] **VM → Edit → Metadata → enable-oslogin:** `TRUE`. OS Login
        means SSH access is gated by IAM (`roles/compute.osLogin` or
        `osAdminLogin`), not by metadata-stored SSH keys. Eliminates
        the "ex-employee's SSH key is still on the VM" footgun.
  - [ ] **VM → Edit → Metadata → block-project-ssh-keys:** `TRUE`.
        Prevents project-wide SSH keys from getting copied onto this
        VM by future operators.
  - [ ] On the VM, confirm `/etc/ssh/sshd_config`:
        - `PasswordAuthentication no`
        - `PermitRootLogin no` (OS Login enforces this anyway)
        - `ChallengeResponseAuthentication no`
        - `KbdInteractiveAuthentication no`
        - `MaxAuthTries 3`
        - `LoginGraceTime 30`
        - `ClientAliveInterval 300`
        - `ClientAliveCountMax 2`
        - `Protocol 2`
  - [ ] After any sshd_config change: `sudo systemctl reload ssh`.

  ### 5b. Firewall (gcloud-managed, supplements `nftables`)

  The repo's `pi-firewall.service` blocks AWS/ECS metadata
  (169.254.170.2) and IPv6 link-local (fe80::/10) for uid **1000**
  (the AI's sandbox uid in v1.1). The backend (uid 1100) keeps
  unrestricted egress.

  **NOTE on GCE metadata (169.254.169.254):** intentionally NOT
  blocked. The dual-uid sandbox runs the legitimate `pi` process AND
  the AI's bash subprocess as the SAME uid (1000), so a kernel-uid
  firewall cannot tell them apart. Blocking the GCE metadata server
  for uid 1000 also blocks pi's own ADC token fetch, which broke
  every `--provider anthropic-vertex` / `--provider google-vertex`
  chat in production with "No API key found" at startup.

  The trust boundary for the metadata token has therefore moved from
  "kernel firewall" to **"GCP IAM scope on the VM service account"**
  (§6 below). As long as the SA only has `roles/aiplatform.user`
  (and NOT `roles/iam.serviceAccountTokenCreator`,
  `roles/storage.admin`, `roles/owner`, etc.), a stolen token can at
  most spend Vertex / Anthropic quota in our project — same blast
  radius as a paid pi prompt would already have. **Audit the SA's
  bindings every month** (§6, command at the bottom of §7) — that is
  now the single most important defence against AI-token theft.

  Inbound is gated by GCP firewall rules:

  - [ ] **VPC Network → Firewall:** confirm rules:
        - `allow-https` (0.0.0.0/0 → tcp:443) — public traffic to Caddy.
        - `allow-http` (0.0.0.0/0 → tcp:80) — Let's Encrypt HTTP-01
          fallback only; ACME is configured for DNS-01 so this is rarely
          used. Consider removing.
        - `allow-ssh-iap` (35.235.240.0/20 → tcp:22) — SSH ONLY through
          GCP IAP. NO `0.0.0.0/0` SSH rule. If you need to debug from a
          non-IAP machine, use `gcloud compute ssh` (which transparently
          tunnels through IAP).
  - [ ] No other inbound rules. In particular: **no `0.0.0.0/0 → tcp:8788`**
        (the backend port — Caddy reverse-proxies it from inside the VM,
        public traffic should never reach it directly).

  ### 5c. OS hardening

  - [ ] `unattended-upgrades` installed and configured for security
        patches (the deploy script doesn't install this — add it once
        manually):
        ```bash
        sudo apt-get install -y unattended-upgrades
        sudo dpkg-reconfigure --priority=low unattended-upgrades
        ```
  - [ ] `fail2ban` for the host (defense-in-depth for SSH; OS Login
        already gates auth, but fail2ban catches the few SSH probes
        that reach the VM):
        ```bash
        sudo apt-get install -y fail2ban
        sudo systemctl enable --now fail2ban
        ```

  ---

  ## 6. GCS backup bucket

  **Why it matters:** The bucket holds nightly snapshots of every
  user's chat history, `billing.db`, and `registry.json`. A misconfigured
  bucket leaks every conversation in plaintext.

  - [ ] `gs://digi-setu-pi-backups` is in a multi-region (default `US`
        for cheaper egress to laptop restore, `nam4` for US + EU
        redundancy). Confirm in `gsutil ls -L -b gs://digi-setu-pi-backups`.
  - [ ] **Bucket settings → Permissions:** `Uniform bucket-level access`
        = `On`. ACL-based access is a footgun.
  - [ ] **Bucket settings → Public access:** `Subject to object ACLs` is
        FORBIDDEN — must be `Not public` (uniform access already enforces
        this; the dashboard checkbox is a sanity belt).
  - [ ] **Permissions → IAM:** ONLY two principals:
        - The compute SA: `roles/storage.objectAdmin` (the backup
          script needs write).
        - You (operator email): `roles/storage.admin` for
          troubleshooting.
        - NOT `allUsers`, NOT `allAuthenticatedUsers`, NOT any group
          you don't recognize.
  - [ ] **Lifecycle:** rule = "delete after 90 days". Verify with
        `gsutil lifecycle get gs://digi-setu-pi-backups` — keeps storage
        costs flat and limits the blast radius of a bucket leak to 90 days.
  - [ ] **Object versioning:** `Off`. We back up daily snapshots; we
        don't need version history of those snapshots.
  - [ ] **Encryption:** Google-managed default key is fine for v1.
        Phase 5: customer-managed key (CMEK) for compliance / right-to-
        be-forgotten implementation.

  ---

  ## 7. Domain registrar (the registrar that owns digi-setu.com)

  **Why it matters:** A compromised registrar account = attacker can
  point `digi-setu.com` at any IP they want and trick browsers into
  trusting their cert (DNS-01 ACME makes this trivial). This is the
  account most operators forget to harden because it's set-and-forget.

  - [ ] **Registrar account → 2FA:** `On`. Use a hardware key
        (YubiKey) if the registrar supports it.
  - [ ] **Registrar → Domain → Lock:** `On` (sometimes called
        "Registrar Lock" or "Transfer Lock"). Prevents the domain
        from being transferred to another registrar without a manual
        unlock.
  - [ ] **Registrar → Domain → Auto-renew:** `On`. Domain expiry =
        outage + reputation hit.
  - [ ] **Registrar → DNSSEC:** `On` if Cloudflare and your registrar
        both support it (Cloudflare → DNS → Settings → DNSSEC →
        Enable, then paste the DS record into the registrar). Belt-
        and-suspenders against DNS spoofing.

  ---

  ## 8. Repo hygiene (operator laptop)

  **Why it matters:** The local repo has `deploy/stack.env` with
  every production secret. One `git add stack.env && git push` makes
  every secret public.

  - [ ] `deploy/stack.env` is git-ignored (verify:
        `git check-ignore deploy/stack.env` returns 0).
  - [ ] `web/backend/.env*` are git-ignored.
  - [ ] Pre-commit hook: install `git-secrets`
        (<https://github.com/awslabs/git-secrets>) and add patterns
        for `sk_live_`, `pk_live_`, `whsec_`, `cfut_`,
        `AIza[A-Za-z0-9]{35}`, `eyJ[A-Za-z0-9_-]{20,}`.
        ```bash
        brew install git-secrets
        git secrets --install
        git secrets --register-aws
        git secrets --add 'sk_live_[A-Za-z0-9]+'
        git secrets --add 'whsec_[A-Za-z0-9]+'
        git secrets --add 'cfut_[A-Za-z0-9]+'
        ```
  - [ ] Operator laptop has FileVault (macOS) / LUKS (Linux) full-disk
        encryption ON. A stolen laptop with `stack.env` on it is the
        same as a leaked secret repo.

  ---

  ## 9. Verification — the audit run

  Once a month, walk through this script (~5 min):

  ```bash
  # 1. Cloudflare HSTS+TLS
  curl -sI https://digi-setu.com | grep -iE 'strict-transport|content-security|x-frame|permissions-policy'
  # Expect: HSTS with preload, CSP with default-src 'self', X-Frame-Options DENY,
  # Permissions-Policy with deny-by-default list.

  # 2. SSL Labs grade (one-shot, takes ~90 sec)
  echo 'Browse to https://www.ssllabs.com/ssltest/analyze.html?d=digi-setu.com'
  # Expect: A or A+

  # 3. Mozilla Observatory grade
  echo 'Browse to https://observatory.mozilla.org/analyze/digi-setu.com'
  # Expect: A or B with a clear path to A.

  # 4. SSH lockdown
  ssh-audit digi-setu-live  # https://github.com/jtesta/ssh-audit
  # Expect: A grade, no CBC ciphers, no sha1 MACs.

  # 5. GCP IAM drift (compare against the section 4 list)
  gcloud projects get-iam-policy frontend-472812 --format=json \
      | jq '.bindings[] | select(.members[] | contains("digi-setu-live"))'
  gcloud projects get-iam-policy digi-setu-dev --format=json \
      | jq '.bindings[] | select(.members[] | contains("digi-setu-live"))'
  # Expect: aiplatform.user on frontend-472812, artifactregistry.reader on digi-setu-dev.

  # 6. GCS bucket public exposure
  gsutil iam get gs://digi-setu-pi-backups | jq '.bindings'
  # Expect: NO allUsers, NO allAuthenticatedUsers.

  # 7. nftables egress firewall (on the VM)
  ssh digi-setu-live 'sudo nft list table inet pi_egress'
  # Expect: 2 drop rules
  #   - skuid 1000 → 169.254.170.2 (AWS metadata, unused but blocked)
  #   - skuid 1000 → fe80::/10 (IPv6 link-local)
  # GCE metadata (169.254.169.254) is INTENTIONALLY allowed for uid 1000
  # so pi's own ADC token fetch works — see §5b for the rationale and
  # the IAM-scope mitigation that replaces this firewall layer.

  # 8. Container hardening (on the VM)
  ssh digi-setu-live 'docker inspect pi-backend' | \
      jq '.[0].HostConfig | {CapDrop, SecurityOpt, ReadonlyRootfs, PidsLimit, Memory}'
  # Expect: CapDrop=["ALL"], SecurityOpt=["no-new-privileges:true"],
  #         ReadonlyRootfs=true, PidsLimit=1024, Memory=4294967296.

  # 9. Pi env scrub (on the VM)
  ssh digi-setu-live 'docker exec pi-backend bash -c "ps -o cmd= -C pi | head -1"'
  # Expect: a `pi --mode rpc ...` line, not relevant by itself
  ssh digi-setu-live 'docker exec -u 1100 pi-backend bash -c "cd /tmp && env | grep -iE \"clerk|stripe|cloudflare|jwt|admin\""'
  # Expect: NO output. (If anything matches, the env scrubber regressed —
  # see web/backend/services/pi_session.py _PI_ENV_DENY.)

  # 10. Webhook signature verification on a test event
  curl -X POST https://digi-setu.com/api/billing/webhook \
       -H 'Content-Type: application/json' \
       -d '{"type":"customer.subscription.updated","data":{"object":{}}}' \
       -i 2>&1 | head -1
  # Expect: HTTP/1.1 400 Bad Request (signature missing).
  ```

  ---

  ## 10. Incident response (if a secret leaks)

  Speed matters more than process. The order:

  1. **Revoke first, investigate second.** Always.
  2. Stripe SK leaked → Stripe dashboard → Developers → API Keys → roll.
     Then: rotate the webhook secret too (you don't know if the
     attacker captured it from the same source).
  3. Clerk SK leaked → Clerk dashboard → API Keys → Revoke + Issue. Then:
     **invalidate every active session** (Sessions → Sign out all users).
  4. Cloudflare token leaked → Cloudflare → My Profile → API Tokens →
     Roll. Caddy auto-renewal will pick up the new value on next
     `bash scripts/remote-deploy.sh stack`.
  5. GCP SA key leaked (we don't use SA keys, only ADC — but if you
     ever DO create a key) → IAM → Service Accounts → Keys → Delete.
  6. Update `deploy/stack.env`, re-deploy via
     `bash scripts/remote-deploy.sh stack && bash scripts/remote-deploy.sh restart`.
  7. ONLY THEN: pull the audit logs and figure out what was hit between
     the leak time and the rotation time. Cloud Logging on GCP, Stripe
     events, Clerk audit log.
  8. If you find evidence of unauthorized access: notify affected users
     within 72 hours per GDPR / standard practice. Email template in
     `deploy/INCIDENT_RESPONSE.md` (Phase 5 deliverable).

  ---

  ## What's still in the "Phase 5" bucket

  These live as TODOs in `DEPLOY.md` but aren't operator dashboard
  toggles — they need code changes:

  1. ~~**`runuser` sandbox** so the AI's bash doesn't share uid 1100
     with the backend.~~ **Closed in v1.1** via `setpriv --reuid 1000
     --regid 1000 --clear-groups --no-new-privs` in
     `services/pi_session.py`. The AI's bash now runs as uid 1000;
     `billing.db`, `registry.json`, `users/`, and other workspaces
     return EACCES. See section 11 below for the full kernel-level
     isolation model.
  2. **CMEK on the GCS backup bucket** for right-to-be-forgotten /
     SOC2 readiness.
  3. **Per-tenant database isolation** so a single sandbox uid can't
     `cd /srv/pi/data/workspaces/<known-uuid>` to read another
     tenant's data. Today this is mitigated by uuid4 entropy (122
     bits — infeasible to brute-force) and `0710` mode on the
     parent dir (no `ls`), but a per-tenant uid would close it
     completely.
  4. **Subresource Integrity (SRI)** hashes on bundled JS (Vite
     supports this via a plugin; we just haven't wired it).
  5. **`script-src 'strict-dynamic'`** with hash-based allow-list so
     we drop `'unsafe-inline'` from style-src.

  None of these block v1.1. All of them block "open up the public
  funnel beyond the closed beta".

  ---

  ## 11. Dual-uid sandbox (v1.1) — what it does and how to verify

  **Why it matters:** This is the layer that stops a hostile prompt
  from `cat`ting another user's chat history, billing records, or
  the operator's API keys. Up to v1.0 the AI's bash ran as the same
  uid as the backend (1100) — every file the backend could read,
  the AI could read. v1.1 splits that into two uids; the file-mode
  bits do the rest.

  ### 11a. The model

  Two uids inside the backend container:

  | uid | gid | user      | role                                        |
  |-----|-----|-----------|---------------------------------------------|
  | 1100 | 1100 | `app`    | FastAPI backend. Member of group `sandbox`. |
  | 1000 | 1000 | `sandbox`| pi --mode rpc + AI's bash subprocess.       |

  Permission table on `/srv/pi/data/`:

  | Path                      | Mode | Owner    | Sandbox can…                |
  |---------------------------|------|----------|-----------------------------|
  | `data/`                   | 0710 | 1100:1000 | traverse only (no `ls`)    |
  | `billing.db`              | 0600 | 1100:1100 | NOTHING                    |
  | `registry.json`           | 0600 | 1100:1100 | NOTHING                    |
  | `users/`                  | 0700 | 1100:1100 | NOTHING                    |
  | `workspaces/`             | 0710 | 1100:1000 | cd-by-uuid only            |
  | `workspaces/<wsid>/`      | 2770 | 1000:1000 | rwx (own this)             |
  | `chats/<sid>/`            | 2770 | 1000:1000 | rwx (own this)             |
  | `shadows/<wsid>/`         | 2770 | 1000:1000 | rwx (own this)             |
  | `typst-packages/`         | 2775 | 1000:1000 | rwx (shared cache)         |

  The 0710 trick: group `--x` lets the sandbox `cd` into a child by
  name (if it knows the name) but not `ls` the parent. Combined with
  uuid4 wsids (122 bits of entropy from `secrets.token_urlsafe(8)`),
  enumerating other users' workspaces is computationally infeasible.

  ### 11b. The wiring

  - `Dockerfile.backend` creates user `sandbox` (uid 1000) and adds
    `app` to group 1000 as a SECONDARY group.
  - `deploy/systemd/pi-prepare.service` enforces the permission
    table at boot (idempotent — re-running on already-correct dirs
    is a no-op).
  - `deploy/docker-compose.yml` adds `CAP_CHOWN`, `CAP_FOWNER`,
    `CAP_SETUID`, `CAP_SETGID` back to the backend's `cap_drop: ALL`
    base so it can chown new dirs and run setpriv.
  - `services/sandbox_layout.py` is the single source of truth for
    `stamp_sandbox_dir()` / `stamp_sandbox_tree()`.
  - `services/pi_session.py` wraps the pi exec in
    `/usr/bin/setpriv --reuid 1000 --regid 1000 --clear-groups
    --no-new-privs pi --mode rpc …`.
  - `deploy/nftables/pi-egress.nft` blocks `skuid 1000` from AWS
    ECS metadata (169.254.170.2) and IPv6 link-local (fe80::/10).
    GCE metadata (169.254.169.254) is intentionally ALLOWED for
    uid 1000 — see §5b for why (pi needs its own ADC) and the
    IAM-scope mitigation. The backend (uid 1100) has unrestricted
    egress so its Vertex SDK can
    still fetch ADC tokens.

  ### 11c. Verification — run on the VM after deploy

  ```bash
  # 1. The pi subprocess is running as uid 1000 (not 1100)
  ssh digi-setu-live 'docker exec pi-backend sh -c "ps -eo uid,pid,cmd | grep -E \"(pi --mode|bash)\""'
  # Expect lines like:  1000  1234 node /usr/local/bin/pi --mode rpc …
  #                     1000  1235 bash -c …

  # 2. The sandbox uid CANNOT read backend-only files
  ssh digi-setu-live 'docker exec --user 1000:1000 pi-backend cat /srv/pi/data/billing.db'
  # Expect: cat: /srv/pi/data/billing.db: Permission denied
  ssh digi-setu-live 'docker exec --user 1000:1000 pi-backend cat /srv/pi/data/registry.json'
  # Expect: cat: /srv/pi/data/registry.json: Permission denied
  ssh digi-setu-live 'docker exec --user 1000:1000 pi-backend ls /srv/pi/data/users'
  # Expect: ls: cannot access '/srv/pi/data/users': Permission denied

  # 3. The sandbox CAN'T enumerate other workspaces (no listing)
  ssh digi-setu-live 'docker exec --user 1000:1000 pi-backend ls /srv/pi/data/workspaces'
  # Expect: ls: cannot open directory '/srv/pi/data/workspaces': Permission denied

  # 4. The sandbox CAN reach its own workspace (cd by uuid)
  WS=$(ssh digi-setu-live 'docker exec pi-backend ls /srv/pi/data/workspaces | head -1')
  ssh digi-setu-live "docker exec --user 1000:1000 pi-backend ls /srv/pi/data/workspaces/${WS}"
  # Expect: a normal listing of `workspace/`, the symlinks, etc.

  # 5. The metadata server is reachable for BOTH uid 1000 AND uid 1100.
  #    (uid 1000 is allowed by design — see §5b for why. The token
  #    blast radius is now controlled by the SA's IAM scope, not by
  #    the firewall.)
  ssh digi-setu-live 'docker exec --user 1000:1000 pi-backend curl -sS --max-time 2 -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/scopes'
  # Expect: a 200 OK listing the SA's scopes (Vertex + read storage).
  ssh digi-setu-live 'docker exec --user 1100:1100 pi-backend curl -sS --max-time 2 -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/scopes'
  # Expect: a 200 OK with the same scopes. (Backend Vertex auth works.)
  # AWS metadata (169.254.170.2) and IPv6 link-local (fe80::/10) ARE
  # still blocked for uid 1000; verify with:
  ssh digi-setu-live 'docker exec --user 1000:1000 pi-backend curl -sS --max-time 2 http://169.254.170.2/'
  # Expect: a curl: (28) Connection timed out — NOT a 200.

  # 6. setpriv is the binary we expect (not a forgotten symlink)
  ssh digi-setu-live 'docker exec pi-backend stat -c "%U:%G %a %n" /usr/bin/setpriv'
  # Expect: root:root 755 /usr/bin/setpriv

  # 7. The container actually has the caps we added
  ssh digi-setu-live 'docker inspect pi-backend' | jq '.[0].HostConfig | {CapDrop, CapAdd}'
  # Expect: CapDrop=["ALL"], CapAdd=["CHOWN","FOWNER","SETUID","SETGID"]
  ```

  ### 11d. The remaining gap

  The sandbox COULD `cd /srv/pi/data/workspaces/<other-uuid>/` if
  it knew the exact uuid. wsids are uuid4 from
  `secrets.token_urlsafe(8)` (122 bits), so brute-forcing is
  computationally infeasible — that's our defence today. A
  fully-isolated model would assign a unique sandbox uid PER
  WORKSPACE, but that requires either dynamic Linux user creation
  (operationally messy at scale) or a runuser-style namespace
  per chat session (engineering cost: ~1 week). Not blocking the
  closed beta; tracked as a Phase-5+ deliverable.

  > **2026-05-08 update — superseded by §12.** The "Phase-5+" item
  > above is now §12 below: per-session Docker containers replace
  > the dual-uid sandbox. Section 11 is kept as historical reference
  > for the registry/file-tree code path (which still runs uid 1100
  > on the backend); the AI's bash no longer runs as uid 1000 in
  > the backend container — it runs in its own ephemeral
  > `pi-session` container.

  ---

  ## 12. Per-session Docker container sandbox (Phase 6 architecture)

  **Why it matters:** This is the trust boundary between the user's
  AI-driven shell and everything else (the backend, other users'
  workspaces, the host filesystem, the public internet). It replaces
  the dual-uid model in §11 with **one ephemeral Docker container
  per chat session**, giving each user kernel-namespace isolation
  AND root-inside-container freedom (sudo apt install, install rust,
  etc.) without compromising cross-tenant or host security.

  ### 12a. Architecture at a glance

  ```text
   ┌─ host (GCP VM) ────────────────────────────────────────────────────────┐
   │                                                                        │
   │  pi-backend (host network mode)         pi-egress docker network       │
   │  uid 1100 / 1000 dual-uid               172.30.16.0/20                 │
   │                                                                        │
   │  ┌──────────────────────────┐           ┌─────────────────┐            │
   │  │ FastAPI                  │◄─stdio────┤ pi-sess-<sid-A> │ user A     │
   │  │  + egress proxy thread   │           │ uid 1000 inside │            │
   │  │    listening on          │           │ /workspace bind │            │
   │  │    172.30.16.1:1080      │◄──HTTPS───┤ HTTPS_PROXY=    │            │
   │  │  + container_pool        │           │   172.30.16.1   │            │
   │  └─────────┬────────────────┘           └─────────────────┘            │
   │            │                                                           │
   │            │ docker.sock                ┌─────────────────┐            │
   │            ├────────────────────────────┤ pi-sess-<sid-B> │ user B     │
   │            │                            └─────────────────┘            │
   │            │                                                           │
   │            ▼                                                           │
   │  /srv/pi/state (CA + secrets)                                          │
   │  /srv/pi/data  (workspaces, chats, registry)                           │
   │                                                                        │
   │  nftables rules (deploy/nftables/pi-egress.nft):                       │
   │    src=172.30.16.0/20 → dst=172.30.16.1:1080  ALLOW                    │
   │    src=172.30.16.0/20 → anywhere else         DROP (incl. 169.254.x)   │
   └────────────────────────────────────────────────────────────────────────┘
  ```

  ### 12b. The boundaries (what each layer enforces)

  | Layer | Enforces | Bypass cost |
  |-------|----------|-------------|
  | Kernel namespaces (per-container netns/mountns/pidns) | "Container A cannot see container B's files / processes / network" | A kernel CVE in namespace setup. Patch promptly. |
  | nftables host firewall (`pi-egress.nft`) | "Container subnet 172.30.16.0/20 can ONLY talk to the proxy at 172.30.16.1:1080" | Root on the VM. |
  | Egress proxy hostname allow-list | "Outbound HTTPS only to ~30 curated hostnames" | Root in the proxy = backend RCE. |
  | MITM CA (signs leaf certs for `*.aiplatform.googleapis.com`) | "Vertex auth header is injected by proxy, not the AI" | Container can't see CA private key (only public cert is bind-mounted ro). |
  | Per-session container `cap_drop ALL` + small cap_add | "AI can sudo inside container, can't escape" | Kernel CVE in the cap_add set we kept (CHOWN/FOWNER/SETUID/SETGID/DAC_OVERRIDE/NET_BIND_SERVICE). |
  | Bash policy (`services/policy.py`) | "Refuse cryptominer / metadata-IP curl / docker.sock probe attempts at the bash layer for clearer error messages" | Trivial — this is advisory, not the trust boundary. |

  Any one of the layers being defeated is contained by the others.
  The matrix is intentional defense-in-depth.

  ### 12c. Wiring (files that have to stay in sync)

  | File | Role |
  |------|------|
  | `deploy/Dockerfile.session` | Per-session image: Debian + node + typst + sudo NOPASSWD for sandbox uid 1000 |
  | `deploy/entrypoint-session.sh` | tini → install MITM CA → `setpriv --reuid 1000` → `pi --mode rpc` |
  | `web/backend/services/pi_session.py` | Spawns `docker run -i --rm … pi-session …` per chat |
  | `web/backend/services/egress_proxy.py` | HTTP CONNECT proxy + Vertex MITM auth injector |
  | `web/backend/services/container_pool.py` | Quotas + orphan cleanup |
  | `deploy/nftables/pi-egress.nft` | Force traffic from 172.30.16.0/20 through proxy only |
  | `deploy/systemd/pi-egress-network.service` | Creates the `pi-egress` docker bridge (172.30.16.0/20) at boot |
  | `deploy/docker-compose.yml` | Backend gets `/var/run/docker.sock` + `/srv/pi/state` rw |

  Every one of these files has a header comment documenting why it
  exists and what its peers are. When you change subnet / gateway /
  port settings, change ALL of them in lockstep.

  ### 12d. Vertex auth — the MITM CA

  The backend's egress proxy generates a CA cert at first boot and
  stores it under `/srv/pi/state/`:

  ```
  /srv/pi/state/proxy/mitm-ca.crt   0644 1100 ←─ public, bind-mounted ro into containers
  /srv/pi/state/proxy/mitm-ca.key   0600 1100 ←─ private, NEVER leaves the host
  /srv/pi/state/proxy/leaf-certs/   0700 1100 ←─ per-host signed leaf certs (cache)
  ```

  Every per-session container bind-mounts `mitm-ca.crt` (read-only)
  at `/etc/pi/mitm-ca.crt` and the entrypoint installs it into the
  container's trust store + sets `NODE_EXTRA_CA_CERTS` /
  `CURL_CA_BUNDLE` / `SSL_CERT_FILE`.

  When pi-ai (Node) makes an HTTPS request to
  `*.aiplatform.googleapis.com`, the chain is:

  ```
  pi-ai fetch → HTTPS_PROXY=http://172.30.16.1:1080
            → CONNECT us-central1-aiplatform.googleapis.com:443
            → proxy returns 200 OK, presents leaf cert signed by
              backend CA (Node trusts because NODE_EXTRA_CA_CERTS)
            → proxy reads request, drops any client-supplied
              Authorization, injects Bearer <ADC token from
              backend google-auth>, adds X-Goog-User-Project
            → proxy opens REAL TLS to upstream, forwards modified
              request, reads response, forwards back through the
              client-side TLS tunnel
  ```

  Result: container has zero credentials, proxy holds them all.
  An RCE on the container can scrape its env / disk / processes
  forever and find nothing.

  ### 12e. CA rotation procedure

  Run on the VM whenever a backend code change touches the proxy
  module, or every 90 days, whichever is sooner:

  ```bash
  ssh digi-setu-live '
    sudo systemctl stop pi.service
    sudo rm -rf /srv/pi/state/proxy
    sudo systemctl start pi-prepare.service  # recreates the dir
    sudo systemctl start pi.service          # proxy regenerates on first request
  '
  ```

  Live chats during rotation get one TLS handshake error and the
  AI's SDK retries (Anthropic SDK's default). UX impact: <1s
  hiccup, no user action needed.

  ### 12f. Verification

  ```bash
  # 1. The egress proxy is listening
  ssh digi-setu-live 'sudo ss -lnt sport = :1080'
  # Expect: LISTEN  0  64  172.30.16.1:1080

  # 2. CA cert is present and has correct perms
  ssh digi-setu-live 'sudo ls -la /srv/pi/state/proxy/'
  # Expect: mitm-ca.crt: -rw-r--r--  app   (uid 1100)
  #         mitm-ca.key: -rw-------  app   (uid 1100)
  #         leaf-certs/  drwx------ app    (uid 1100)

  # 3. Container subnet cannot reach metadata server
  ssh digi-setu-live 'sudo docker run --rm --network pi-egress \
                          alpine sh -c "wget -qO- --timeout=2 \
                          http://169.254.169.254/ && echo LEAKED"'
  # Expect: nothing (timeout) — NOT "LEAKED"

  # 4. Container subnet CAN reach the proxy
  ssh digi-setu-live 'sudo docker run --rm --network pi-egress \
                          pi-session:latest \
                          sh -c "curl -m 3 -sS -x http://172.30.16.1:1080 \
                          https://api.github.com >/dev/null && echo OK"'
  # Expect: OK

  # 5. Off-allow-list host returns 451 from proxy
  ssh digi-setu-live 'sudo docker run --rm --network pi-egress \
                          pi-session:latest \
                          sh -c "curl -m 3 -sS -o /dev/null -w \"%{http_code}\" \
                                 -x http://172.30.16.1:1080 \
                                 -X CONNECT https://evil.example.com:443"'
  # Expect: 451

  # 6. No container labelled pi.app=pi-typst-test is orphaned
  ssh digi-setu-live 'sudo docker ps -a --filter label=pi.app=pi-typst-test --format "{{.Names}}: {{.Status}}"'
  # Expect: only currently-active chats (up <N>m) — no Exited containers

  # 7. Run the smoke test
  ./deploy/scripts/smoke-session.sh
  # Expect: PASS: 8  FAIL: 0  SKIP: 0
  ```

  ### 12g. Trade-offs you signed up for

  - **`/var/run/docker.sock` mounted in backend.** The backend has
    docker root via the socket. A backend RCE is now full host root
    via `docker run --privileged --pid=host --net=host -v /:/host`.
    Mitigation: backend cap_drop ALL except CHOWN/FOWNER/SETUID/
    SETGID + read_only rootfs + Clerk auth required for all routes.
    Do NOT add new dev tools to the backend image without signing
    off on this trade.

  - **CA private key on the backend.** A backend RCE leaks the CA
    private key, which is trusted by every container running our
    image. Attacker could MITM Vertex calls from any of OUR
    deployments running our image. They could not MITM Vertex calls
    on someone else's deployment (different CA), nor any third-party
    Vertex client. Rotate per §12e on every backend code change to
    keep the leak window small.

  - **Per-session container has root inside.** This is a feature,
    not a bug. The container is namespaced from the host kernel
    (root in container ≠ root on host). The user explicitly wanted
    this so the AI can `apt install` whatever the user asks for.
    Belt-and-suspenders: `cap_drop ALL` reduces what container-root
    can actually do (no CAP_SYS_ADMIN, no CAP_NET_ADMIN, no
    CAP_SYS_PTRACE, no CAP_NET_RAW), and the container has a 1 GiB
    memory cap, 512-PID limit, and 1-CPU quota so a runaway can't
    starve the host.

  - **Egress allow-list is curated by hostname.** It can't catch a
    malicious package hosted on github.com or an exfil endpoint
    proxied through gist.github.com. We accept this — the threat
    model assumes a benign user with a possibly-confused AI, not a
    user who has been promp-injected into running specific exfil
    code. Enterprise-tier hardening can add per-user payload
    inspection (Suricata sniffing the proxy's upstream connection)
    later.
