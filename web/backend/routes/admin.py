"""
Public admin routes consumed by off-VM operators / automation.

Currently exposes:

  GET /api/admin/load
    Returns memory utilisation, active session count, and the GCE
    machine type the backend is running on. Used by the autoscaler
    Cloud Function (`deploy/autoscale/cloud-function/`) to pick a
    target tier on a 10-minute cadence.

Auth model — deliberately separate from Clerk:
  * Clerk fronts every USER-facing route. An off-VM automation (the
    autoscaler) has no Clerk session, so it presents a long random
    bearer token sourced from the operator-managed
    ``ADMIN_LOAD_TOKEN`` env var (stack.env on the VM, Secret Manager
    secret on the Cloud Function side).
  * Empty / unset token => the route is DISABLED (returns 503). Never
    expose the load endpoint without a token in production.
  * Constant-time bearer compare so a guess attack can't be timed.

Unlike /api/internal/* this route is NOT loopback-only: the autoscaler
runs in a Cloud Function and reaches the VM via Caddy on the public
hostname. The bearer token is the only thing standing between this
endpoint and the internet, so the secret needs to be:
  * 32+ bytes of crypto-grade randomness
  * stored in Secret Manager (Cloud Function side) and stack.env (VM
    side) with mode 0600
  * rotated on operator turnover
"""

from __future__ import annotations

import logging
import os
import secrets as _secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _load_token() -> str:
    """Resolved at call time so a `systemctl restart pi.service` after a
    token rotation takes effect without a backend rebuild."""
    return (os.environ.get("ADMIN_LOAD_TOKEN") or "").strip()


def _require_admin_bearer(authorization: str | None) -> None:
    expected = _load_token()
    if not expected:
        # Endpoint is DISABLED when no token is set. Returning 503
        # (instead of 401) makes it obvious to a probing operator that
        # the route exists but the deployment hasn't enabled it.
        raise HTTPException(
            status_code=503,
            detail="admin api disabled (ADMIN_LOAD_TOKEN not set)",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing admin bearer token")
    presented = authorization.split(" ", 1)[1].strip()
    if not _secrets.compare_digest(presented, expected):
        raise HTTPException(status_code=403, detail="bad admin bearer token")


def _read_meminfo() -> tuple[int, int]:
    """Return (mem_used_bytes, mem_total_bytes) from /proc/meminfo.

    Uses MemTotal − MemAvailable to match what `free -b` reports as
    "used". MemAvailable accounts for buffers/cache that the kernel
    will reclaim under pressure, which is the right signal for an
    autoscaler — caches aren't a problem to keep around, real
    allocations are.

    Returns (0, 0) on platforms without /proc/meminfo (macOS dev
    boxes) so the endpoint doesn't 500 in local testing.
    """
    try:
        with open("/proc/meminfo", "r", encoding="ascii") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return 0, 0
    total_kb = avail_kb = 0
    for line in lines:
        if line.startswith("MemTotal:"):
            total_kb = int(line.split()[1])
        elif line.startswith("MemAvailable:"):
            avail_kb = int(line.split()[1])
        if total_kb and avail_kb:
            break
    if not total_kb:
        return 0, 0
    used_kb = max(total_kb - avail_kb, 0)
    return used_kb * 1024, total_kb * 1024


def _read_machine_type() -> str:
    """Read the GCE machine type from the metadata server.

    Returns the short name (``e2-small``) — NOT the projects/.../
    machineTypes/... fully-qualified form. Empty string when running
    outside GCE (local dev, CI). Times out fast (1 s) so a metadata-
    server outage doesn't slow load polling.
    """
    try:
        import urllib.request

        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/machine-type",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:  # noqa: S310
            raw = resp.read().decode("ascii", errors="replace").strip()
    except Exception:
        return ""
    # Format: projects/PROJECT_NUM/machineTypes/e2-small
    if "/machineTypes/" in raw:
        return raw.rsplit("/machineTypes/", 1)[-1]
    return raw


async def _active_session_count() -> int:
    """Count of currently-running per-session containers via the
    container pool helper. Returns 0 when docker is unreachable
    (subprocess runtime fallback, dev box without docker)."""
    try:
        from services import container_pool

        return await container_pool.global_count()
    except Exception as exc:
        logger.warning("admin.load: global_count failed: %s", exc)
        return 0


@router.get("/load")
async def admin_load(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Snapshot of the signals the autoscaler needs.

    Response shape (stable; do NOT break — the Cloud Function pins to
    these field names):

        {
          "active_sessions": 12,
          "mem_used_bytes":  5_234_221_440,
          "mem_total_bytes": 8_364_158_976,
          "mem_util":        0.6258,        // 0..1
          "machine_type":    "e2-standard-2",
          "ok":              true
        }
    """
    _require_admin_bearer(authorization)
    used, total = _read_meminfo()
    sessions = await _active_session_count()
    util = (used / total) if total else 0.0
    return {
        "ok": True,
        "active_sessions": sessions,
        "mem_used_bytes": used,
        "mem_total_bytes": total,
        "mem_util": round(util, 4),
        "machine_type": _read_machine_type(),
    }
