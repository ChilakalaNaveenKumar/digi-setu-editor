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
                         support@digi-setu.com).

In production Caddy serves the SPA from /srv/pi/www and reverse-proxies
/api/* and /ws/* to FastAPI on 127.0.0.1:8788, so the backend never
serves static assets itself.
"""

from __future__ import annotations

import os
from pathlib import Path

# digi-setu/desktop/backend/config.py
#   .parents[0] = backend/
#   .parents[1] = desktop/
#   .parents[2] = <repo root>/  ← PROJECT_ROOT (in dev) or <_MEIPASS> (frozen)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── Single source of truth: Vertex AI default region ─────────────────────
# Both the desktop sidecar's startup auto-fill (config.py) and the per-
# request env builder (services/byok.py) anchor on this constant. Web's
# scripts/env.sh line 41 sets the equivalent default; if you ever change
# either, change BOTH or you'll silently route Vertex traffic to a region
# where the picked model 404s (which is exactly the silent-hang bug we
# hit when desktop defaulted to us-central1 while gemini-3-flash-preview
# only lives at "global").
VERTEX_DEFAULT_LOCATION = "global"

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
                "#\n"
                "# Google AI Studio (Gemini, free tier available — get a key at\n"
                "# https://aistudio.google.com/app/apikey):\n"
                "# GEMINI_API_KEY=AIza...\n"
                "#\n"
                "# OpenAI (GPT-4o etc.):\n"
                "# OPENAI_API_KEY=sk-proj-...\n"
                "#\n"
                "# === Without a key ===\n"
                "# Sign in with the in-app login button. Your subscription\n"
                "# covers the AI cost; the app routes prompts through\n"
                "# api.digi-setu.com and we never store the conversation.\n"
                "#\n"
                "# === Permissions ===\n"
                "# auto      = run every tool without asking\n"
                "# ask       = ask before shell / write / edit / process (default)\n"
                "# cautious  = ask before every tool call, including reads\n"
                "# PI_PERMISSION_MODE_DEFAULT=ask\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    _load_dotenv_into_environ(_USER_ENV)

    # ── Vertex auto-config (operator only) ─────────────────────────
    # When the dev sets `PI_OPERATOR_VERTEX=1` to test against their
    # service-account JSON locally, lift the project_id out of the
    # JSON so the parent uvicorn (title_gen helper) and any pi
    # subprocess have GOOGLE_CLOUD_PROJECT plugged in. Without this,
    # title_gen logs "[title_gen] GOOGLE_CLOUD_PROJECT unset" and any
    # Vertex pi turn hangs forever on a project-less URL.
    #
    # We DO NOT do this for end users — even if they happen to have
    # GOOGLE_APPLICATION_CREDENTIALS in their env (e.g. their shell
    # has it set for a different unrelated project), without
    # PI_OPERATOR_VERTEX=1 it's not a BYOK key and shouldn't bleed
    # into the desktop's Vertex env. The Clerk-relay path (M2+) is
    # what handles non-BYOK users.
    _operator_vertex = os.environ.get("PI_OPERATOR_VERTEX", "").strip().lower() in (
        "1", "true", "yes",
    )
    _adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if _operator_vertex and _adc and not os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip():
        try:
            import json as _json
            _adc_path = Path(_adc).expanduser().resolve()
            with open(_adc_path, "r", encoding="utf-8") as _f:
                _adc_json = _json.load(_f)
            _proj = ""
            if isinstance(_adc_json, dict):
                for _key in ("project_id", "quota_project_id"):
                    _val = _adc_json.get(_key)
                    if isinstance(_val, str) and _val.strip():
                        _proj = _val.strip()
                        break
            if _proj:
                os.environ["GOOGLE_CLOUD_PROJECT"] = _proj
                import sys as _sys
                print(
                    f"[config] auto-filled GOOGLE_CLOUD_PROJECT={_proj!r} "
                    f"from GOOGLE_APPLICATION_CREDENTIALS (PI_OPERATOR_VERTEX=1)",
                    file=_sys.stderr,
                )
        except (OSError, ValueError, ImportError) as _exc:
            import sys as _sys
            print(
                f"[config] WARN: could not read project_id from "
                f"GOOGLE_APPLICATION_CREDENTIALS={_adc!r}: {_exc}",
                file=_sys.stderr,
            )

    # Default location + Vertex SDK toggles, only if the operator
    # is intentionally on the Vertex path AND hasn't pinned them.
    # See VERTEX_DEFAULT_LOCATION below for why "global".
    if _operator_vertex and _adc:
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", VERTEX_DEFAULT_LOCATION)
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")


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
#
# Tenant matching (CRITICAL):
#   The JWT issued by Clerk's frontend (pk_xxx) can ONLY be verified
#   by the matching backend secret (sk_xxx) AND only by an upstream
#   that uses the same tenant. Mixing tenants gives the user-visible
#   bug "web shows my Enterprise plan, desktop shows Free" — because
#   the desktop minted a test-tenant JWT, the cloud verified against
#   prod, rejected with 401, and the desktop fell back to the
#   synthetic Free snapshot.
#
# To make this hard to misconfigure we auto-pick the prod Clerk pair
# (CLERK_*_PROD) whenever the desktop is pointed at the prod cloud
# (PI_CLOUD_API_BASE / PI_RELAY_BASE on digi-setu.com). The dev can
# still force the test tenant by exporting CLERK_TENANT=test (e.g.
# when running against a local FastAPI that's also configured with
# the test tenant).
_clerk_tenant_override = os.environ.get("CLERK_TENANT", "").strip().lower()


def _cloud_is_prod() -> bool:
    """True if any of the cloud endpoints we'll talk to live on the
    prod domain (digi-setu.com). Read directly from os.environ rather
    than the parsed PI_CLOUD_API_BASE / PI_RELAY_BASE because those
    are computed lower in this file (forward-reference avoidance).
    """
    candidates = [
        os.environ.get("PI_CLOUD_API_BASE", "").strip().lower(),
        os.environ.get("PI_RELAY_BASE", "").strip().lower(),
    ]
    # Defaults baked into the binary point at prod, so an unset env
    # also means "prod cloud" in practice.
    if not any(candidates):
        return True
    return any("digi-setu.com" in c for c in candidates if c)


def _resolve_clerk_pair() -> tuple[str, str]:
    """Pick the (publishable, secret) Clerk pair that matches the
    upstream we'll talk to. Falls back to the non-suffixed pair when
    the prod pair isn't configured.
    """
    test_pub = os.environ.get("CLERK_PUBLISHABLE_KEY", "").strip()
    test_sec = os.environ.get("CLERK_SECRET_KEY", "").strip()
    prod_pub = os.environ.get("CLERK_PUBLISHABLE_KEY_PROD", "").strip()
    prod_sec = os.environ.get("CLERK_SECRET_KEY_PROD", "").strip()

    want_prod: bool
    if _clerk_tenant_override == "prod":
        want_prod = True
    elif _clerk_tenant_override == "test":
        want_prod = False
    else:
        want_prod = _cloud_is_prod()

    if want_prod and prod_pub and prod_sec:
        return prod_pub, prod_sec
    return test_pub, test_sec


CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY = _resolve_clerk_pair()
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET", "").strip()

# Tag the active tenant for /api/config + log lines so the frontend
# can render "you're signed into the test tenant" warnings if needed
# and the operator can spot mismatches in the sidecar log.
if CLERK_PUBLISHABLE_KEY.startswith("pk_live_"):
    CLERK_TENANT_KIND = "prod"
elif CLERK_PUBLISHABLE_KEY.startswith("pk_test_"):
    CLERK_TENANT_KIND = "test"
else:
    CLERK_TENANT_KIND = "unknown"

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
# What counts as a real end-user key (intentional, considered list):
#
#   ANTHROPIC_API_KEY    — Anthropic console key, sk-ant-...
#   GEMINI_API_KEY       — Google AI Studio key, AIza...
#   GOOGLE_API_KEY       — alias accepted by some Google SDKs
#   OPENAI_API_KEY       — OpenAI key, sk-proj-... / sk-...
#
# Notably ABSENT: GOOGLE_APPLICATION_CREDENTIALS. That's a Google
# Cloud service-account JSON, which is operator-shaped (you provision
# it for a project you own, you bill its usage to that project). End
# users virtually never have one; their "I have a Google key" is
# GEMINI_API_KEY (free AI Studio tier). Treating ADC JSON as BYOK
# would silently route Gemini calls through `provider=google-vertex`,
# which fails without GOOGLE_CLOUD_PROJECT and looks like "chat
# never responds" to the user. See docs/desktop-architecture.md §5.
#
# The operator (this codebase's author) DOES want to test with their
# own service-account JSON locally — for that case we expose the
# explicit gate `PI_OPERATOR_VERTEX=1`. With that env var set AND a
# GOOGLE_APPLICATION_CREDENTIALS path that exists, we light up
# operator-Vertex BYOK. Without `PI_OPERATOR_VERTEX=1`, the JSON is
# ignored from a BYOK standpoint and the user falls through to the
# Clerk-relay path (M2+), where the operator's own server-side
# service account is what actually talks to Vertex.
_BYOK_PROBE_VARS = (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
)

# Operator override. Set in the developer's local env (NOT in the
# shipped binary, NOT in any user-facing template) to admit the
# service-account JSON path as a BYOK key for self-testing only.
_PI_OPERATOR_VERTEX = os.environ.get("PI_OPERATOR_VERTEX", "").strip().lower() in (
    "1",
    "true",
    "yes",
)


def _byok_keys_present() -> list[str]:
    """Return the list of detected BYOK env var names (for logging).

    The operator-override `GOOGLE_APPLICATION_CREDENTIALS` slot is
    appended last so existing log lines (`['ANTHROPIC_API_KEY',
    'GEMINI_API_KEY', ...]`) keep their stable order in the common
    case.
    """
    keys = [k for k in _BYOK_PROBE_VARS if os.environ.get(k, "").strip()]
    if _PI_OPERATOR_VERTEX and os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    ).strip():
        keys.append("GOOGLE_APPLICATION_CREDENTIALS")
    return keys


DETECTED_BYOK_KEYS = _byok_keys_present()
BYOK_MODE = DEPLOY_MODE == "desktop" and bool(DETECTED_BYOK_KEYS)

# Auth required iff:
#   - Clerk is configured (CLERK_SECRET_KEY set) AND
#   - we're not in BYOK mode (BYOK skips Clerk because the user is
#     paying their AI provider directly — there's nothing for us to
#     authorise against).
AUTH_REQUIRED = bool(CLERK_SECRET_KEY) and not BYOK_MODE


def refresh_byok_state() -> dict[str, object]:
    """Re-read ~/.digi-setu/.env into os.environ and recompute the
    BYOK-related module globals (DETECTED_BYOK_KEYS, BYOK_MODE,
    AUTH_REQUIRED). Returns a dict of the new values for the caller
    (the file watcher) to log.

    Mutates module globals in place so that callers using
    ``import config; config.BYOK_MODE`` see the live value. Callers
    using ``from config import BYOK_MODE`` capture the value at
    import time and won't observe the refresh — those call sites
    that need live values must switch to attribute access. The
    /api/config endpoint is the primary consumer for the UI gate
    and reads via attribute access.

    Idempotent. Safe to call from any thread (the underlying
    ``os.environ`` mutation is GIL-protected; module global writes
    are atomic in CPython).
    """
    global DETECTED_BYOK_KEYS, BYOK_MODE, AUTH_REQUIRED
    if DEPLOY_MODE == "desktop" and _DESKTOP_HOME is not None:
        _user_env = _DESKTOP_HOME / ".env"
        if _user_env.exists():
            # IMPORTANT: _load_dotenv_into_environ keeps existing env
            # vars unchanged (`if _k not in os.environ`). When the
            # user EDITS or REMOVES a key, the in-memory env still
            # has the old value. To make removals work we drop any
            # BYOK var that's not present in the new file before
            # re-loading.
            try:
                file_keys: set[str] = set()
                for _line in _user_env.read_text(encoding="utf-8").splitlines():
                    _stripped = _line.strip()
                    if (
                        not _stripped
                        or _stripped.startswith("#")
                        or "=" not in _stripped
                    ):
                        continue
                    _k, _, _ = _stripped.partition("=")
                    file_keys.add(_k.strip())
            except OSError:
                file_keys = set()
            for _byok_var in (*_BYOK_PROBE_VARS, "GOOGLE_APPLICATION_CREDENTIALS"):
                if _byok_var not in file_keys and _byok_var in os.environ:
                    # Best-effort: we only drop vars that the file
                    # CLAIMS to manage. Vars set by the parent shell
                    # (operator dev mode) stay put.
                    os.environ.pop(_byok_var, None)
            _load_dotenv_into_environ(_user_env)
    DETECTED_BYOK_KEYS = _byok_keys_present()
    BYOK_MODE = DEPLOY_MODE == "desktop" and bool(DETECTED_BYOK_KEYS)
    AUTH_REQUIRED = bool(CLERK_SECRET_KEY) and not BYOK_MODE
    return {
        "detected_byok_keys": list(DETECTED_BYOK_KEYS),
        "byok_mode": BYOK_MODE,
        "auth_required": AUTH_REQUIRED,
    }

if DEPLOY_MODE == "desktop":
    import sys as _sys
    if BYOK_MODE:
        if _PI_OPERATOR_VERTEX and "GOOGLE_APPLICATION_CREDENTIALS" in DETECTED_BYOK_KEYS:
            print(
                f"[config] BYOK mode (OPERATOR-VERTEX) — using "
                f"{DETECTED_BYOK_KEYS}. PI_OPERATOR_VERTEX=1 is set; "
                f"this path is for the Digi Setu dev only.",
                file=_sys.stderr,
            )
        else:
            print(
                f"[config] BYOK mode active — using user-provided keys: "
                f"{DETECTED_BYOK_KEYS}. Clerk login is OPTIONAL.",
                file=_sys.stderr,
            )
    elif CLERK_SECRET_KEY:
        print(
            f"[config] Clerk tenant = {CLERK_TENANT_KIND} "
            f"(publishable={CLERK_PUBLISHABLE_KEY[:14] + '…' if CLERK_PUBLISHABLE_KEY else 'unset'}). "
            f"Cloud target = {os.environ.get('PI_CLOUD_API_BASE') or 'https://digi-setu.com'}. "
            f"Override with CLERK_TENANT=test|prod if these don't match.",
            file=_sys.stderr,
        )
        # If the user has an ADC JSON but no PI_OPERATOR_VERTEX flag,
        # they may think they're providing a key. Tell them why we're
        # ignoring it so they don't spend an hour debugging.
        _stranded_adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if _stranded_adc and not _PI_OPERATOR_VERTEX:
            print(
                "[config] Note: GOOGLE_APPLICATION_CREDENTIALS is set but "
                "ignored as a BYOK key — service-account JSONs are "
                "operator-shaped, not end-user keys. To bring your own "
                "key set ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY "
                "in ~/.digi-setu/.env. Falling through to Clerk relay.",
                file=_sys.stderr,
            )
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


# ── Cloud relay (desktop-only) ─────────────────────────────────────
# When the user has no BYOK key and is signed in via Clerk, the
# desktop's chat WS dispatches the session to the operator-hosted
# relay endpoint instead of spawning pi locally. The relay runs pi
# server-side using the operator's Vertex creds (via egress_proxy.py),
# streams tokens back, and round-trips tool calls to the desktop.
#
#   PI_RELAY_BASE   — root URL of the relay WebSocket. Default points
#                     at production. Override for staging/local dev:
#                       PI_RELAY_BASE=ws://localhost:8788   (uvicorn
#                                                            without
#                                                            Caddy)
#                       PI_RELAY_BASE=wss://api-staging.digi-setu.com
#                     The desktop binary ships with the prod default
#                     baked in; only flip this if you're testing
#                     against a non-prod backend.
#
# We never override this with a user-supplied value from
# ~/.digi-setu/.env — that would let a tampered config redirect
# traffic to an attacker's relay. PI_RELAY_BASE is read from the
# process env only (set by the Tauri shell or the dev's launcher).
PI_RELAY_BASE = (
    os.environ.get("PI_RELAY_BASE", "").strip()
    or "wss://api.digi-setu.com"
).rstrip("/")

PI_RELAY_PATH = (
    os.environ.get("PI_RELAY_PATH", "").strip()
    or "/v1/ws/desktop-relay"
)

# ── Cloud HTTP API base ────────────────────────────────────────────
# The desktop sidecar is a *thin client* for everything billing-
# related (plans, monthly spend, activity log, Stripe Checkout /
# Customer Portal). The cloud — the only place Stripe creds and the
# canonical CreditLedger live — owns all of that. The sidecar proxies
# read-only calls to it and the SPA opens the customer-facing pages
# (https://digi-setu.com/pricing, …/account/billing) in the system
# browser for write actions.
#
#   PI_CLOUD_API_BASE   override the cloud HTTP base. Defaults to the
#                       APEX domain (https://digi-setu.com) because
#                       that's where the existing Caddyfile routes
#                       /api/* to FastAPI on 127.0.0.1:8788. The
#                       api.digi-setu.com subdomain is intentionally
#                       narrower — it only serves /v1/* (the desktop
#                       relay WS); calling /api/* on it returns 404
#                       (see deploy/caddy/Caddyfile, the api block at
#                       the bottom). Splitting "API" between two hosts
#                       is the cost of having shipped /v1/ws/desktop-
#                       relay before /api/* needed to be reachable
#                       from a desktop sidecar; we'll consolidate the
#                       day api.digi-setu.com gets a dedicated VM.
#   PI_CLOUD_WEB_BASE   override the cloud user-facing site base for
#                       Upgrade / Manage subscription deep-links.
#
# Same hardening as PI_RELAY_BASE: read from process env only, never
# from the user-controlled ~/.digi-setu/.env, so a tampered config
# can't redirect billing reads to an attacker's host.
PI_CLOUD_API_BASE = (
    os.environ.get("PI_CLOUD_API_BASE", "").strip()
    or "https://digi-setu.com"
).rstrip("/")

PI_CLOUD_WEB_BASE = (
    os.environ.get("PI_CLOUD_WEB_BASE", "").strip()
    or "https://digi-setu.com"
).rstrip("/")


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
# *** REMOVED FROM DESKTOP. ***
#
# Stripe credentials never live on a user's machine. The desktop
# sidecar has zero knowledge of secret keys, price ids, or webhook
# secrets — those exist only on the cloud backend at
# api.digi-setu.com.
#
# When the user clicks "Upgrade" or "Manage subscription" in the
# desktop UI we open https://digi-setu.com/pricing or
# https://digi-setu.com/account/billing in the system browser
# (see desktop/frontend/src/lib/native-bridge.ts → openExternal).
# Stripe Checkout and the Customer Portal run in the user's normal
# browser session, exactly like every other SaaS desktop app
# (Notion, Linear, Slack, …).
#
# Plan id + monthly spend + activity events are read from the cloud
# via routes/usage.py (which proxies api.digi-setu.com/api/usage)
# and cached briefly by services/plan_cache.py. They are NOT
# authoritative on the desktop — the cloud relay enforces every
# spend gate at chat-WS time, so a user who deletes their local
# state file gains nothing.
#
# Anything that previously flipped on `BILLING_ENABLED` is now
# always-on at the cloud (which always has Stripe configured) and
# always points-to-cloud at the desktop. The constant is kept here
# as `False` for backwards compatibility with any code that imports
# it during the deprecation window — those call sites should be
# converted to PI_CLOUD_WEB_BASE redirects.
BILLING_ENABLED = False


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
