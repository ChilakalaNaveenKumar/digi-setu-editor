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

The observer scope is the **sandbox parent** (`workspace_path` itself),
NOT just the user-files subdir (`workspace_path / "workspace/"`). This
matters because pi runs with cwd `/workspace` (the sandbox parent in
docker mode) and AGENTS.md / past chat history sometimes nudge the
agent toward absolute paths like `/workspace/test-binaries/foo` —
which land at `<sandbox>/test-binaries/foo` on host, OUTSIDE the
user-files dir. With this watcher scope:

    1. Writes inside `workspace/` ── emit normally with the rel path
       inside the user-files dir (existing behavior).
    2. Writes to agent-metadata files (.pi, AGENTS.md, extensions/,
       guides/, node_modules/, package.json) ── ignored via
       `should_ignore`.
    3. Stray writes (anything else under `workspace_path`) ── the
       file/dir is RELOCATED into `<workspace_path>/workspace/<rel>`
       and a back-symlink is left at the original path so the AI's
       subsequent reads still resolve. The synthetic `created` event
       is emitted with the new (workspace/-relative) path so the
       file tree refreshes.

The relocate-on-stray strategy means the file tree is always the
authoritative view: the disk wins. The AI can use any path under
`/workspace`; whatever lands there ends up visible to the user
without code changes on the agent side.
"""

from __future__ import annotations

import asyncio
import os
import queue
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from services.paths import should_ignore, ws_root


# Names that live at the SANDBOX PARENT level (not inside `workspace/`)
# but are agent-metadata symlinks installed by registry._wire_sandbox_symlinks.
# Any watch event whose top-level component matches one of these is
# silently dropped — they're implementation detail, never user files.
# `.pi` is covered separately by `should_ignore`'s leading-dot rule.
_SANDBOX_AGENT_METADATA = {
    "AGENTS.md",
    "package.json",
    "extensions",
    "guides",
    "node_modules",
}

# The single subdir under the sandbox that IS the user-files dir.
# Anything outside this subdir but inside sandbox parent is a stray
# write candidate for relocation.
_USER_FILES_SUBDIR = "workspace"


def _is_agent_metadata(top_level_name: str) -> bool:
    """Top-level entries in the sandbox parent that are agent metadata
    (symlinks created at workspace bootstrap) — ignored by the
    watcher and never relocated."""
    if top_level_name in _SANDBOX_AGENT_METADATA:
        return True
    # Hidden files / dirs (most importantly `.pi`).
    if top_level_name.startswith(".") and top_level_name not in (".", ".."):
        return True
    return False


class _Handler(FileSystemEventHandler):
    """
    Watchdog runs in its own thread; this handler is sync. It posts raw
    events (with absolute src paths) to a thread-safe queue. The
    WorkspaceWatcher's async pump does the path classification +
    stray relocation on the asyncio loop so we don't block watchdog's
    callback thread on disk I/O.
    """

    def __init__(self, raw_queue: queue.Queue) -> None:
        super().__init__()
        self._raw_queue = raw_queue

    def _post(self, kind: str, event: FileSystemEvent, src: str | None = None) -> None:
        payload: dict = {
            "kind": kind,
            "abs_path": str(event.src_path),
            "is_dir": bool(event.is_directory),
        }
        if src is not None:
            payload["abs_src"] = str(src)
        self._raw_queue.put(payload)

    def on_created(self, event: FileSystemEvent) -> None:
        self._post("created", event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._post("modified", event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._post("deleted", event)

    def on_moved(self, event: FileSystemEvent) -> None:
        new_event = FileSystemEvent(event.dest_path)  # type: ignore[arg-type]
        new_event.is_directory = event.is_directory  # type: ignore[attr-defined]
        self._post("moved", new_event, src=event.src_path)


class WorkspaceWatcher:
    """
    Owns one watchdog observer over a single workspace's SANDBOX PARENT
    directory (not just the user-files subdir; see module docstring).
    Subscribers receive batched fs_change messages on an asyncio.Queue.
    Lifecycle is managed by WatcherRegistry — don't construct directly.
    """

    DEBOUNCE_SECS = 0.08

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = Path(workspace_path)
        self._user_root = ws_root(self.workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self._user_root.mkdir(parents=True, exist_ok=True)
        # Pre-resolve so `_classify` can do a fast string-prefix
        # comparison without per-event resolve(). macOS in particular
        # routes events through `/private/var/...` even when the dir
        # was opened as `/var/...` (symlink); without normalising on
        # both sides every classify call would fall through to
        # "ignore" and the file tree would never refresh on dev
        # laptops.
        self._workspace_path_resolved = self.workspace_path.resolve()
        self._user_root_resolved = self._user_root.resolve()

        self._raw_queue: queue.Queue = queue.Queue()
        self._subscribers: Set[asyncio.Queue] = set()
        self._observer: Observer | None = None  # type: ignore[type-arg]
        self._pump_task: asyncio.Task | None = None
        self._started = False
        self._refcount = 0

        # Track stray top-level paths we've already relocated within
        # this watcher's lifetime. After relocation we leave a symlink
        # at the original path so the AI's reads still work; subsequent
        # watchdog events for paths inside that symlink loop back to
        # the user-files dir and we don't want to re-relocate them.
        self._relocated_stray_tops: Set[str] = set()
        self._relocated_lock = threading.Lock()

    async def ensure_started(self) -> None:
        if self._started:
            return
        self._started = True

        # Sweep any pre-existing strays from prior chats (before this
        # fix was deployed, or before the watcher was started this
        # session). Doing it BEFORE starting the observer means we
        # don't race against our own move events.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._initial_relocation_sweep)

        # Watch the SANDBOX PARENT recursively. This is the source-of-
        # truth scope: anything pi (or its bash subprocesses) writes
        # anywhere in the sandbox is captured here, including stray
        # absolute /workspace/foo writes that historically slipped
        # past the old (workspace/-only) watcher.
        observer = Observer()
        observer.schedule(
            _Handler(self._raw_queue),
            str(self.workspace_path),
            recursive=True,
        )
        observer.daemon = True
        observer.start()
        self._observer = observer

        self._pump_task = asyncio.create_task(
            self._pump_loop(),
            name=f"fswatcher-pump[{self.workspace_path.name}]",
        )
        print(
            f"[fswatcher] started observer for ws={self.workspace_path.name} root={self.workspace_path}",
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

    # ── path classification + stray relocation ────────────────────────────
    def _classify(self, abs_path: str) -> tuple[str, str | None]:
        """Return ``("user", rel)`` for paths inside the user-files dir
        (rel is the path relative to ``workspace/``), ``("stray", rel)``
        for paths outside ``workspace/`` but still inside the sandbox
        parent that should be relocated, or ``("ignore", None)`` for
        agent-metadata paths and anything outside the sandbox.

        Compares against the **resolved** sandbox path so symlink
        prefixes (most importantly macOS `/var` → `/private/var`)
        don't cause every event to be classified as outside-sandbox
        and silently dropped.
        """
        try:
            # `os.path.realpath` is faster than `Path.resolve` and
            # doesn't stat each component (important for very chatty
            # node_modules-style traffic). We don't need the path to
            # currently exist — it might already be deleted by the
            # time we classify the event.
            real = Path(os.path.realpath(abs_path))
            sandbox = self._workspace_path_resolved
            try:
                rel_to_sandbox = real.relative_to(sandbox).as_posix()
            except ValueError:
                # Outside sandbox entirely (shouldn't happen — observer
                # scope is sandbox itself, but be defensive).
                return ("ignore", None)
        except (ValueError, OSError):
            return ("ignore", None)

        if rel_to_sandbox in (".", ""):
            return ("ignore", None)

        top = rel_to_sandbox.split("/", 1)[0]

        if _is_agent_metadata(top):
            return ("ignore", None)

        if top == _USER_FILES_SUBDIR:
            # Inside `workspace/` — strip the subdir from the rel path.
            inner = rel_to_sandbox[len(_USER_FILES_SUBDIR) :].lstrip("/")
            if not inner:
                return ("ignore", None)
            if should_ignore(inner):
                return ("ignore", None)
            return ("user", inner)

        # Stray write: top-level entry in sandbox that isn't `workspace/`
        # and isn't agent metadata. The pump will relocate it into
        # `workspace/<top>/...` so it shows up in the user's tree.
        if should_ignore(rel_to_sandbox):
            return ("ignore", None)
        return ("stray", rel_to_sandbox)

    def _relocate_stray_top(self, top_name: str) -> bool:
        """Move the stray top-level entry ``<sandbox>/<top_name>`` into
        ``<sandbox>/workspace/<top_name>`` and leave a symlink at the
        original path so the AI's subsequent reads still resolve to
        the same content.

        Idempotent: tracks already-relocated tops and skips repeat
        attempts. Returns ``True`` if anything was moved this call.

        Best-effort: any failure (target exists, permission denied,
        symlink-create race) is logged but doesn't propagate. The
        watcher will still emit the synthetic events with the
        workspace/-relative path; if the move silently failed the
        client will get an event for a file that isn't where the
        path says it is. Better than dropping the event entirely.
        """
        with self._relocated_lock:
            if top_name in self._relocated_stray_tops:
                return False

        src = self.workspace_path / top_name
        if not src.exists() and not src.is_symlink():
            # Already moved by an earlier event in the same batch, OR
            # the AI deleted it before we got here. Either way: nothing
            # to do.
            with self._relocated_lock:
                self._relocated_stray_tops.add(top_name)
            return False

        # If src is already a symlink (e.g. from a previous relocation
        # in a prior session that crashed mid-cleanup), assume it
        # points at the right place and just remember the migration.
        if src.is_symlink():
            with self._relocated_lock:
                self._relocated_stray_tops.add(top_name)
            return False

        target = self._user_root / top_name

        try:
            self._user_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(
                f"[fswatcher] relocate: mkdir user_root failed: {exc}",
                file=sys.stderr,
            )
            return False

        # If the target already exists, MERGE non-conflicting children
        # into it instead of clobbering. This handles the case where
        # the AI wrote BOTH `/workspace/test-binaries/a` AND
        # `/workspace/workspace/test-binaries/b` (rare, but possible
        # mid-conversation as the AI's path style drifts).
        if target.exists() or target.is_symlink():
            self._merge_into_existing(src, target)
        else:
            try:
                shutil.move(str(src), str(target))
            except (OSError, shutil.Error) as exc:
                print(
                    f"[fswatcher] relocate: move {src} -> {target} failed: {exc}",
                    file=sys.stderr,
                )
                return False

        # Leave a symlink at the original sandbox-parent path so any
        # bash command holding an open path-relative reference (e.g.
        # `cat /workspace/test-binaries/foo`) keeps working. The
        # symlink target is RELATIVE so it survives container path
        # remapping — `/workspace/test-binaries -> workspace/test-binaries`
        # inside the docker container resolves to
        # `/workspace/workspace/test-binaries` which is the relocated
        # data.
        try:
            os.symlink(f"{_USER_FILES_SUBDIR}/{top_name}", src)
        except FileExistsError:
            # Race: something recreated the path between our move and
            # the symlink. Log + skip — the move already succeeded so
            # files are visible in the tree.
            pass
        except OSError as exc:
            print(
                f"[fswatcher] relocate: symlink {src} -> {_USER_FILES_SUBDIR}/{top_name} failed: {exc}",
                file=sys.stderr,
            )

        with self._relocated_lock:
            self._relocated_stray_tops.add(top_name)
        print(
            f"[fswatcher] relocated stray {top_name} -> workspace/{top_name} "
            f"(ws={self.workspace_path.name})",
            file=sys.stderr,
        )
        return True

    def _initial_relocation_sweep(self) -> None:
        """Scan the sandbox parent for existing strays and relocate
        them. Called once at watcher startup so old workspaces (where
        prior chats wrote outside `workspace/`) get cleaned up the
        first time the user opens them after this fix ships.

        Cheap — one shallow `iterdir` of the sandbox parent. Per-stray
        cost is one rename + one symlink. No-op for fresh workspaces.
        """
        try:
            entries = list(self.workspace_path.iterdir())
        except OSError as exc:
            print(
                f"[fswatcher] initial sweep: iterdir failed: {exc}",
                file=sys.stderr,
            )
            return
        for entry in entries:
            name = entry.name
            if name == _USER_FILES_SUBDIR:
                continue
            if _is_agent_metadata(name):
                continue
            # Skip if it's already a symlink (probably a previous
            # relocation's back-symlink).
            if entry.is_symlink():
                with self._relocated_lock:
                    self._relocated_stray_tops.add(name)
                continue
            self._relocate_stray_top(name)

    def _merge_into_existing(self, src: Path, target: Path) -> None:
        """Move children of ``src`` into ``target``, preserving any
        existing files in ``target``. Used when both stray-write
        and proper paths created the same top-level dir name."""
        if not src.is_dir():
            # Stray is a file but target dir already has the same
            # name as a dir — give up and rename the stray with a
            # `.stray` suffix so it's still visible.
            try:
                rescue = self._user_root / f"{src.name}.stray-{int(time.time())}"
                shutil.move(str(src), str(rescue))
            except (OSError, shutil.Error) as exc:
                print(
                    f"[fswatcher] merge fallback: rescue {src} failed: {exc}",
                    file=sys.stderr,
                )
            return
        for child in src.iterdir():
            dest = target / child.name
            if dest.exists() or dest.is_symlink():
                continue  # respect existing
            try:
                shutil.move(str(child), str(dest))
            except (OSError, shutil.Error) as exc:
                print(
                    f"[fswatcher] merge: move {child} -> {dest} failed: {exc}",
                    file=sys.stderr,
                )
        # Clean up the now-empty src.
        try:
            src.rmdir()
        except OSError:
            pass

    # ── pump ──────────────────────────────────────────────────────────────
    async def _pump_loop(self) -> None:
        """Bridge thread queue → debounced fan-out to async subscribers.

        Per-batch flow:
            1. Drain the raw queue with a short debounce window.
            2. Classify each event (`user` / `stray` / `ignore`).
            3. For strays, synchronously relocate the top-level entry
               into the user-files dir (idempotent per top, per
               watcher lifetime).
            4. Emit a single fs_change payload listing every visible
               event, with paths relative to the user-files dir.
        """
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

            # Pre-pass: collect stray tops we need to relocate. Doing
            # this in one go (vs. inline per event) means a single
            # bash command writing many files inside one stray dir
            # only triggers one mv + one symlink, not N.
            stray_tops_to_relocate: list[str] = []
            seen_tops: Set[str] = set()
            for ev in batch:
                cls, rel = self._classify(ev["abs_path"])
                if cls == "stray" and rel is not None:
                    top = rel.split("/", 1)[0]
                    if top in seen_tops:
                        continue
                    seen_tops.add(top)
                    with self._relocated_lock:
                        if top in self._relocated_stray_tops:
                            continue
                    stray_tops_to_relocate.append(top)

            for top in stray_tops_to_relocate:
                # Run the relocate on the executor so a slow disk
                # doesn't block the asyncio loop.
                await loop.run_in_executor(None, self._relocate_stray_top, top)

            # Now classify a SECOND time after relocation: stray paths
            # have been turned into user paths via the back-symlink, so
            # the rebased rel path is what we want to emit. This means
            # the frontend always sees `workspace/`-relative paths and
            # never has to know about the relocation machinery.
            seen: dict[tuple[str, str], dict] = {}
            for ev in batch:
                cls, rel = self._classify(ev["abs_path"])
                if cls == "ignore" or rel is None:
                    continue
                if cls == "stray":
                    # After relocation, the abs_path no longer exists
                    # at the original location (it's a symlink there).
                    # The "real" path is now under workspace/. Strip
                    # the original top from rel and prepend workspace/-
                    # relative form to make it look like a normal
                    # write inside the user-files dir.
                    rebased = rel  # `rel` is already the path relative to sandbox parent
                    # rel here is e.g. "test-binaries/foo.bin"; that
                    # IS the path inside the user-files dir post-
                    # relocation (we moved <sandbox>/test-binaries to
                    # <sandbox>/workspace/test-binaries).
                    payload = {
                        "kind": ev["kind"],
                        "path": rebased,
                        "is_dir": bool(ev["is_dir"]),
                    }
                else:
                    # cls == "user"
                    payload = {
                        "kind": ev["kind"],
                        "path": rel,
                        "is_dir": bool(ev["is_dir"]),
                    }
                src_abs = ev.get("abs_src")
                if src_abs is not None:
                    src_cls, src_rel = self._classify(src_abs)
                    if src_cls != "ignore" and src_rel is not None:
                        payload["src"] = src_rel
                key = (payload["path"], payload["kind"])
                seen[key] = payload

            if not seen:
                continue

            payload_envelope = {"type": "fs_change", "events": list(seen.values())}

            stale = []
            for sub in self._subscribers:
                try:
                    sub.put_nowait(payload_envelope)
                except asyncio.QueueFull:
                    stale.append(sub)
            for s in stale:
                self._subscribers.discard(s)


class WatcherRegistry:
    """
    Owns one WorkspaceWatcher per active workspace. Ref-counted: when the
    last subscriber releases it, the observer thread tears down.

    Leak guarantees:
      1. ``acquire`` returns a watcher whose refcount has been bumped.
         If ``ensure_started`` raises, the bump is rolled back BEFORE
         the exception propagates, so the caller never has to remember
         to call ``release`` on a half-baked acquire.
      2. ``release`` is idempotent for a workspace that has already
         hit refcount=0 (no-op rather than double-stop).
      3. The optional reaper task evicts watchers whose refcount has
         been zero for ``REAPER_GRACE_SECS``. This is belt-and-braces
         for the (already covered by the SessionRuntime reaper) case
         where a caller forgets to release on a crash path — the
         observer thread doesn't outlive the SessionRuntime that
         owned it by more than ``REAPER_GRACE_SECS``. Threshold
         logging fires if live count exceeds ``LIVE_WARN_THRESHOLD``
         so we can spot runaway growth in production.
    """

    LIVE_WARN_THRESHOLD = 200
    REAPER_TICK_SECS = 30.0
    REAPER_GRACE_SECS = 60.0

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
        # Tracks zero-refcount watchers and the monotonic timestamp
        # they hit zero. The reaper evicts entries older than
        # REAPER_GRACE_SECS — gives a short window for a
        # rapidly-reconnecting client to re-acquire without
        # tearing down the observer thread.
        self._zero_since: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: asyncio.Task | None = None
        self._last_warned_count = 0

    @staticmethod
    def _key(workspace_path: Path) -> str:
        return str(Path(workspace_path).resolve())

    async def start_reaper(self) -> None:
        """Idempotent. Call from app lifespan startup."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(
                self._reaper_loop(),
                name="fswatcher-reaper",
            )

    async def stop_reaper(self) -> None:
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except (asyncio.CancelledError, Exception):
                pass
            self._reaper_task = None

    def stats(self) -> dict[str, int]:
        """Snapshot for /admin/load + dashboards."""
        live = sum(1 for w in self._watchers.values() if w._started)
        return {
            "registered": len(self._watchers),
            "live": live,
            "zero_refcount_pending": len(self._zero_since),
            "total_subscribers": sum(len(w._subscribers) for w in self._watchers.values()),
        }

    async def acquire(self, workspace_path: Path) -> WorkspaceWatcher:
        """Bump refcount + return a started watcher.

        On ``ensure_started`` failure the refcount bump is rolled
        back so the caller never holds a leaked reference.
        """
        key = self._key(workspace_path)
        async with self._lock:
            w = self._watchers.get(key)
            if w is None:
                w = WorkspaceWatcher(workspace_path)
                self._watchers[key] = w
            w._refcount += 1
            # Cancel any pending grace-period eviction.
            self._zero_since.pop(key, None)
            self._maybe_warn_live_count_locked()
        try:
            await w.ensure_started()
        except Exception:
            # Roll back the refcount + remove the entry if no other
            # caller is racing. We do NOT call w.stop() because
            # ensure_started failed before the observer was scheduled
            # (or it raised after partial setup; w.stop() is itself
            # tolerant of a partially-started watcher).
            async with self._lock:
                w._refcount = max(0, w._refcount - 1)
                if w._refcount == 0:
                    self._watchers.pop(key, None)
                    self._zero_since.pop(key, None)
            try:
                await w.stop()
            except Exception:  # noqa: BLE001
                pass
            raise
        return w

    async def release(self, workspace_path: Path) -> None:
        key = self._key(workspace_path)
        to_stop: WorkspaceWatcher | None = None
        async with self._lock:
            w = self._watchers.get(key)
            if w is None:
                return
            w._refcount = max(0, w._refcount - 1)
            if w._refcount > 0:
                return
            # Don't stop immediately — give a short grace window so
            # a tab refresh / quick reconnect doesn't tear down +
            # rebuild the observer thread for the same workspace.
            # The reaper will evict after REAPER_GRACE_SECS.
            self._zero_since[key] = time.monotonic()
            # If the reaper is not running (unit tests, dev), fall
            # back to immediate stop.
            if self._reaper_task is None or self._reaper_task.done():
                self._watchers.pop(key, None)
                self._zero_since.pop(key, None)
                to_stop = w
        if to_stop is not None:
            await to_stop.stop()

    def _maybe_warn_live_count_locked(self) -> None:
        """Print a stderr warning the first time we cross the
        threshold (and again on each doubling above it). Cheap signal
        for ops that something has stopped releasing watchers."""
        live = len(self._watchers)
        if live < self.LIVE_WARN_THRESHOLD:
            self._last_warned_count = 0
            return
        if live >= max(self._last_warned_count * 2, self.LIVE_WARN_THRESHOLD):
            print(
                f"[fswatcher] WARN: registered watcher count = {live} "
                f"(threshold {self.LIVE_WARN_THRESHOLD}). Possible leak.",
                file=sys.stderr,
            )
            self._last_warned_count = live

    async def _reaper_loop(self) -> None:
        """Evict watchers that have been idle for ``REAPER_GRACE_SECS``."""
        try:
            while True:
                await asyncio.sleep(self.REAPER_TICK_SECS)
                now = time.monotonic()
                to_stop: list[WorkspaceWatcher] = []
                async with self._lock:
                    expired_keys = [
                        k for k, t in self._zero_since.items()
                        if now - t > self.REAPER_GRACE_SECS
                    ]
                    for k in expired_keys:
                        w = self._watchers.pop(k, None)
                        self._zero_since.pop(k, None)
                        if w is not None:
                            to_stop.append(w)
                for w in to_stop:
                    try:
                        await w.stop()
                    except Exception as exc:  # noqa: BLE001
                        print(
                            f"[fswatcher-reaper] stop failed for {w.workspace_path.name}: {exc}",
                            file=sys.stderr,
                        )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            print(
                f"[fswatcher-reaper] crashed: {exc!r} — restarting",
                file=sys.stderr,
            )
            # Self-restart so a transient bug doesn't permanently
            # block grace-period evictions.
            self._reaper_task = asyncio.create_task(
                self._reaper_loop(),
                name="fswatcher-reaper",
            )
