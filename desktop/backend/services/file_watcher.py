"""
WorkspaceWatcher — per-workspace watchdog observer.

One observer thread per active workspace. Spun up the first time a WS
connection holds it open (refcount = 1) and torn down when the last
connection releases it (refcount = 0). This keeps the observer footprint
proportional to the number of active sessions, not the number of
registered workspaces.

Public surface (used by routes/chat_ws.py):

    WatcherRegistry.instance()
        .acquire(workspace_path)   → WorkspaceWatcher (started, refcount += 1)
        .release(workspace_path)   → refcount -= 1, stop observer if 0

    WorkspaceWatcher
        .subscribe()               → asyncio.Queue of fs_change batches
        .unsubscribe(q)
"""

from __future__ import annotations

import asyncio
import queue
import sys
import threading
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from services.paths import should_ignore, to_rel, ws_root


class _Handler(FileSystemEventHandler):
    """
    Watchdog runs in its own thread; this handler is sync. It posts raw
    events to a thread-safe queue; the WorkspaceWatcher's async pump
    debounces and fans them out to subscribers on the event loop.
    """

    def __init__(self, raw_queue: queue.Queue, root: Path) -> None:
        super().__init__()
        self._raw_queue = raw_queue
        self._root = root

    def _emit(self, kind: str, event: FileSystemEvent, src: str | None = None) -> None:
        rel = to_rel(event.src_path, self._root)
        if rel is None or should_ignore(rel):
            return
        payload = {"kind": kind, "path": rel, "is_dir": bool(event.is_directory)}
        if src is not None:
            src_rel = to_rel(src, self._root)
            if src_rel is not None and not should_ignore(src_rel):
                payload["src"] = src_rel
        self._raw_queue.put(payload)

    def on_created(self, event: FileSystemEvent) -> None:
        self._emit("created", event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._emit("modified", event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._emit("deleted", event)

    def on_moved(self, event: FileSystemEvent) -> None:
        new_event = FileSystemEvent(event.dest_path)  # type: ignore[arg-type]
        new_event.is_directory = event.is_directory  # type: ignore[attr-defined]
        self._emit("moved", new_event, src=event.src_path)


class WorkspaceWatcher:
    """
    Owns one watchdog observer over a single workspace's user-files dir.
    Subscribers receive batched fs_change messages on an asyncio.Queue.
    Lifecycle is managed by WatcherRegistry — don't construct directly.
    """

    DEBOUNCE_SECS = 0.08

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = Path(workspace_path)
        self._root = ws_root(self.workspace_path)
        self._root.mkdir(parents=True, exist_ok=True)

        self._raw_queue: queue.Queue = queue.Queue()
        self._subscribers: Set[asyncio.Queue] = set()
        self._observer: Observer | None = None  # type: ignore[type-arg]
        self._pump_task: asyncio.Task | None = None
        self._started = False
        self._refcount = 0

    async def ensure_started(self) -> None:
        if self._started:
            return
        self._started = True

        observer = Observer()
        observer.schedule(_Handler(self._raw_queue, self._root), str(self._root), recursive=True)
        observer.daemon = True
        observer.start()
        self._observer = observer

        self._pump_task = asyncio.create_task(
            self._pump_loop(),
            name=f"fswatcher-pump[{self.workspace_path.name}]",
        )
        print(
            f"[fswatcher] started observer for ws={self.workspace_path.name} root={self._root}",
            file=sys.stderr,
        )

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False

        if self._pump_task and not self._pump_task.done():
            self._pump_task.cancel()
            try:
                await self._pump_task
            except (asyncio.CancelledError, Exception):
                pass
            self._pump_task = None

        obs = self._observer
        self._observer = None
        if obs is not None:
            try:
                obs.stop()
                obs.join(timeout=2.0)
            except Exception as exc:
                print(
                    f"[fswatcher] observer stop failed for {self.workspace_path.name}: {exc}",
                    file=sys.stderr,
                )
        print(f"[fswatcher] stopped observer for ws={self.workspace_path.name}", file=sys.stderr)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def _pump_loop(self) -> None:
        """Bridge thread queue → debounced fan-out to async subscribers."""
        loop = asyncio.get_running_loop()
        while True:
            first = await loop.run_in_executor(None, self._raw_queue.get)
            batch = [first]
            await asyncio.sleep(self.DEBOUNCE_SECS)
            try:
                while True:
                    batch.append(self._raw_queue.get_nowait())
            except queue.Empty:
                pass

            seen: dict[tuple[str, str], dict] = {}
            for ev in batch:
                key = (ev["path"], ev["kind"])
                seen[key] = ev
            payload = {"type": "fs_change", "events": list(seen.values())}

            stale = []
            for sub in self._subscribers:
                try:
                    sub.put_nowait(payload)
                except asyncio.QueueFull:
                    stale.append(sub)
            for s in stale:
                self._subscribers.discard(s)


class WatcherRegistry:
    """
    Owns one WorkspaceWatcher per active workspace. Ref-counted: when the
    last WS connection releases it, the observer thread tears down.
    """

    _singleton: "WatcherRegistry | None" = None
    _singleton_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "WatcherRegistry":
        with cls._singleton_lock:
            if cls._singleton is None:
                cls._singleton = cls()
            return cls._singleton

    def __init__(self) -> None:
        self._watchers: dict[str, WorkspaceWatcher] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(workspace_path: Path) -> str:
        return str(Path(workspace_path).resolve())

    async def acquire(self, workspace_path: Path) -> WorkspaceWatcher:
        key = self._key(workspace_path)
        async with self._lock:
            w = self._watchers.get(key)
            if w is None:
                w = WorkspaceWatcher(workspace_path)
                self._watchers[key] = w
            w._refcount += 1
        await w.ensure_started()
        return w

    async def release(self, workspace_path: Path) -> None:
        key = self._key(workspace_path)
        async with self._lock:
            w = self._watchers.get(key)
            if w is None:
                return
            w._refcount = max(0, w._refcount - 1)
            if w._refcount > 0:
                return
            del self._watchers[key]
        await w.stop()
