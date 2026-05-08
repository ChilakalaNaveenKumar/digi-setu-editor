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
# In production (web mode) env comes from /opt/pi/stack.env via
# systemd's EnvironmentFile.
_BACKEND_DIR = Path(__file__).resolve().parent
_load_dotenv_into_environ(_BACKEND_DIR / ".env")

# "web" (default) or "desktop". The desktop launcher (Tauri) sets
# PI_MODE=desktop before spawning uvicorn so the frontend's picker UX
# branches accordingly.
DEPLOY_MODE = os.environ.get("PI_MODE", "web").strip().lower() or "web"


# ── Desktop home dir (~/.digi-setu/) ───────────────────────────────
# Desktop mode keeps EVERYTHING under one user-visible folder:
#   ~/.digi-setu/.env                user-editable (BYOK keys, prefs)
#   ~/.digi-setu/workspaces/         per-workspace chats + shadow git
#   ~/.digi-setu/audits/             AI tool-call audit trail
#   ~/.digi-setu/registry.json       workspace catalogue
#   ~/.digi-setu/prefs.json          permission_mode + UI prefs
#
# The path is set by the Tauri shell via PI_DATA_ROOT, but we recompute
# it here too as a fallback (running the sidecar binary by hand without
# Tauri) and use it to locate the .env file. On Windows this becomes
# %USERPROFILE%\.digi-setu\.
def _desktop_home() -> Path:
    explicit = os.environ.get("DIGI_SETU_HOME", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".digi-setu"


_DESKTOP_HOME = _desktop_home() if DEPLOY_MODE == "desktop" else None

# In desktop mode load ~/.digi-setu/.env BEFORE we read any of the
# CLERK_/STRIPE_/ANTHROPIC_/etc. vars below — that's where the user
# puts their BYOK keys and personal config. We seed an example .env
# the first time the file is missing so they don't have to guess
# what to write.
if DEPLOY_MODE == "desktop" and _DESKTOP_HOME is not None:
    try:
        _DESKTOP_HOME.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[config] WARN: cannot create {_DESKTOP_HOME}: {exc}", file=__import__("sys").stderr)

    _USER_ENV = _DESKTOP_HOME / ".env"
    if not _USER_ENV.exists():
        # Seed a friendly template the user can edit. The defaults
        # below are commented out — uncommenting any one of them
        # flips the app into BYOK mode (see AUTH_REQUIRED logic
        # below). We never write secrets ourselves; this is just a
        # blank canvas.
        try:
            _USER_ENV.write_text(
                "# Digi Setu — user config\n"
                "# Edit this file to bring your own AI provider keys.\n"
                "# Anything you set here wins over the app's built-in defaults.\n"
                "#\n"
                "# === Bring your own key (skips Clerk login) ===\n"
                "# Uncomment ONE of the blocks below and paste your key:\n"
                "#\n"
                "# Anthropic (Claude direct):\n"
                "# ANTHROPIC_API_KEY=sk-ant-...\n"
                "# PI_PROVIDER=anthropic\n"
                "# PI_MODEL=claude-sonnet-4-6\n"
                "#\n"
                "# Google AI Studio (Gemini, free tier available):\n"
                "# GEMINI_API_KEY=AIza...\n"
                "# PI_PROVIDER=google\n"
                "# PI_MODEL=gemini-3-pro-preview\n"
                "#\n"
                "# Vertex AI (your own GCP project):\n"
                "# GOOGLE_APPLICATION_CREDENTIALS=/Users/you/path/to/service-account.json\n"
                "# GOOGLE_CLOUD_PROJECT=your-project\n"
                "# PI_PROVIDER=anthropic-vertex\n"
                "# PI_MODEL=claude-sonnet-4-6\n"
                "#\n"
                "# === Permissions ===\n"
                "# auto / approve_risky / approve_all\n"
                "# PI_PERMISSION_MODE_DEFAULT=approve_risky\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    _load_dotenv_into_environ(_USER_ENV)


# Where workspaces, chats, shadows, registry.json all live on local disk.
# Cloud Run / web prod points this at /tmp or a tmpfs. Desktop points
# it at ~/.digi-setu/. Local dev keeps the historical web/data/.
_data_env = os.environ.get("PI_DATA_ROOT", "").strip()
if _data_env:
    DATA_ROOT = Path(_data_env).expanduser()
elif DEPLOY_MODE == "desktop" and _DESKTOP_HOME is not None:
    DATA_ROOT = _DESKTOP_HOME
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
# In desktop mode, if the user dropped any AI provider credentials
# into ~/.digi-setu/.env we treat that as "I'm running this fully
# offline against my own quota; don't make me sign in to Clerk".
#
# Detection rule: any one of these env vars present and non-empty.
# Order doesn't matter — pi_session.py picks the right provider
# based on PI_PROVIDER (which the user also sets, or we infer below).
_BYOK_PROBE_VARS = (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "OPENAI_API_KEY",
)


def _byok_keys_present() -> list[str]:
    """Return the list of detected BYOK env var names (for logging)."""
    return [k for k in _BYOK_PROBE_VARS if os.environ.get(k, "").strip()]


DETECTED_BYOK_KEYS = _byok_keys_present()
BYOK_MODE = DEPLOY_MODE == "desktop" and bool(DETECTED_BYOK_KEYS)

# Auth required iff:
#   - Clerk is configured (CLERK_SECRET_KEY set) AND
#   - we're not in BYOK mode (BYOK skips Clerk because the user is
#     paying their AI provider directly — there's nothing for us to
#     authorise against).
AUTH_REQUIRED = bool(CLERK_SECRET_KEY) and not BYOK_MODE

if DEPLOY_MODE == "desktop":
    import sys as _sys
    if BYOK_MODE:
        print(
            f"[config] BYOK mode active — using user-provided keys: "
            f"{DETECTED_BYOK_KEYS}. Clerk login is OPTIONAL.",
            file=_sys.stderr,
        )
    elif CLERK_SECRET_KEY:
        print(
            "[config] No BYOK keys found in ~/.digi-setu/.env — "
            "Clerk login required for cloud-relay AI access.",
            file=_sys.stderr,
        )
    else:
        print(
            "[config] WARN: desktop mode without Clerk OR BYOK keys. "
            "AI calls will fail until the user signs in OR adds keys "
            "to ~/.digi-setu/.env.",
            file=_sys.stderr,
        )


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
