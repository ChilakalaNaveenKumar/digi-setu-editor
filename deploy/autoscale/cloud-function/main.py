"""
pi-autoscale — Cloud Function that resizes the digi-setu-live VM based
on real load.

Lifecycle:

  Cloud Scheduler  ── every 10 min ──►  this function (HTTP trigger)
                                              │
                                              ▼
                              GET https://<host>/api/admin/load
                              (bearer token from Secret Manager)
                                              │
                              ┌───────────────┴───────────────┐
                              │  active_sessions, mem_util,   │
                              │  current machine_type         │
                              └───────────────┬───────────────┘
                                              │
                                              ▼
                                         pick_tier()
                                              │
                                  ┌───────────┴──────────┐
                                  │ Same tier as now? no-│
                                  │ op + log.            │
                                  │ Different tier?       │
                                  │   check cooldown      │
                                  │   stop → setMachineType
                                  │   → start             │
                                  └───────────────────────┘

Why HTTP-triggered (not Pub/Sub)?
  HTTP triggers expose a stable URL for the operator to curl with a
  ?force_tier=N query for emergencies. Pub/Sub triggers would require
  a separate publish step every time you want to nudge the box up.

Why a single function (vs. separate decide+apply)?
  At 10-minute cadence and small request volume there's no benefit to
  splitting. The whole run takes ~3-90s depending on whether a resize
  actually happens; well under the 540s Cloud Function default timeout.

Safety guards (all configurable via env vars):
  * AUTOSCALE_MIN_TIER / AUTOSCALE_MAX_TIER
        Pin the ladder. Default 0..4 (e2-small through e2-standard-8).
        Set both to the same value to lock the box to one size.
  * AUTOSCALE_COOLDOWN_S
        Seconds since last resize before ANY new resize is allowed.
        Default 900 (15 min). Prevents flapping between tiers when a
        single noisy turn pushes memory across a threshold.
  * AUTOSCALE_SCALE_DOWN_DELAY_S
        Extra cooldown ON TOP OF AUTOSCALE_COOLDOWN_S that scale-DOWN
        decisions must survive before being applied. Default 1800
        (30 min). Hysteresis: scale up fast, scale down slow.
  * AUTOSCALE_DRY_RUN
        "true" = log the decision but don't actually resize. Used for
        the initial bring-up to validate the tier picker before
        granting compute write IAM.

Operator overrides:
  curl -H "Authorization: Bearer $TOKEN" \\
       "https://$URL/?force_tier=3&reason=incident_2026_05_10"
  Forces a specific tier IMMEDIATELY, bypassing cooldown. Use only for
  incident response. Logged with the supplied reason.

Idempotency: a partial run (e.g. stop succeeds, set-machine-type
fails) leaves the VM stopped. The next scheduled invocation will
detect that, restart the VM at the OLD type, and try again. We never
leave the VM in a half-resized state.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import functions_framework
import requests
from google.cloud import compute_v1
from google.cloud import secretmanager

logger = logging.getLogger("pi_autoscale")
logger.setLevel(logging.INFO)


# ── Configuration (env vars) ─────────────────────────────────────────
GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
GCP_ZONE       = os.environ["GCP_ZONE"]            # e.g. us-central1-a
GCP_INSTANCE   = os.environ["GCP_INSTANCE"]        # e.g. digi-setu-live
BACKEND_URL    = os.environ["BACKEND_URL"].rstrip("/")  # e.g. https://digi-setu.com
ADMIN_TOKEN_SECRET = os.environ.get("ADMIN_TOKEN_SECRET", "pi-admin-load-token")

MIN_TIER = int(os.environ.get("AUTOSCALE_MIN_TIER", "0"))
MAX_TIER = int(os.environ.get("AUTOSCALE_MAX_TIER", "4"))
COOLDOWN_S = int(os.environ.get("AUTOSCALE_COOLDOWN_S", "900"))
SCALE_DOWN_EXTRA_S = int(os.environ.get("AUTOSCALE_SCALE_DOWN_DELAY_S", "1800"))
DRY_RUN = (os.environ.get("AUTOSCALE_DRY_RUN", "false").lower() == "true")


# ── Tier ladder ──────────────────────────────────────────────────────
# Each tier: (machine_type, mem_gib, scale_up_threshold_util)
#
# scale_up_threshold_util = fraction of THIS tier's memory after which
# we recommend moving to the NEXT tier. Trips when mem_util > threshold
# OR active_sessions > tier_mem_gib (1 GB per session, matching
# PI_SESSION_MEM_LIMIT).
TIERS: list[tuple[str, int, float]] = [
    ("e2-small",      2,  0.70),
    ("e2-medium",     4,  0.70),
    ("e2-standard-2", 8,  0.70),
    ("e2-standard-4", 16, 0.70),
    ("e2-standard-8", 32, 0.70),
]


def _machine_type_to_tier_index(machine_type: str) -> int:
    """Return the TIERS index for the given machine type, or -1 if it's
    one we don't have in the ladder (operator manually picked something
    weird — we'll pin to MIN_TIER on the next run to fix it)."""
    short = machine_type.rsplit("/", 1)[-1] if "/" in machine_type else machine_type
    for i, (name, _, _) in enumerate(TIERS):
        if name == short:
            return i
    return -1


def _pick_tier(sessions: int, mem_util: float, current_idx: int) -> tuple[int, str]:
    """Pure decision function: return (target_tier, reason)."""
    current_idx = max(0, current_idx)
    cur_name, cur_gib, cur_thresh = TIERS[current_idx]

    needs_scale_up = (
        mem_util > cur_thresh
        or sessions > cur_gib  # 1 GB per pi container
    )
    if needs_scale_up and current_idx < MAX_TIER:
        return current_idx + 1, (
            f"mem_util={mem_util:.2%} or sessions={sessions} exceeds "
            f"tier {current_idx} ({cur_name}, {cur_gib}GiB)"
        )

    # Scale down if there's plenty of room AT THE PREVIOUS TIER.
    # Requires the smaller tier could handle the load with headroom:
    #   smaller tier mem * scale_up_threshold ≥ current actual usage
    if current_idx > MIN_TIER:
        prev_name, prev_gib, prev_thresh = TIERS[current_idx - 1]
        cur_used_gib = mem_util * cur_gib
        fits_smaller = (
            cur_used_gib < prev_gib * prev_thresh * 0.7  # 70% safety margin
            and sessions <= prev_gib * 0.7
        )
        if fits_smaller:
            return current_idx - 1, (
                f"mem_used={cur_used_gib:.1f}GiB + sessions={sessions} "
                f"fits comfortably in tier {current_idx - 1} ({prev_name})"
            )

    return current_idx, f"holding at tier {current_idx} ({cur_name})"


# ── Cloud helpers ────────────────────────────────────────────────────
_compute_client: Optional[compute_v1.InstancesClient] = None
_secret_client: Optional[secretmanager.SecretManagerServiceClient] = None
_cached_token: Optional[str] = None


def _get_compute_client() -> compute_v1.InstancesClient:
    global _compute_client
    if _compute_client is None:
        _compute_client = compute_v1.InstancesClient()
    return _compute_client


def _get_admin_token() -> str:
    """Resolve the admin bearer token from Secret Manager. Cached for
    the lifetime of this function instance (Cloud Functions reuse
    instances across invocations, so this saves a Secret Manager RPC
    on every scheduled run)."""
    global _secret_client, _cached_token
    if _cached_token:
        return _cached_token
    if _secret_client is None:
        _secret_client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{ADMIN_TOKEN_SECRET}/versions/latest"
    resp = _secret_client.access_secret_version(request={"name": name})
    _cached_token = resp.payload.data.decode("utf-8").strip()
    return _cached_token


def _fetch_load() -> dict[str, Any]:
    """Call the backend's GET /api/admin/load with the bearer token."""
    token = _get_admin_token()
    r = requests.get(
        f"{BACKEND_URL}/api/admin/load",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"backend returned non-ok: {data}")
    return data


def _get_instance() -> compute_v1.Instance:
    return _get_compute_client().get(
        project=GCP_PROJECT_ID,
        zone=GCP_ZONE,
        instance=GCP_INSTANCE,
    )


def _wait_op(zone_op: compute_v1.Operation, kind: str, timeout_s: int = 180) -> None:
    """Block until a zonal operation completes (or raise)."""
    op_client = compute_v1.ZoneOperationsClient()
    start = time.monotonic()
    while True:
        op = op_client.get(
            project=GCP_PROJECT_ID,
            zone=GCP_ZONE,
            operation=zone_op.name,
        )
        if op.status == compute_v1.Operation.Status.DONE:
            if op.error and op.error.errors:
                raise RuntimeError(f"{kind} failed: {op.error}")
            return
        if time.monotonic() - start > timeout_s:
            raise TimeoutError(f"{kind} did not complete within {timeout_s}s")
        time.sleep(2)


def _seconds_since(iso_ts: str) -> float:
    """Parse an ISO-8601 timestamp from the compute API and return how
    many seconds ago it was. Returns +inf when input is empty so a
    fresh VM (no lastStartTimestamp) is treated as 'cooldown long ago
    expired'."""
    if not iso_ts:
        return float("inf")
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    now = datetime.now(timezone.utc)
    return (now - ts).total_seconds()


def _apply_resize(target_machine_type: str, current_status: str) -> None:
    """Perform stop → setMachineType → start. Tolerant of partial
    state from a previous failed run (e.g. VM already TERMINATED)."""
    if DRY_RUN:
        logger.info("[dry-run] would resize to %s (current status: %s)",
                    target_machine_type, current_status)
        return

    client = _get_compute_client()

    if current_status != "TERMINATED":
        logger.info("Stopping instance %s …", GCP_INSTANCE)
        op = client.stop(
            project=GCP_PROJECT_ID,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE,
        )
        _wait_op(op, "stop")
        logger.info("Stopped.")

    full_mt = (
        f"projects/{GCP_PROJECT_ID}/zones/{GCP_ZONE}/machineTypes/{target_machine_type}"
    )
    logger.info("Setting machine type → %s …", target_machine_type)
    op = client.set_machine_type(
        project=GCP_PROJECT_ID,
        zone=GCP_ZONE,
        instance=GCP_INSTANCE,
        instances_set_machine_type_request_resource=compute_v1.InstancesSetMachineTypeRequest(
            machine_type=full_mt,
        ),
    )
    _wait_op(op, "setMachineType")
    logger.info("Machine type set.")

    logger.info("Starting instance %s …", GCP_INSTANCE)
    op = client.start(
        project=GCP_PROJECT_ID,
        zone=GCP_ZONE,
        instance=GCP_INSTANCE,
    )
    _wait_op(op, "start")
    logger.info("Started. Stack will come back up via pi.service in ~30s.")


# ── HTTP entry point ─────────────────────────────────────────────────
@functions_framework.http
def autoscale(request) -> tuple[str, int]:
    """HTTP handler. Idempotent — Cloud Scheduler retries are safe."""
    force_tier_raw = (request.args.get("force_tier") if request else "") or ""
    reason_override = (request.args.get("reason") if request else "") or ""
    force_tier: Optional[int] = None
    if force_tier_raw:
        try:
            force_tier = int(force_tier_raw)
        except ValueError:
            return json.dumps({"error": "force_tier must be an integer"}), 400
        if not (MIN_TIER <= force_tier <= MAX_TIER):
            return json.dumps(
                {"error": f"force_tier must be {MIN_TIER}..{MAX_TIER}"}
            ), 400

    # 1. Snapshot current instance state from compute API.
    inst = _get_instance()
    current_status = inst.status  # RUNNING / STOPPING / TERMINATED / ...
    current_mt = inst.machine_type
    current_idx = _machine_type_to_tier_index(current_mt)
    last_start = (inst.last_start_timestamp or "")  # ISO 8601
    seconds_since_start = _seconds_since(last_start)

    # 2. If the VM isn't running, refuse to act (operator intervention).
    if current_status not in {"RUNNING", "TERMINATED"}:
        msg = (
            f"instance is {current_status}; refusing to act. "
            f"Wait for it to settle, or apply manually."
        )
        logger.warning(msg)
        return json.dumps({"action": "skipped", "reason": msg}), 200

    # 3. Decide target tier.
    if force_tier is not None:
        target_idx = force_tier
        decision_reason = f"force_tier={force_tier} reason={reason_override or 'unspecified'}"
    else:
        # Fetch backend load. If this fails, fall back to "no change" —
        # we don't want a single backend hiccup triggering a resize.
        try:
            load = _fetch_load()
        except Exception as exc:
            logger.exception("Could not fetch /api/admin/load; holding tier.")
            return json.dumps({
                "action": "skipped",
                "reason": f"load fetch failed: {exc}",
            }), 200

        target_idx, decision_reason = _pick_tier(
            sessions=int(load.get("active_sessions", 0)),
            mem_util=float(load.get("mem_util", 0.0)),
            current_idx=current_idx,
        )

    target_idx = max(MIN_TIER, min(MAX_TIER, target_idx))
    target_name = TIERS[target_idx][0]
    current_name = TIERS[max(0, current_idx)][0] if current_idx >= 0 else "unknown"

    summary: dict[str, Any] = {
        "current_machine_type": current_name,
        "target_machine_type":  target_name,
        "current_tier":         current_idx,
        "target_tier":          target_idx,
        "reason":               decision_reason,
        "seconds_since_last_start": seconds_since_start,
        "dry_run": DRY_RUN,
    }

    # 4. Already at target → no-op.
    if target_idx == current_idx:
        summary["action"] = "no_change"
        logger.info(json.dumps(summary))
        return json.dumps(summary), 200

    # 5. Cooldown checks (skipped for force_tier).
    if force_tier is None:
        if seconds_since_start < COOLDOWN_S:
            summary["action"] = "cooldown"
            summary["reason"] = (
                f"only {seconds_since_start:.0f}s since last start; "
                f"cooldown is {COOLDOWN_S}s. Holding."
            )
            logger.info(json.dumps(summary))
            return json.dumps(summary), 200
        if target_idx < current_idx and seconds_since_start < (
            COOLDOWN_S + SCALE_DOWN_EXTRA_S
        ):
            summary["action"] = "scale_down_pending"
            summary["reason"] = (
                f"scale-down requires {COOLDOWN_S + SCALE_DOWN_EXTRA_S}s "
                f"since last start; only {seconds_since_start:.0f}s elapsed. "
                "Holding."
            )
            logger.info(json.dumps(summary))
            return json.dumps(summary), 200

    # 6. Apply.
    summary["action"] = "resize"
    logger.info("Applying: %s", json.dumps(summary))
    try:
        _apply_resize(target_name, current_status)
    except Exception as exc:
        logger.exception("Resize failed.")
        summary["action"] = "resize_failed"
        summary["error"] = str(exc)
        return json.dumps(summary), 500
    logger.info("Resize applied: %s", json.dumps(summary))
    return json.dumps(summary), 200
