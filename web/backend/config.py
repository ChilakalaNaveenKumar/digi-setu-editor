"""
Backend-wide configuration constants resolved from env / on-disk paths.

Anything that needs to know "what mode are we in" or "where does data live"
imports from here so we have one switch to flip between local dev, Cloud
Run, and the Tauri sidecar.

Environment knobs (all optional):

    PI_MODE              "web" (default) or "desktop"
    PI_DATA_ROOT         override for the on-disk data dir. In the VM
                         deploy this is /srv/pi/data (bind-mounted by
                         docker-compose); in dev it stays under web/data/.
    PI_CORS_EXTRA_ORIGINS comma-separated origins to allow CORS from in
                         addition to localhost (e.g. https://digi-setu.com)
    PORT / HOST          uvicorn bind address (the production Dockerfile
                         pins them; main.py honours both for local dev).

    CLERK_SECRET_KEY     Clerk backend API key. When SET, every request
                         (except health/config/auth-webhook/feedback)
                         must carry a valid Clerk session cookie or 401.
                         When UNSET, the backend runs in "open dev mode"
                         and stamps every request with user_id="dev".
    CLERK_PUBLISHABLE_KEY Mirror of the frontend publishable key — only
                         used by GET /api/config so the SPA can boot
                         without baking it into the bundle.
    CLERK_WEBHOOK_SECRET Svix signing key for /api/auth/webhook. Required
                         if CLERK_SECRET_KEY is set; webhooks are
                         rejected with 401 if missing.

    FEEDBACK_EMAIL_TO    Where /api/feedback delivers messages (default
                         nchilaka@digi-setu.com).

In production Caddy serves the SPA from /srv/pi/www and reverse-proxies
/api/* and /ws/* to FastAPI on 127.0.0.1:8788, so the backend never
serves static assets itself.
"""

from __future__ import annotations

import os
from pathlib import Path

# pi-typst-test/web/backend/config.py
#   .parents[0] = backend/
#   .parents[1] = web/
#   .parents[2] = pi-typst-test/  ← PROJECT_ROOT (in dev) or /app (in container)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load backend/.env into os.environ before we read anything else.
# This is dev-mode convenience so users don't have to remember to
# `export $(cat .env | xargs)` before every uvicorn restart.
# In production the env comes from /opt/pi/stack.env via systemd's
# EnvironmentFile, so this no-ops there (no .env on the VM).
#
# Order matters: existing env vars WIN over .env values, so a one-off
# `CLERK_SECRET_KEY=foo uvicorn …` still overrides the file.
_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    try:
        for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k and _k not in os.environ:
                os.environ[_k] = _v
    except OSError:
        pass

# Where workspaces, chats, shadows, registry.json all live on local disk.
# In Cloud Run we point this at /tmp so the (read-only) image layer isn't
# touched. In dev it stays under web/data/.
_data_env = os.environ.get("PI_DATA_ROOT", "").strip()
DATA_ROOT = Path(_data_env).expanduser() if _data_env else PROJECT_ROOT / "web" / "data"

# "web" (default) or "desktop". The desktop launcher (Tauri) sets
# PI_MODE=desktop before spawning uvicorn so the frontend's picker UX
# branches accordingly.
DEPLOY_MODE = os.environ.get("PI_MODE", "web").strip().lower() or "web"

# CORS origins for the Vite dev server. Production same-origin requests
# don't need CORS at all (Caddy serves SPA + proxies API on the same host).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_extra = os.environ.get("PI_CORS_EXTRA_ORIGINS", "").strip()
if _extra:
    CORS_ORIGINS.extend(o.strip() for o in _extra.split(",") if o.strip())


# ── Clerk auth ─────────────────────────────────────────────────────
# Empty CLERK_SECRET_KEY = "open dev mode" (every request gets user_id
# "dev"). Setting all three flips the production guard on; see
# services/auth.py for the verify path.
CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY", "").strip()
CLERK_PUBLISHABLE_KEY = os.environ.get("CLERK_PUBLISHABLE_KEY", "").strip()
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET", "").strip()

# Stable identifier we stamp on every workspace/session in dev mode so
# the frontend's `owner_user_id` filter still works without a real
# Clerk session. NEVER returned to a real Clerk user (their `sub` is
# always a `user_xxx` token).
DEV_USER_ID = "dev"

AUTH_REQUIRED = bool(CLERK_SECRET_KEY)


# ── Feedback delivery ──────────────────────────────────────────────
FEEDBACK_EMAIL_TO = os.environ.get("FEEDBACK_EMAIL_TO", "").strip() or "nchilaka@digi-setu.com"


# ── Admin override ─────────────────────────────────────────────────
# Comma-separated lists of users who should be treated as enterprise-tier
# regardless of their Stripe subscription state. Useful for the operator
# (you) running local tests without paying yourself, and for support
# staff that need to reproduce a paid-plan-only bug. Both are checked.
#
#   ADMIN_EMAILS     match against the user's primary verified email
#                    address (case-insensitive). Resolved on first use
#                    via the Clerk SDK and cached forever in-process.
#                    Empty (default) = no email-based admins.
#   ADMIN_USER_IDS   match against Clerk's `user_xxx` sub. Doesn't need
#                    a network round-trip, so prefer this in containers
#                    where the Clerk lookup is on the latency budget.
#                    The literal id "dev" works in open-dev mode.
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
}
ADMIN_USER_IDS = {
    u.strip()
    for u in os.environ.get("ADMIN_USER_IDS", "").split(",")
    if u.strip()
}


# ── Stripe billing ─────────────────────────────────────────────────
# USD-only for v1 (Stripe Subscriptions don't support INR payments
# from India yet). When the first paying user from outside the US/EU
# asks for it we'll add Razorpay (India) or move to Paddle/Lemon
# Squeezy as Merchant of Record. Until then:
#
#   STRIPE_SECRET_KEY      sk_live_… / sk_test_… — set this to enable
#                          the /api/billing/* routes. When EMPTY all
#                          billing routes return 503 and the SPA
#                          surfaces "billing not configured".
#   STRIPE_WEBHOOK_SECRET  whsec_… from the Stripe Dashboard webhook
#                          page. Required when STRIPE_SECRET_KEY is set.
#   STRIPE_PRICE_STARTER   price_… ids per plan. Created once via
#   STRIPE_PRICE_PRO       Stripe Dashboard or `stripe prices create`;
#   STRIPE_PRICE_MAX       see deploy/README.md for the setup recipe.
#   BILLING_RETURN_URL     where Stripe redirects after checkout
#                          (success + cancel both go here, with a
#                          ?billing=success|cancel query). Defaults
#                          to OAUTH_REDIRECT_BASE.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
BILLING_RETURN_URL = (
    os.environ.get("BILLING_RETURN_URL", "").strip()
    or os.environ.get("OAUTH_REDIRECT_BASE", "").strip()
    or "http://localhost:5173"
)
BILLING_ENABLED = bool(STRIPE_SECRET_KEY)


# ── Per-workspace safety limits ────────────────────────────────────
# These are the soft caps that protect us (and the user) from a
# runaway pi turn. They're per-workspace, not per-user, because
# pi runs in a workspace and the costs accrue there.
#
#   WORKSPACE_DISK_QUOTA_MB    Refuse new prompts when the workspace
#                              dir exceeds this many MB. The agent
#                              has already written the file by the
#                              time we notice (we can't unwrite), so
#                              the gate is on the NEXT prompt — the
#                              user gets a clear "your sandbox is
#                              full, delete files or the chat" error.
#                              Default 100 MB matches the per-chat
#                              guidance we gave in deploy docs.
#   PROMPT_TIMEOUT_SECONDS     Wall-clock cap on a single pi turn.
#                              When pi gets stuck in a tool loop or a
#                              bash command hangs, we kill the entire
#                              pi subprocess after this many seconds
#                              so the user isn't billed for an
#                              infinite stream of "I'm thinking…"
#                              tokens. Default 900 = 15 min — enough
#                              for a deep Opus run, short enough that
#                              a runaway costs single-digit dollars.
def _i_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


WORKSPACE_DISK_QUOTA_MB = _i_env("WORKSPACE_DISK_QUOTA_MB", 100)
PROMPT_TIMEOUT_SECONDS = _i_env("PROMPT_TIMEOUT_SECONDS", 900)
