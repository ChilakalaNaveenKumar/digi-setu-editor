"""
Internal-only bearer token used by the spawned pi process to call
loopback endpoints (currently ``/api/internal/extract-md``).

Lifecycle:
    * On first call, mint a 256-bit URL-safe token via ``secrets``.
    * Pin it on ``os.environ["PI_INTERNAL_TOKEN"]`` so any subprocess
      we spawn (pi, the egress proxy, future workers) inherits it.
    * Subsequent calls return the same value — singleton — without
      regenerating, so the token survives across imports.

Why an env var rather than an in-memory module global?
    The pi process is a NODE child of the backend Python process. It
    needs to know the token to send it back as a bearer header. The
    cleanest cross-language hand-off is the env block we already
    populate in ``services/pi_session.py``. Storing the token on
    ``os.environ`` AFTER mint makes that subprocess hand-off a no-op
    (the spawned pi inherits the parent's env unless we explicitly
    strip it).

Operators can pre-set ``PI_INTERNAL_TOKEN`` in the runtime environment
(stack.env, systemd unit, k8s secret, …) to plug in their own value;
we honour it as-is rather than overwriting. Anything ≥16 chars is
accepted; we don't enforce a specific format because the operator may
have rotated to a shared-secret store with its own conventions.
"""

from __future__ import annotations

import os
import secrets
import threading

_lock = threading.Lock()
_MIN_LEN = 16


def get_internal_token(*, allow_empty: bool = False) -> str:
    """Return the per-process internal bearer token, minting one on
    first call. If ``allow_empty`` is True (used by /health), a missing
    token returns an empty string instead of raising — handy for
    smoke-testing the route reachability without actually authenticating.
    """
    existing = os.environ.get("PI_INTERNAL_TOKEN", "").strip()
    if len(existing) >= _MIN_LEN:
        return existing
    if allow_empty and not existing:
        # Don't mint just because /health was hit before any pi spawn —
        # operator hasn't proven they need it yet, and minting now
        # would leak via /health.
        return ""
    with _lock:
        # Double-check inside the lock — another thread may have
        # already minted. Same singleton trick as pi_session/UserPrefs.
        existing = os.environ.get("PI_INTERNAL_TOKEN", "").strip()
        if len(existing) >= _MIN_LEN:
            return existing
        # 32 bytes ≈ 43 chars URL-safe. Same format as Django's
        # SECRET_KEY recommendation.
        token = secrets.token_urlsafe(32)
        os.environ["PI_INTERNAL_TOKEN"] = token
        return token


def get_backend_base_url() -> str:
    """Best-effort URL the spawned pi can use to reach this backend.

    We don't try to introspect the live uvicorn binding because that
    would couple two layers (a) we'd have to thread the listening
    address through, and (b) on production Cloud Run / k8s the
    inside-the-pod address is `127.0.0.1:<PORT>` regardless of the
    public DNS, so the operator-supplied env var is always going to
    be the right answer.

    Resolution order:
        1. ``PI_BACKEND_BASE_URL`` (operator override, e.g.
           ``http://127.0.0.1:8788`` on prod or ``http://127.0.0.1:8000``
           in dev).
        2. ``UVICORN_HOST`` + ``UVICORN_PORT`` from the local boot env
           (set by uvicorn when invoked with --host/--port).
        3. ``http://127.0.0.1:8000`` — the conventional uvicorn
           default for `python -m uvicorn main:app`.
    """
    explicit = (os.environ.get("PI_BACKEND_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    host = (os.environ.get("UVICORN_HOST") or "").strip() or "127.0.0.1"
    port = (os.environ.get("UVICORN_PORT") or "").strip() or "8000"
    return f"http://{host}:{port}"
