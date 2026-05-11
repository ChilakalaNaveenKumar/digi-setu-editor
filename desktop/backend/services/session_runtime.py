"""
SessionRuntime — one-per-session host of the pi subprocess + event fanout.

Replaces the WebSocket-shaped state machine in routes/chat_ws.py with a
transport-agnostic primitive: spawn pi on demand, capture every event
into a ring buffer with monotonic ids, and let any number of consumers
(SSE streams, the partial-turn tracker, the billing pump) subscribe.

Why this exists
---------------
The old WS layer entangled two concerns:
  1. The transport (WebSocket, heartbeats, multi-tab kicks, parked-
     session bridges, exponential-backoff reconnect…)
  2. The runtime (pi process lifecycle, billing, fs/bg fanout,
     watchdog, partial-turn persistence…)

Every transport bug we shipped (the reconnect loop, "Stop pill stuck",
duplicate-tab havoc, "Connection lost" flicker) was the transport
state machine getting confused. The runtime concerns were sound.

This module owns the runtime. routes/chat_sse.py reads from it. The
WS code goes away once the SSE path is verified.

Lifecycle
---------
    rt = await SessionRuntimeRegistry.instance().acquire(
        session_id, user_id, model_id
    )
    turn_id = await rt.send_prompt("hello")
    async for ev_id, evt in rt.stream(since=0):
        ...                              # SSE writes here
    await rt.abort()                     # POST /abort
    await rt.answer_permission(pid, True)# POST /permission

The runtime is reaped automatically by a background task after
`IDLE_TIMEOUT_SECONDS` of no activity (no prompts AND no in-flight
turn). If a new prompt arrives mid-eviction the registry serialises
under a per-session asyncio.Lock so we never end up with two pi
processes for one session.

Multi-user fairness
-------------------
* Per-user concurrency cap: services/rate_limit.acquire_chat_slot is
  taken on first prompt (NOT on stream open) and released on
  runtime close. An idle user with 3 open sessions but no live pi
  burns no slots.
* Global pi-spawn rate-limit (services/rate_limit "pi.spawn"
  bucket) — a hostile client cannot crash the host by reconnecting
  in a tight loop because reconnects don't spawn pi. Only prompts do.

Resume model
------------
Each event gets a monotonically-increasing id. Clients (EventSource)
pass `Last-Event-ID` on reconnect; we replay everything after that
id from the ring. If the client's id is older than the oldest
buffered event we return a `_dropped_events` envelope so the SPA
knows it missed something (e.g. show a "history may be incomplete"
banner — same affordance you get when a chat reconnect lags too far).
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from services.error_codes import bridge_error, log_error, log_info
from services.pi_session import PiSession


# Ring buffer: drop oldest events past this many. ~1 KB avg event ×
# 1000 events ≈ 1 MB per session. With 100 active sessions that's
# 100 MB worst-case for replay buffers — comfortably under the
# 16 GB VM budget. If a turn produces >1000 events the oldest are
# dropped first; clients that lag that far see a `_dropped_events`
# marker in their stream.
RING_CAPACITY = 1000


# Idle eviction. After this many seconds with no prompt/abort/permission
# answer AND no in-flight turn the runtime is closed: pi is terminated,
# the chat slot released, the ring buffer freed. Bumping this trades
# RAM for "feels instant on next message". 10 min picked to match the
# old WS heartbeat-watchdog cadence.
IDLE_TIMEOUT_SECONDS = 10 * 60.0


# How often the reaper wakes to scan for evictable runtimes.
REAPER_TICK_SECONDS = 30.0


# Sentinel event id for "subscribed before any event was produced".
# `since=0` means "from the very beginning of this runtime's life" —
# any event id is > 0 so the first yield is guaranteed.
SENTINEL_SINCE = 0


class SessionRuntime:
    """One pi subprocess + event fanout. See module docstring."""

    def __init__(
        self,
        *,
        session_id: str,
        user_id: str,
        workspace_path: Path,
        chats_dir: Path,
        model_id: str,
        provider: Optional[str],
        permission_mode: str,
        permission_mode_file: Optional[Path],
        workspace_id: str,
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.workspace_path = workspace_path
        self.chats_dir = chats_dir
        self.model_id = model_id
        self.provider = provider
        self.permission_mode = permission_mode
        self.permission_mode_file = permission_mode_file
        self.workspace_id = workspace_id

        self._pi: Optional[PiSession] = None
        self._pi_task: Optional[asyncio.Task[None]] = None
        # Lock protects start/close races so we never spawn two pi's
        # for the same runtime even if two prompts race the first
        # `ensure_started()` call.
        self._lifecycle_lock = asyncio.Lock()
        self._closed = False

        # Ring buffer of (event_id, event). We keep insertion order
        # via deque so dropping the oldest on overflow is O(1).
        self._ring: deque[tuple[int, dict[str, Any]]] = deque(maxlen=RING_CAPACITY)
        self._next_id = 1
        self._lowest_id = 1  # smallest id still in the ring (for resume gap detection)

        # Wake all waiting `stream()` consumers when a new event lands.
        # Using an asyncio.Condition would be cleaner but Event is
        # enough here because every consumer holds its own cursor; we
        # only need a "something changed" pulse, not a "specific item".
        self._notify = asyncio.Event()

        # Last activity timestamp (any prompt, abort, permission, or
        # event from pi). Used by the reaper to decide eviction.
        self._last_active = time.monotonic()

        # In-flight turn marker — runtime won't be reaped while a turn
        # is running, even if `_last_active` is stale (e.g. a long
        # tool execution that produces no client-facing events for a
        # few minutes).
        self._in_flight = False

        # Outstanding permission requests pi has emitted but the user
        # hasn't answered yet. Stored so a reconnecting client can
        # re-render any modal without waiting for pi to repeat itself.
        self._pending_permissions: dict[str, dict[str, Any]] = {}

    # ── lifecycle ───────────────────────────────────────────────────
    async def ensure_started(self) -> None:
        """Spawn pi if it isn't running yet. Idempotent."""
        async with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError("session runtime closed")
            if self._pi is not None:
                return

            self._pi = PiSession(
                session_id=self.session_id,
                workspace_path=self.workspace_path,
                session_dir=self.chats_dir,
                model=self.model_id,
                provider=self.provider,
                permission_mode=self.permission_mode,
                permission_mode_file=self.permission_mode_file,
                user_id=self.user_id,
            )
            try:
                await self._pi.start()
            except Exception as exc:
                self._pi = None
                log_error(
                    "internal",
                    session_id=self.session_id,
                    user_id=self.user_id,
                    exc=exc,
                    where="session_runtime.start",
                )
                # Surface to any subscribed stream so the SPA can show
                # an error card instead of a silent "thinking…".
                self._enqueue(bridge_error("internal"))
                raise

            # Emit the same `_session_info` envelope the WS path used
            # so the existing frontend dispatcher doesn't notice the
            # transport change.
            self._enqueue({
                "type": "_session_info",
                "model": self.model_id,
                "model_name": self.model_id,  # caller may overwrite via patch
                "permission_mode": self.permission_mode,
                "workspace_id": self.workspace_id,
            })

            self._pi_task = asyncio.create_task(
                self._pump_pi_events(),
                name=f"pi-pump-{self.session_id}",
            )

    async def close(self) -> None:
        """Tear down pi, free the ring, wake all stream consumers."""
        async with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True

        # Cancel the pump task FIRST so it doesn't race with pi.close().
        if self._pi_task is not None:
            self._pi_task.cancel()
            try:
                await self._pi_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._pi_task = None

        if self._pi is not None:
            try:
                await self._pi.close()
            except Exception as exc:  # noqa: BLE001
                log_error(
                    "internal",
                    session_id=self.session_id,
                    user_id=self.user_id,
                    exc=exc,
                    where="session_runtime.close",
                )
            self._pi = None

        # One last pulse so any consumer mid-iteration wakes up and
        # sees `_closed` so it can exit cleanly instead of hanging.
        self._notify.set()
        self._in_flight = False

        log_info(
            "runtime_closed",
            session_id=self.session_id,
            user_id=self.user_id,
            where="session_runtime.close",
        )

    # ── client-facing actions ───────────────────────────────────────
    async def send_prompt(self, message: str, *, request_id: Optional[str] = None) -> str:
        """Forward a user prompt to pi. Spawns pi if needed.

        Returns the request id we tagged the prompt with — clients
        can use it to correlate the assistant turn that follows.
        """
        await self.ensure_started()
        assert self._pi is not None
        rid = request_id or f"req-{int(time.time() * 1000)}"
        self._touch()
        self._in_flight = True
        await self._pi.send({
            "type": "prompt",
            "id": rid,
            "message": message,
        })
        return rid

    async def abort(self) -> None:
        """Tell pi to abandon the current turn.

        We don't kill pi — abort is in-protocol; pi receives the
        signal, drops the in-flight tool execution, and emits its
        own `agent_end`. The runtime stays alive for the next prompt.
        """
        if self._pi is None:
            return
        self._touch()
        try:
            await self._pi.send({"type": "abort"})
        except Exception as exc:  # noqa: BLE001
            log_error(
                "internal",
                session_id=self.session_id,
                user_id=self.user_id,
                exc=exc,
                where="session_runtime.abort",
            )

    async def answer_permission(self, prompt_id: str, granted: bool) -> bool:
        """Forward the user's allow/deny click for a tool call.

        Returns True iff the prompt id was actually outstanding (so
        the route can 404 on stale ids). pi will emit the proper
        tool_execution_end / blocked envelope based on this answer.
        """
        if self._pi is None:
            return False
        rec = self._pending_permissions.pop(prompt_id, None)
        if rec is None:
            return False
        self._touch()
        await self._pi.send({
            "type": "permission_response",
            "id": prompt_id,
            "granted": granted,
        })
        return True

    # ── event subscription ──────────────────────────────────────────
    async def stream(
        self,
        *,
        since: int = SENTINEL_SINCE,
    ) -> AsyncIterator[tuple[int, dict[str, Any]]]:
        """Yield (id, event) tuples in order, starting after `since`.

        Blocks (without busy-waiting) when caught up. Returns when
        the runtime is closed.

        Resume gap handling: if `since` is older than the oldest
        event still in the ring we yield a synthetic `_dropped_events`
        envelope first so the client knows there was a gap.
        """
        # Replay phase: if the caller is behind the oldest buffered
        # event, tell them up front; then catch them up to head.
        if since > 0 and since < self._lowest_id - 1:
            yield (
                self._next_id,  # use next id so resume on this one is consistent
                {
                    "type": "_dropped_events",
                    "from": since,
                    "to": self._lowest_id - 1,
                },
            )
        # First flush any backlog newer than `since`.
        for ev_id, evt in list(self._ring):
            if ev_id > since:
                yield (ev_id, evt)
                since = ev_id

        # Then live-tail.
        while not self._closed:
            self._notify.clear()
            # If new events came in between the backlog flush and
            # clear() we'd miss them — guard by re-checking.
            if self._ring and self._ring[-1][0] > since:
                for ev_id, evt in list(self._ring):
                    if ev_id > since:
                        yield (ev_id, evt)
                        since = ev_id
                continue
            try:
                await asyncio.wait_for(self._notify.wait(), timeout=20.0)
            except asyncio.TimeoutError:
                # Timeout exists so SSE writers can emit a keep-alive
                # comment line on iOS Safari (which kills idle SSE
                # after ~30s). The route handler decides what to do
                # with the silent tick.
                continue

    # ── internal: pi → ring pump ────────────────────────────────────
    async def _pump_pi_events(self) -> None:
        """Drain pi.events() into the ring buffer. Runs as a background task."""
        assert self._pi is not None
        try:
            async for evt in self._pi.events():
                self._touch()
                # Track in-flight turn boundaries so the reaper
                # doesn't kill pi mid-stream.
                t = evt.get("type")
                if t in ("agent_start", "turn_start"):
                    self._in_flight = True
                elif t in ("agent_end", "turn_end"):
                    self._in_flight = False
                elif t == "permission_request":
                    pid = str(evt.get("id") or "")
                    if pid:
                        self._pending_permissions[pid] = dict(evt)

                self._enqueue(evt)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log_error(
                "internal",
                session_id=self.session_id,
                user_id=self.user_id,
                exc=exc,
                where="session_runtime.pump",
            )
            self._enqueue(bridge_error("internal"))
        finally:
            # Pi exited (clean shutdown OR crash). Surface an end-
            # of-stream marker so consumers can re-fetch history /
            # show a "session ended" affordance.
            self._enqueue({"type": "_runtime_ended"})

    # ── internal helpers ────────────────────────────────────────────
    def _enqueue(self, evt: dict[str, Any]) -> None:
        """Append an event to the ring and pulse waiters."""
        if self._closed:
            return
        ev_id = self._next_id
        self._next_id += 1
        if len(self._ring) == RING_CAPACITY:
            # Track the new lowest id when we drop the oldest.
            dropped_id, _ = self._ring[0]
            self._lowest_id = dropped_id + 1
        self._ring.append((ev_id, evt))
        self._notify.set()

    def _touch(self) -> None:
        self._last_active = time.monotonic()

    # Reaper introspection — public so the registry's reaper can call.
    def is_idle(self, now: float) -> bool:
        if self._in_flight:
            return False
        if self._pi is None:
            # Runtime that never started yet should reap quickly.
            return now - self._last_active > IDLE_TIMEOUT_SECONDS
        return now - self._last_active > IDLE_TIMEOUT_SECONDS


class SessionRuntimeRegistry:
    """Process-singleton registry of live SessionRuntimes.

    Single uvicorn worker by design (mirrors the existing assumption
    in services/session_locks.py). If we ever scale out, swap this
    for a Redis SETEX with the worker id and route SSE streams to
    the worker that owns the runtime.
    """

    def __init__(self) -> None:
        self._runtimes: dict[str, SessionRuntime] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: Optional[asyncio.Task[None]] = None

    async def start_reaper(self) -> None:
        """Idempotent — safe to call from app startup."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(
                self._reaper_loop(),
                name="session-runtime-reaper",
            )

    async def stop_reaper(self) -> None:
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._reaper_task = None

    async def acquire(
        self,
        *,
        session_id: str,
        user_id: str,
        workspace_path: Path,
        chats_dir: Path,
        model_id: str,
        provider: Optional[str],
        permission_mode: str,
        permission_mode_file: Optional[Path],
        workspace_id: str,
    ) -> SessionRuntime:
        """Return the existing runtime for this session, or build a fresh one.

        Does NOT spawn pi yet — call rt.ensure_started() / rt.send_prompt()
        for that. Cheap to call from a stream subscriber that just
        wants to read events.
        """
        async with self._lock:
            existing = self._runtimes.get(session_id)
            if existing is not None and not existing._closed:
                return existing
            rt = SessionRuntime(
                session_id=session_id,
                user_id=user_id,
                workspace_path=workspace_path,
                chats_dir=chats_dir,
                model_id=model_id,
                provider=provider,
                permission_mode=permission_mode,
                permission_mode_file=permission_mode_file,
                workspace_id=workspace_id,
            )
            self._runtimes[session_id] = rt
            return rt

    def get(self, session_id: str) -> Optional[SessionRuntime]:
        rt = self._runtimes.get(session_id)
        if rt is None or rt._closed:
            return None
        return rt

    async def evict(self, session_id: str) -> None:
        async with self._lock:
            rt = self._runtimes.pop(session_id, None)
        if rt is not None:
            await rt.close()

    def active_count(self) -> int:
        """For /admin/load + capacity dashboards."""
        return sum(1 for rt in self._runtimes.values() if not rt._closed)

    async def _reaper_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(REAPER_TICK_SECONDS)
                now = time.monotonic()
                # Snapshot to avoid mutating while iterating.
                victims = [
                    sid
                    for sid, rt in list(self._runtimes.items())
                    if rt.is_idle(now)
                ]
                for sid in victims:
                    print(
                        f"[session_runtime_reaper] evicting idle session {sid}",
                        file=sys.stderr,
                    )
                    await self.evict(sid)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            print(
                f"[session_runtime_reaper] crashed: {exc!r} — restarting",
                file=sys.stderr,
            )
            # Self-restart so a transient bug doesn't permanently
            # leak runtimes.
            self._reaper_task = asyncio.create_task(self._reaper_loop())


_singleton: Optional[SessionRuntimeRegistry] = None


def session_runtime_registry() -> SessionRuntimeRegistry:
    global _singleton
    if _singleton is None:
        _singleton = SessionRuntimeRegistry()
    return _singleton
