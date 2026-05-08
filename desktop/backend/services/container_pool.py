"""
container_pool — lifecycle management for per-session pi-session containers.

Three jobs:

    1. **Orphan cleanup on backend boot.** A backend crash / kill -9
       leaves `pi-sess-*` containers running with no parent. They eat
       memory + Vertex tokens (the AI inside might still be looping).
       On startup we enumerate every container labelled `pi.app=
       pi-typst-test` and `docker rm -f` them. Idempotent — fresh boot
       with no stale containers is a no-op.

    2. **Per-user concurrency cap.** Without this, a user could open
       10 chats, leave them all active, and burn ~10 GiB of mem +
       100 PIDs on the VM. We cap at PI_SESSION_MAX_PER_USER (default
       2) — when a 3rd chat opens we kill the user's OLDEST container
       (by container start time) before spawning the new one. The
       UI surfaces this as "older chat suspended; reopen to resume".

    3. **Global concurrency cap.** Total `pi-sess-*` containers on the
       VM cap at PI_SESSION_MAX_GLOBAL (default 50). New chats beyond
       this cap return a structured 429 — the SPA shows
       "VM at capacity, try again in a minute".

Threading: this module's public functions are called from the FastAPI
event loop (lifespan, chat_ws WebSocket handler). Docker CLI calls are
blocking subprocess invocations done in a thread executor so the loop
stays responsive. Average call latency: 30-150ms (dockerd RTT +
process spawn).

Labels (applied at `docker run` in services/pi_session.py — that file
imports `LABEL_*` constants from here so the strings stay in sync):

    pi.app          "pi-typst-test"          identifies our containers
    pi.user_id      <user_xxx | "dev">       quota / orphan attribution
    pi.session_id   <full session_id>        debug correlation
    pi.created_at   <ISO 8601 UTC>           tiebreaker for "oldest"
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

# Constants (also imported by services/pi_session.py to keep the
# label strings authoritative in one place).
LABEL_APP_KEY = "pi.app"
LABEL_APP_VALUE = "pi-typst-test"
LABEL_USER_ID = "pi.user_id"
LABEL_SESSION_ID = "pi.session_id"
LABEL_CREATED_AT = "pi.created_at"

PI_SESSION_MAX_PER_USER = int(os.environ.get("PI_SESSION_MAX_PER_USER", "2"))
PI_SESSION_MAX_GLOBAL = int(os.environ.get("PI_SESSION_MAX_GLOBAL", "50"))


class ContainerPoolUnavailable(RuntimeError):
    """Raised when docker is not reachable. The caller should fall
    back to the subprocess runtime instead of failing the chat."""


class GlobalCapacityExceeded(RuntimeError):
    """Raised when the VM is at PI_SESSION_MAX_GLOBAL containers."""


def _docker_bin() -> Optional[str]:
    return shutil.which("docker")


def _run_docker(*args: str, timeout: float = 10.0) -> tuple[int, str, str]:
    """
    Synchronous docker invocation. Returns (rc, stdout, stderr).
    Used in `await asyncio.to_thread(...)` from the async public API.
    """
    docker = _docker_bin()
    if not docker:
        raise ContainerPoolUnavailable("docker binary not found in PATH")
    try:
        proc = subprocess.run(
            [docker, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ContainerPoolUnavailable(f"docker {args[0]} timed out after {timeout}s")
    return proc.returncode, proc.stdout, proc.stderr


def _list_containers_sync(filters: list[str]) -> list[str]:
    """Return container IDs matching the given filter list."""
    args = ["ps", "-a", "--quiet"]
    for f in filters:
        args += ["--filter", f]
    rc, out, err = _run_docker(*args, timeout=5.0)
    if rc != 0:
        logger.warning("container_pool: docker ps failed (rc=%d): %s", rc, err.strip())
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _inspect_container_sync(container_id: str, fmt: str) -> Optional[str]:
    """Return formatted field from `docker inspect` or None on failure."""
    rc, out, _ = _run_docker(
        "inspect", "--format", fmt, container_id, timeout=3.0
    )
    if rc != 0:
        return None
    return out.strip() or None


# ── Public API ───────────────────────────────────────────────────────
async def cleanup_orphaned_containers() -> int:
    """
    Find every pi-typst-test container on the host and force-remove
    it. Returns the count removed. Called once from the FastAPI
    lifespan startup so a backend restart leaves no stragglers.

    Why not match by name prefix `pi-sess-*`? Because the operator
    might run a one-off container with a similar name during
    debugging; the `pi.app` label is OURS and won't clash with manual
    invocations.
    """
    try:
        ids = await asyncio.to_thread(
            _list_containers_sync,
            [f"label={LABEL_APP_KEY}={LABEL_APP_VALUE}"],
        )
    except ContainerPoolUnavailable as exc:
        logger.info("container_pool: docker not reachable, skipping cleanup: %s", exc)
        return 0

    if not ids:
        return 0

    # `docker rm -f` accepts multiple IDs in one call. Force flag
    # because some might still be running.
    try:
        rc, _, err = await asyncio.to_thread(
            _run_docker, "rm", "-f", *ids, timeout=15.0
        )
    except ContainerPoolUnavailable as exc:
        logger.warning("container_pool: cleanup rm failed: %s", exc)
        return 0

    if rc != 0:
        logger.warning("container_pool: docker rm -f failed (rc=%d): %s", rc, err.strip())
        # Some IDs might have been removed before the failure; we still
        # report the attempt count.

    logger.info("container_pool: removed %d orphaned pi-session containers", len(ids))
    return len(ids)


async def count_for_user(user_id: str) -> int:
    """
    Return the number of currently-running pi-session containers for
    `user_id`. Used by the chat WebSocket handler to enforce the
    per-user concurrency cap.
    """
    if not user_id:
        return 0
    try:
        ids = await asyncio.to_thread(
            _list_containers_sync,
            [
                f"label={LABEL_APP_KEY}={LABEL_APP_VALUE}",
                f"label={LABEL_USER_ID}={user_id}",
                "status=running",
            ],
        )
    except ContainerPoolUnavailable:
        return 0
    return len(ids)


async def global_count() -> int:
    """Return the total number of running pi-session containers."""
    try:
        ids = await asyncio.to_thread(
            _list_containers_sync,
            [f"label={LABEL_APP_KEY}={LABEL_APP_VALUE}", "status=running"],
        )
    except ContainerPoolUnavailable:
        return 0
    return len(ids)


async def evict_oldest_for_user(user_id: str) -> Optional[str]:
    """
    Find the oldest running container for `user_id` and `docker rm -f`
    it. Returns the removed container ID (or None if there was nothing
    to evict). Called when the user is at PI_SESSION_MAX_PER_USER and
    is starting another chat.
    """
    if not user_id:
        return None

    try:
        # `--format` to get id + created timestamp; sort manually.
        rc, out, err = await asyncio.to_thread(
            _run_docker,
            "ps",
            "--filter", f"label={LABEL_APP_KEY}={LABEL_APP_VALUE}",
            "--filter", f"label={LABEL_USER_ID}={user_id}",
            "--filter", "status=running",
            "--format", "{{.ID}} {{.CreatedAt}}",
            timeout=5.0,
        )
    except ContainerPoolUnavailable:
        return None

    if rc != 0 or not out.strip():
        return None

    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            rows.append((parts[0], parts[1]))
    if not rows:
        return None

    # Format example: "abc123 2026-05-08 12:30:55 +0000 UTC"
    rows.sort(key=lambda r: r[1])
    oldest_id = rows[0][0]

    logger.info(
        "container_pool: evicting oldest container %s for user %s (over per-user cap)",
        oldest_id, user_id,
    )
    try:
        await asyncio.to_thread(_run_docker, "rm", "-f", oldest_id, timeout=10.0)
    except ContainerPoolUnavailable as exc:
        logger.warning("container_pool: evict failed: %s", exc)
        return None
    return oldest_id


async def enforce_quotas(user_id: str) -> None:
    """
    Pre-spawn quota check. Either succeeds (caller should proceed
    with PiSession.start()) or raises:

      * GlobalCapacityExceeded — VM is full; the chat WS handler
        should send a structured 429 to the SPA.

    For per-user-cap, we don't raise — we evict the user's oldest
    container instead (the user-facing experience is "your old chat
    got suspended" rather than "you can't open this chat").

    No-op when docker is unreachable (subprocess runtime fallback
    handles its own resource accounting).
    """
    try:
        total = await global_count()
    except ContainerPoolUnavailable:
        return

    if total >= PI_SESSION_MAX_GLOBAL:
        raise GlobalCapacityExceeded(
            f"VM at capacity ({total}/{PI_SESSION_MAX_GLOBAL} concurrent chats)"
        )

    user_count = await count_for_user(user_id)
    while user_count >= PI_SESSION_MAX_PER_USER:
        evicted = await evict_oldest_for_user(user_id)
        if not evicted:
            break  # nothing to evict; let the chat through anyway
        user_count -= 1
