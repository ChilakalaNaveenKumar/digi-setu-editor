"""
bg_processes — track @aliou/pi-processes background sessions and stream
their on-disk log files to subscribed WebSockets.

@aliou/pi-processes (the LLM tool) appends every byte written by spawned
daemons to per-process files under /tmp/pi-processes-<ts>/. Our backend
catches the `process(action: "start")` tool result, harvests the file
paths + pid, then opens an asyncio polling tailer that pushes each new
chunk of bytes to the per-WS queue as a `bg_output` event. The frontend
reconstructs the live terminal feed without burning any LLM tokens.

Event shapes published to subscribers:

    { "type": "bg_started",
      "process": { id, name, command, pid, stdoutFile, stderrFile, startTime } }

    { "type": "bg_output",
      "id": "<process id>",
      "stream": "stdout" | "stderr",
      "chunk": "<bytes since last poll, utf-8 with backslashreplace>" }

    { "type": "bg_ended",
      "id": "<process id>",
      "exitCode": int | null,
      "status": "exited" | "killed" | "terminate_timeout" }

The kill REST endpoint (`POST /api/bg/{id}/kill`) sends SIGTERM to the
pid directly — no LLM round-trip. We escalate to SIGKILL after a 5s
grace period if the process is still alive.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Polling interval for tailing log files. 100ms matches the extension's own
# `notifyOutputChanged` throttle (manager.ts:84) so we never busy-spin yet
# we feel "live" to the human eye.
_TAIL_POLL_MS = 100

# Liveness check interval for spawned daemons. Cheap (just kill -0).
_LIVENESS_POLL_S = 1.0


class _ProcessRecord:
    """One tracked background process. Owns its tailer task lifecycle."""

    __slots__ = (
        "id",
        "name",
        "command",
        "pid",
        "stdout_file",
        "stderr_file",
        "start_time",
        "end_time",
        "exit_code",
        "status",
        "_stdout_offset",
        "_stderr_offset",
        "_task",
        "_subscribers",
    )

    def __init__(
        self,
        *,
        id: str,
        name: str,
        command: str,
        pid: int,
        stdout_file: str,
        stderr_file: str,
        start_time: float,
    ) -> None:
        self.id = id
        self.name = name
        self.command = command
        self.pid = pid
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.start_time = start_time
        self.end_time: Optional[float] = None
        self.exit_code: Optional[int] = None
        self.status: str = "running"
        self._stdout_offset = 0
        self._stderr_offset = 0
        self._task: Optional[asyncio.Task[None]] = None
        self._subscribers: Set[asyncio.Queue[Dict[str, Any]]] = set()

    def info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "pid": self.pid,
            "stdoutFile": self.stdout_file,
            "stderrFile": self.stderr_file,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "exitCode": self.exit_code,
            "status": self.status,
        }


class BackgroundProcessRegistry:
    """
    Per-workspace bg-process catalogue.

    Scope: one instance per workspace (resolve via BackgroundProcessHub).
    The previous global singleton leaked processes across workspaces — a
    `bg_started` for workspace A would be broadcast to every connected
    chat in workspace B, and `POST /api/bg/{id}/kill` from one workspace
    could kill another's process. This class is now strictly local.

    Concurrency model: every public method is called from the asyncio loop
    (FastAPI WS handler). Tailer tasks run on the same loop. No thread
    crossings — no locking needed.
    """

    def __init__(self) -> None:
        self._records: Dict[str, _ProcessRecord] = {}
        self._subscribers: Set[asyncio.Queue[Dict[str, Any]]] = set()

    @classmethod
    def instance(cls) -> "BackgroundProcessRegistry":
        """Deprecated. Use BackgroundProcessHub.for_workspace(wsid) instead.

        Kept only so any leftover call sites fail loud at runtime when they
        try to use a process-wide registry that no longer exists.
        """
        raise RuntimeError(
            "BackgroundProcessRegistry is now per-workspace; "
            "use BackgroundProcessHub.for_workspace(wsid)."
        )

    # ── subscriptions ────────────────────────────────────────────
    def subscribe(self) -> asyncio.Queue[Dict[str, Any]]:
        """A new WS connection = a new subscriber queue."""
        q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    def _broadcast(self, msg: Dict[str, Any]) -> None:
        # Fan out to all subscribers. Drop on backpressure (queues are unbounded
        # by default, so this only matters if a subscriber stops draining).
        for q in self._subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    # ── catalog ──────────────────────────────────────────────────
    def list(self) -> List[Dict[str, Any]]:
        return [r.info() for r in self._records.values()]

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        r = self._records.get(id)
        return r.info() if r else None

    # ── public: register a process from a tool-result event ──────
    def register_from_start_result(
        self, details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Called when a `process(action: "start")` tool succeeds. Reads the
        process dict the extension echoed back (see start.ts:111 — every
        field on `ProcessInfo`), starts a tailer, and broadcasts
        `bg_started`. Returns the process info if registration succeeded,
        None if the payload was malformed.
        """
        proc = details.get("process") or {}
        pid = proc.get("pid")
        pid_int: Optional[int]
        if isinstance(pid, int):
            pid_int = pid
        elif isinstance(pid, str) and pid.isdigit():
            pid_int = int(pid)
        else:
            pid_int = None

        pid_value = pid_int if pid_int is not None else 0

        rec_id = proc.get("id")
        stdout_file = proc.get("stdoutFile")
        stderr_file = proc.get("stderrFile")
        if not isinstance(rec_id, str) or not rec_id:
            return None
        if not isinstance(stdout_file, str) or not isinstance(stderr_file, str):
            return None

        # Idempotent — second start with same id (shouldn't happen, but a safety
        # net for re-tracking on reconnects) reuses the existing record.
        existing = self._records.get(rec_id)
        if existing:
            return existing.info()

        rec = _ProcessRecord(
            id=rec_id,
            name=str(proc.get("name") or rec_id),
            command=str(proc.get("command") or ""),
            pid=pid_value,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            start_time=float(proc.get("startTime") or time.time() * 1000),
        )
        self._records[rec_id] = rec
        rec._task = asyncio.create_task(
            self._tail_loop(rec), name=f"bg-tailer[{rec_id}]"
        )
        self._broadcast({"type": "bg_started", "process": rec.info()})
        return rec.info()

    # ── public: react to a `process(action: "kill")` or "process_ended" event
    def mark_ended_from_result(self, details: Dict[str, Any]) -> None:
        """
        Called on successful `process(action: "kill")` or whenever the
        extension sends back updated process info that says exited/killed.
        Updates our local record + broadcasts `bg_ended`. The tailer task
        notices via its own liveness polling and self-cancels too.
        """
        proc = details.get("process") or {}
        rec_id = proc.get("id")
        if not isinstance(rec_id, str):
            return
        rec = self._records.get(rec_id)
        if not rec or rec.status != "running":
            return
        status = proc.get("status")
        if isinstance(status, str):
            rec.status = status
        if rec.status == "running":
            return
        rec.exit_code = proc.get("exitCode") if isinstance(proc.get("exitCode"), int) else None
        rec.end_time = time.time() * 1000
        self._broadcast(
            {
                "type": "bg_ended",
                "id": rec.id,
                "exitCode": rec.exit_code,
                "status": rec.status,
            }
        )

    # ── public: REST kill (SIGTERM the pid directly, no LLM in the loop) ──
    async def kill(self, id: str, *, grace_seconds: float = 5.0) -> Dict[str, Any]:
        rec = self._records.get(id)
        if not rec:
            return {"ok": False, "reason": "not_found"}
        if rec.status != "running":
            return {"ok": True, "reason": "already_ended", "status": rec.status}
        if rec.pid <= 0:
            return {"ok": False, "reason": "no_pid"}

        # Send SIGTERM to the process group (extension spawns each daemon as
        # the leader of its own group on Unix, see manager.ts pid==pgid note).
        try:
            os.killpg(rec.pid, signal.SIGTERM)
        except ProcessLookupError:
            # Already gone — let the tailer's liveness loop clean up.
            return {"ok": True, "reason": "already_dead"}
        except PermissionError as exc:
            return {"ok": False, "reason": "permission", "detail": str(exc)}
        except OSError:
            # Fall back to single-process kill (e.g. group lookup failed).
            try:
                os.kill(rec.pid, signal.SIGTERM)
            except ProcessLookupError:
                return {"ok": True, "reason": "already_dead"}

        # Escalate after the grace period if it's still alive.
        deadline = time.monotonic() + grace_seconds
        while time.monotonic() < deadline:
            await asyncio.sleep(0.2)
            if not _is_alive(rec.pid):
                rec.status = "killed"
                rec.end_time = time.time() * 1000
                self._broadcast(
                    {
                        "type": "bg_ended",
                        "id": rec.id,
                        "exitCode": None,
                        "status": "killed",
                    }
                )
                return {"ok": True, "reason": "sigterm"}

        try:
            os.killpg(rec.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            try:
                os.kill(rec.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        rec.status = "killed"
        rec.end_time = time.time() * 1000
        self._broadcast(
            {
                "type": "bg_ended",
                "id": rec.id,
                "exitCode": None,
                "status": "killed",
            }
        )
        return {"ok": True, "reason": "sigkill"}

    # ── internal: tailer loop ────────────────────────────────────
    async def _tail_loop(self, rec: _ProcessRecord) -> None:
        """
        Poll-tail the two log files. Every iteration we:
          1. Drain whatever new bytes have been appended to either file.
          2. Broadcast each chunk as a `bg_output` event.
          3. Check if the pid is still alive; if not, broadcast `bg_ended`
             and exit.

        We don't use inotify/kqueue because (a) the files might not exist
        for a few hundred ms after spawn (extension touches them lazily —
        manager.ts:196), and (b) polling at 100ms is plenty for a
        human-perceived "live" feed and survives missed FS events.
        """
        liveness_deadline = time.monotonic()
        try:
            while True:
                await asyncio.sleep(_TAIL_POLL_MS / 1000)

                # Drain stdout + stderr.
                stdout_chunk = self._read_appended(rec.stdout_file, "stdout", rec)
                if stdout_chunk:
                    self._broadcast(
                        {
                            "type": "bg_output",
                            "id": rec.id,
                            "stream": "stdout",
                            "chunk": stdout_chunk,
                        }
                    )
                stderr_chunk = self._read_appended(rec.stderr_file, "stderr", rec)
                if stderr_chunk:
                    self._broadcast(
                        {
                            "type": "bg_output",
                            "id": rec.id,
                            "stream": "stderr",
                            "chunk": stderr_chunk,
                        }
                    )

                # Liveness check (cheap — once per second is plenty).
                now = time.monotonic()
                if now >= liveness_deadline:
                    liveness_deadline = now + _LIVENESS_POLL_S
                    if rec.pid > 0 and not _is_alive(rec.pid):
                        # Final drain to grab the very last bytes before exit.
                        for stream in ("stdout", "stderr"):
                            path = rec.stdout_file if stream == "stdout" else rec.stderr_file
                            tail = self._read_appended(path, stream, rec)
                            if tail:
                                self._broadcast(
                                    {
                                        "type": "bg_output",
                                        "id": rec.id,
                                        "stream": stream,
                                        "chunk": tail,
                                    }
                                )
                        if rec.status == "running":
                            rec.status = "exited"
                            rec.end_time = time.time() * 1000
                            self._broadcast(
                                {
                                    "type": "bg_ended",
                                    "id": rec.id,
                                    "exitCode": None,
                                    "status": "exited",
                                }
                            )
                        return
        except asyncio.CancelledError:
            return
        except Exception as exc:
            print(
                f"[bg_processes] tailer for {rec.id} crashed: {exc}",
                file=sys.stderr,
            )

    def _read_appended(
        self, path: str, stream: str, rec: _ProcessRecord
    ) -> str:
        """Read everything appended to `path` since the last poll."""
        try:
            st = os.stat(path)
        except FileNotFoundError:
            return ""
        size = st.st_size
        offset = rec._stdout_offset if stream == "stdout" else rec._stderr_offset
        if size <= offset:
            return ""
        try:
            with open(path, "rb") as fh:
                fh.seek(offset)
                buf = fh.read(size - offset)
        except OSError:
            return ""
        if stream == "stdout":
            rec._stdout_offset = size
        else:
            rec._stderr_offset = size
        # The extension already strips ANSI on the way out for tool results,
        # but the on-disk files keep it (manager.ts:247 writes raw `data`).
        # We hand the bytes to the frontend verbatim and let it decide.
        return buf.decode("utf-8", errors="backslashreplace")


def _is_alive(pid: int) -> bool:
    """signal-0 probe; works even if we don't own the process."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — still "alive".
        return True
    return True


class BackgroundProcessHub:
    """Process-wide directory of per-workspace BackgroundProcessRegistry
    instances.

    Resolution is by workspace id (string). The first call for a given id
    lazily allocates a registry; subsequent calls reuse it. We never garbage
    collect — bg processes outlive a single chat connection on purpose,
    and a workspace is a long-lived concept.
    """

    _instance: Optional["BackgroundProcessHub"] = None

    def __init__(self) -> None:
        self._registries: Dict[str, BackgroundProcessRegistry] = {}

    @classmethod
    def instance(cls) -> "BackgroundProcessHub":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def for_workspace(self, workspace_id: str) -> BackgroundProcessRegistry:
        reg = self._registries.get(workspace_id)
        if reg is None:
            reg = BackgroundProcessRegistry()
            self._registries[workspace_id] = reg
        return reg

    def drop_workspace(self, workspace_id: str) -> None:
        """Forget a workspace's registry (called on workspace delete).
        Records inside are not actively killed — the workspace deletion
        elsewhere already kills the sandbox."""
        self._registries.pop(workspace_id, None)
