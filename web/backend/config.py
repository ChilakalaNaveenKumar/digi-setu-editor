"""
Backend-wide configuration constants resolved from env / on-disk paths.

Anything that needs to know where data lives or how to talk to the
outside world imports from here so we have one switch to flip between
local dev and Cloud Run.

Environment knobs (all optional):

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
                         support@digi-setu.com).

In production Caddy serves the SPA from /srv/pi/www and reverse-proxies
/api/* and /ws/* to FastAPI on 127.0.0.1:8788, so the backend never
serves static assets itself.
"""

from __future__ import annotations

import os
from pathlib import Path

# digi-setu/web/backend/config.py
#   .parents[0] = backend/
#   .parents[1] = web/
#   .parents[2] = <repo root>/  ← PROJECT_ROOT (in dev) or /app (in container)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _load_dotenv_into_environ(path: Path) -> bool:
    """Best-effort dotenv parser. Existing env vars win, missing file = no-op.

    Returns True if the file was found and parsed. We deliberately don't
    pull `python-dotenv` for this — the format we accept is a strict
    KEY=VALUE subset (no command substitution, no multi-line values),
    and writing 12 lines is cheaper than a runtime dep.
    """
    if not path.exists():
        return False
    try:
        for _line in path.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _k = _k.strip()
            _v = _v.strip().strip('"').strip("'")
            if _k and _k not in os.environ:
                os.environ[_k] = _v
        return True
    except OSError:
        return False


# Load backend/.env into os.environ before we read anything else.
# This is dev-mode convenience so users don't have to remember to
# `export $(cat .env | xargs)` before every uvicorn restart.
# In production env comes from /opt/pi/stack.env via systemd's
# EnvironmentFile.
_BACKEND_DIR = Path(__file__).resolve().parent
_load_dotenv_into_environ(_BACKEND_DIR / ".env")


# Where workspaces, chats, shadows, registry.json all live on local disk.
# Cloud Run / prod points this at /tmp or a tmpfs (via PI_DATA_ROOT).
# Local dev keeps the historical web/data/.
_data_env = os.environ.get("PI_DATA_ROOT", "").strip()
if _data_env:
    DATA_ROOT = Path(_data_env).expanduser()
else:
    DATA_ROOT = PROJECT_ROOT / "web" / "data"

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


# ── BYOK (bring-your-own-key) ──────────────────────────────────────
# BYOK was a desktop-only feature: in the desktop fork, users drop AI
# provider credentials into ~/.digi-setu/.env and chat calls go
# directly from their machine to the provider, billed against their
# own account. The hosted SaaS web backend NEVER routes that way —
# every chat goes through the operator's Clerk-gated subscription
# pipeline against the operator's Vertex credentials, which are
# expected to be present in this backend's env.
#
# We pin BYOK_MODE to False here for two reasons:
#   1. The web backend uses GOOGLE_APPLICATION_CREDENTIALS for Vertex
#      auth in production. If we auto-detected BYOK from "any AI
#      provider env var present" we'd flip BYOK_MODE on in production
#      and accidentally skip Clerk auth — that's a security hole.
#   2. The desktop fork (desktop/backend/) keeps its own BYOK gate
#      and is where the feature actually lives. Web is separate.
#
# DETECTED_BYOK_KEYS stays as an empty list so /api/config / /api/models
# can still report "no BYOK" to the SPA without a special case.
BYOK_MODE = False
DETECTED_BYOK_KEYS: list[str] = []

# Auth required iff Clerk is configured (CLERK_SECRET_KEY set). The
# old `not BYOK_MODE` half of this conjunction is redundant now that
# BYOK_MODE is pinned False, but kept inline for symmetry with the
# desktop fork's config.
AUTH_REQUIRED = bool(CLERK_SECRET_KEY) and not BYOK_MODE


# ── Feedback delivery ──────────────────────────────────────────────
FEEDBACK_EMAIL_TO = os.environ.get("FEEDBACK_EMAIL_TO", "").strip() or "support@digi-setu.com"


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
#                              the gate is on the NEXT prompt.
#                              Default 2048 MB (2 GiB). Generous
#                              enough for most Typst projects + a
#                              dataset, but caps the per-tenant cost
#                              of a runaway agent. Power users who
#                              need more headroom (multi-GB datasets,
#                              installed toolchains, media work) are
#                              steered toward the desktop client by
#                              the over-quota error message — which
#                              pitches the local app instead of
#                              asking them to delete files.
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


WORKSPACE_DISK_QUOTA_MB = _i_env("WORKSPACE_DISK_QUOTA_MB", 2048)
PROMPT_TIMEOUT_SECONDS = _i_env("PROMPT_TIMEOUT_SECONDS", 900)
