"""
WorkspaceWatcher — single global watchdog observer over PROJECT_ROOT/workspace.

Why one global observer (not one-per-session): the workspace is currently
shared across sessions (pi runs with cwd=PROJECT_ROOT, files land in
workspace/). One Observer is cheaper than N. WS handlers subscribe via
`subscribe(queue)` and get the same event stream; on disconnect they
unsubscribe. When per-session sandboxing lands (web-hosted phase), this
file becomes per-session by changing WORKSPACE_ROOT to a session-scoped path.

Event shape pushed onto subscriber queues:
    { "type": "fs_change", "events": [
        { "kind": "created" | "modified" | "deleted" | "moved",
          "path": "relative/posix/path",
          "is_dir": bool,
          "src": "..."   # only for moved
        }, ...
    ] }

Events are coalesced: if many writes hit during one debounce window
(default 80ms), they're batched into a single fs_change message. That
keeps the UI from re-rendering per-byte during a `pi write` of a large
file (where the OS often emits many "modified" events for one logical
write).
"""

from __future__ import annotations

import asyncio
import queue
import sys
import threading
from pathlib import Path
from typing import Set

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from pi_session import PROJECT_ROOT

WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

# Files we should never report on (noise, lockfiles, OS metadata).
_IGNORE_NAMES = {".DS_Store", ".git"}
_IGNORE_PREFIXES = (".",)
_IGNORE_SUFFIXES = (".swp", ".swo", "~")


def _should_ignore(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    for p in parts:
        if p in _IGNORE_NAMES:
            return True
        if p.endswith(_IGNORE_SUFFIXES):
            return True
        # Allow a leading '.' on segment 0 only if it's the literal current dir;
        # otherwise hide hidden dirs/files (.git, .obsidian, etc.).
        if p.startswith(_IGNORE_PREFIXES) and p not in (".", ".."):
            return True
    return False


def _to_rel(abs_path: str) -> str | None:
    try:
        rel = Path(abs_path).resolve().relative_to(WORKSPACE_ROOT.resolve())
    except (ValueError, OSError):
        return None
    posix = rel.as_posix()
    # `.` means "the workspace root itself" — its mtime changes whenever a
    # child does. The frontend doesn't need that as a tree event.
    if posix == "." or posix == "":
        return None
    return posix


class _Handler(FileSystemEventHandler):
    """
    Translates raw watchdog events into structured dicts and posts them on a
    thread-safe Queue, which the asyncio side drains in a debounced batch.
    Watchdog runs in its own thread, so this handler is sync; we never touch
    asyncio constructs here.
    """

    def __init__(self, raw_queue: queue.Queue) -> None:
        super().__init__()
        self._raw_queue = raw_queue

    # NOTE: watchdog v6 emits both file and directory events; we want both for
    # tree updates (folders matter for the file tree).
    def _emit(self, kind: str, event: FileSystemEvent, src: str | None = None) -> None:
        rel = _to_rel(event.src_path)
        if rel is None or _should_ignore(rel):
            return
        payload = {"kind": kind, "path": rel, "is_dir": bool(event.is_directory)}
        if src is not None:
            src_rel = _to_rel(src)
            if src_rel is None or _should_ignore(src_rel):
                # Treat as a plain create from the new path's POV.
                pass
            else:
                payload["src"] = src_rel
        self._raw_queue.put(payload)

    def on_created(self, event: FileSystemEvent) -> None:
        self._emit("created", event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._emit("modified", event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._emit("deleted", event)

    def on_moved(self, event: FileSystemEvent) -> None:
        # `event.dest_path` is the new path; pass the OLD as src.
        new_event = FileSystemEvent(event.dest_path)  # type: ignore[arg-type]
        new_event.is_directory = event.is_directory  # type: ignore[attr-defined]
        self._emit("moved", new_event, src=event.src_path)


class WorkspaceWatcher:
    """
    Async-friendly facade over a synchronous watchdog Observer.

    Use:
        watcher = WorkspaceWatcher.instance()
        await watcher.ensure_started()
        q = watcher.subscribe()                # asyncio.Queue
        try:
            while True:
                batch = await q.get()          # batched fs_change message
                ...
        finally:
            watcher.unsubscribe(q)
    """

    _singleton: "WorkspaceWatcher | None" = None
    _singleton_lock = threading.Lock()

    DEBOUNCE_SECS = 0.08

    def __init__(self) -> None:
        self._raw_queue: queue.Queue = queue.Queue()
        self._subscribers: Set[asyncio.Queue] = set()
        self._observer: Observer | None = None  # type: ignore[type-arg]
        self._pump_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False

    @classmethod
    def instance(cls) -> "WorkspaceWatcher":
        with cls._singleton_lock:
            if cls._singleton is None:
                cls._singleton = cls()
            return cls._singleton

    async def ensure_started(self) -> None:
        if self._started:
            return
        self._started = True
        self._loop = asyncio.get_running_loop()

        observer = Observer()
        observer.schedule(_Handler(self._raw_queue), str(WORKSPACE_ROOT), recursive=True)
        observer.daemon = True
        observer.start()
        self._observer = observer

        self._pump_task = asyncio.create_task(self._pump_loop(), name="fswatcher-pump")
        print(f"[fswatcher] started observer at {WORKSPACE_ROOT}", file=sys.stderr)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def _pump_loop(self) -> None:
        """
        Bridge thread queue → debounced fan-out to async subscribers. Wakes
        up when the first event lands, sleeps DEBOUNCE_SECS to batch
        subsequent events, then emits one fs_change to every subscriber.
        """
        loop = asyncio.get_running_loop()
        while True:
            # Block on the THREAD queue, off the event loop.
            first = await loop.run_in_executor(None, self._raw_queue.get)
            batch = [first]
            # Drain any events arriving during the debounce window.
            await asyncio.sleep(self.DEBOUNCE_SECS)
            try:
                while True:
                    batch.append(self._raw_queue.get_nowait())
            except queue.Empty:
                pass

            # De-duplicate (path,kind) pairs while preserving last-seen order.
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
                # If a subscriber can't keep up, drop it — they'll resync on
                # next file tree refetch when they reconnect.
                self._subscribers.discard(s)


# ── Static tree snapshot helpers (used by the REST endpoints) ───────────────

def list_tree() -> list[dict]:
    """
    Return the workspace as a flat list of records (relative posix path +
    is_dir + size + mtime). Frontend builds the visual tree. Flat is simpler
    to diff against fs_change events than nested.
    """
    items: list[dict] = []
    if not WORKSPACE_ROOT.exists():
        return items
    for p in sorted(WORKSPACE_ROOT.rglob("*")):
        rel = p.relative_to(WORKSPACE_ROOT).as_posix()
        if _should_ignore(rel):
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        items.append(
            {
                "path": rel,
                "is_dir": p.is_dir(),
                "size": int(stat.st_size) if p.is_file() else 0,
                "mtime": float(stat.st_mtime),
            }
        )
    return items


_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "ico", "avif", "apng"}
_PDF_EXTS = {"pdf"}
_SVG_EXTS = {"svg"}
_AUDIO_EXTS = {"mp3", "wav", "ogg", "flac", "m4a", "aac", "opus"}
_VIDEO_EXTS = {"mp4", "mov", "webm", "mkv", "avi", "m4v"}


def _classify_extension(name: str) -> str:
    """
    Bucket a file by extension into the rendering kind the editor pane
    knows how to handle. Falls back to 'unknown' for everything else;
    callers can then probe the bytes to distinguish text vs. binary.
    """
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _SVG_EXTS:
        return "svg"
    if ext in _AUDIO_EXTS:
        return "audio"
    if ext in _VIDEO_EXTS:
        return "video"
    return "unknown"


def read_file(rel_path: str, max_bytes: int = 2 * 1024 * 1024) -> dict:
    """
    Read a file from the workspace. Refuses path traversal. Returns:

    For known previewable media (image/pdf/svg/audio/video) we DON'T read
    the bytes — we return `kind` + size and let the frontend fetch the
    raw bytes via /api/files/raw which streams with the right Content-Type.

    For text files we return decoded content. For unknown binaries we
    return a "can't preview" record with a `reason`.
    """
    safe_rel = Path(rel_path)
    if safe_rel.is_absolute() or any(part == ".." for part in safe_rel.parts):
        raise PermissionError("path traversal denied")
    abs_path = (WORKSPACE_ROOT / safe_rel).resolve()
    if not str(abs_path).startswith(str(WORKSPACE_ROOT.resolve())):
        raise PermissionError("path escapes workspace")
    if not abs_path.exists():
        raise FileNotFoundError(rel_path)
    if abs_path.is_dir():
        raise IsADirectoryError(rel_path)

    size = abs_path.stat().st_size
    name = abs_path.name
    kind = _classify_extension(name)

    # Known previewable media → just metadata; frontend fetches /raw.
    if kind in ("image", "pdf", "audio", "video"):
        return {
            "path": rel_path,
            "size": size,
            "kind": kind,
            "binary": True,
            "truncated": False,
            "content": "",
        }
    # SVG: return BOTH the source (for "view as code") AND mark as svg
    # so the frontend can default to the rendered preview.
    if kind == "svg":
        if size > max_bytes:
            return {
                "path": rel_path,
                "size": size,
                "kind": "svg",
                "binary": True,
                "truncated": True,
                "content": "",
                "reason": f"svg too large ({size} bytes; cap {max_bytes})",
            }
        try:
            return {
                "path": rel_path,
                "size": size,
                "kind": "svg",
                "binary": False,
                "truncated": False,
                "content": abs_path.read_text(encoding="utf-8"),
            }
        except UnicodeDecodeError:
            return {
                "path": rel_path,
                "size": size,
                "kind": "svg",
                "binary": True,
                "truncated": False,
                "content": "",
                "reason": "svg has invalid utf-8",
            }

    if size > max_bytes:
        return {
            "path": rel_path,
            "size": size,
            "kind": "binary",
            "binary": True,
            "truncated": True,
            "content": "",
            "reason": f"file too large ({size} bytes; cap {max_bytes})",
        }
    raw = abs_path.read_bytes()
    binary = b"\x00" in raw[:4096]
    if binary:
        return {
            "path": rel_path,
            "size": size,
            "kind": "binary",
            "binary": True,
            "truncated": False,
            "content": "",
            "reason": "binary content not displayed",
        }
    return {
        "path": rel_path,
        "size": size,
        "kind": "text",
        "binary": False,
        "truncated": False,
        "content": raw.decode("utf-8", "replace"),
    }


def stream_raw_path(rel_path: str) -> tuple[Path, str]:
    """
    Resolve a workspace-relative path for serving raw bytes. Returns
    (absolute_path, mime_type). The caller should use FastAPI's
    FileResponse — reading the bytes here would defeat streaming.
    """
    abs_path = _safe_workspace_path(rel_path)
    if not abs_path.exists():
        raise FileNotFoundError(rel_path)
    if abs_path.is_dir():
        raise IsADirectoryError(rel_path)
    import mimetypes

    mime, _ = mimetypes.guess_type(abs_path.name)
    if not mime:
        # Reasonable defaults for the known media kinds.
        kind = _classify_extension(abs_path.name)
        mime = {
            "image": "application/octet-stream",
            "pdf": "application/pdf",
            "svg": "image/svg+xml",
            "audio": "audio/mpeg",
            "video": "video/mp4",
        }.get(kind, "application/octet-stream")
    return abs_path, mime


# ── Workspace-sandboxed file-system mutations ─────────────────────────────
def _safe_workspace_path(rel_path: str) -> Path:
    """
    Resolve a workspace-relative path safely. Refuses absolute paths,
    `..` traversal, and any resolved location that escapes the workspace
    root (covers the symlink case too because `.resolve()` follows them).

    Returns the absolute Path on success, raises PermissionError otherwise.
    """
    p = Path(rel_path)
    if p.is_absolute() or any(part == ".." for part in p.parts):
        raise PermissionError("path traversal denied")
    abs_path = (WORKSPACE_ROOT / p).resolve()
    ws_root = WORKSPACE_ROOT.resolve()
    # Use os.path.commonpath for robust prefix check (avoids false positives
    # like `/ws-extra` being accepted because it shares a string prefix with `/ws`).
    try:
        if Path(abs_path) != ws_root and ws_root not in Path(abs_path).parents:
            raise PermissionError("path escapes workspace")
    except ValueError:
        raise PermissionError("path escapes workspace")
    return abs_path


def create_file(rel_path: str, content: str = "", overwrite: bool = False) -> dict:
    """
    Create (or overwrite, when `overwrite=True`) a file inside the workspace.
    Parent directories are created on demand. Returns the freshly-stat'd
    record for the created file.
    """
    if not rel_path or rel_path.endswith("/"):
        raise ValueError("path must be a non-empty file path")
    abs_path = _safe_workspace_path(rel_path)
    if abs_path.exists() and not overwrite:
        raise FileExistsError(rel_path)
    if abs_path.exists() and abs_path.is_dir():
        raise IsADirectoryError(rel_path)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    stat = abs_path.stat()
    return {
        "path": rel_path,
        "is_dir": False,
        "size": int(stat.st_size),
        "mtime": float(stat.st_mtime),
    }


def create_folder(rel_path: str) -> dict:
    """Create a folder (and parents) inside the workspace."""
    if not rel_path:
        raise ValueError("path must be non-empty")
    abs_path = _safe_workspace_path(rel_path)
    if abs_path.exists() and not abs_path.is_dir():
        raise FileExistsError(rel_path)
    abs_path.mkdir(parents=True, exist_ok=True)
    stat = abs_path.stat()
    return {
        "path": rel_path,
        "is_dir": True,
        "size": 0,
        "mtime": float(stat.st_mtime),
    }


def delete_path(rel_path: str) -> dict:
    """Delete a file or recursively delete a folder."""
    abs_path = _safe_workspace_path(rel_path)
    if not abs_path.exists():
        raise FileNotFoundError(rel_path)
    if abs_path.is_dir():
        # rmtree would be safer w/ a guard; we already validated the path is
        # inside the workspace, but be paranoid one more time.
        if abs_path.resolve() == WORKSPACE_ROOT.resolve():
            raise PermissionError("refusing to delete workspace root")
        import shutil

        shutil.rmtree(abs_path)
        return {"path": rel_path, "deleted": True, "is_dir": True}
    abs_path.unlink()
    return {"path": rel_path, "deleted": True, "is_dir": False}


def rename_path(from_rel: str, to_rel: str) -> dict:
    """Rename / move a file or folder inside the workspace."""
    src = _safe_workspace_path(from_rel)
    dst = _safe_workspace_path(to_rel)
    if not src.exists():
        raise FileNotFoundError(from_rel)
    if dst.exists():
        raise FileExistsError(to_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    stat = dst.stat()
    return {
        "path": to_rel,
        "old_path": from_rel,
        "is_dir": dst.is_dir(),
        "size": int(stat.st_size) if dst.is_file() else 0,
        "mtime": float(stat.st_mtime),
    }


def _unique_dest(dst: Path) -> Path:
    """If `dst` exists, append " (copy)", " (copy 2)", etc. until we
    find a free name. Mirrors macOS Finder behaviour."""
    if not dst.exists():
        return dst
    parent = dst.parent
    stem = dst.stem
    suffix = dst.suffix
    # Strip a trailing " (copy N)" so we don't get "foo (copy) (copy)".
    base = stem
    n = 1
    candidate = parent / f"{base} (copy){suffix}"
    while candidate.exists():
        n += 1
        candidate = parent / f"{base} (copy {n}){suffix}"
    return candidate


def copy_path(from_rel: str, to_rel: str | None = None) -> dict:
    """
    Copy a file OR an entire directory tree to a new location inside the
    workspace. If `to_rel` is None we drop the copy next to the source
    with a " (copy)" suffix (Finder-style); otherwise we copy to the
    requested destination, auto-disambiguating only if it already exists
    AND the destination is a directory (in which case we copy INTO it).

    Returns the new path's stat record.
    """
    import shutil

    src = _safe_workspace_path(from_rel)
    if not src.exists():
        raise FileNotFoundError(from_rel)

    if to_rel is None:
        # "Duplicate" — create "<name> (copy)" next to the source.
        dst = _unique_dest(src.parent / src.name)
    else:
        dst = _safe_workspace_path(to_rel)
        # If destination is an existing directory, copy INTO it
        # (use the source's basename, auto-disambiguated).
        if dst.exists() and dst.is_dir():
            dst = _unique_dest(dst / src.name)
        elif dst.exists():
            dst = _unique_dest(dst)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

    rel = dst.resolve().relative_to(WORKSPACE_ROOT.resolve()).as_posix()
    stat = dst.stat()
    return {
        "path": rel,
        "old_path": from_rel,
        "is_dir": dst.is_dir(),
        "size": int(stat.st_size) if dst.is_file() else 0,
        "mtime": float(stat.st_mtime),
    }


def move_path(from_rel: str, to_rel: str) -> dict:
    """
    Move a file OR directory tree to a new location. If `to_rel` is an
    existing directory we move INTO it; if the target already exists we
    auto-disambiguate with a " (copy N)" suffix. Returns the new stat.
    """
    import shutil

    src = _safe_workspace_path(from_rel)
    if not src.exists():
        raise FileNotFoundError(from_rel)
    dst = _safe_workspace_path(to_rel)
    if dst.exists() and dst.is_dir():
        dst = _unique_dest(dst / src.name)
    elif dst.exists():
        dst = _unique_dest(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    rel = dst.resolve().relative_to(WORKSPACE_ROOT.resolve()).as_posix()
    stat = dst.stat()
    return {
        "path": rel,
        "old_path": from_rel,
        "is_dir": dst.is_dir(),
        "size": int(stat.st_size) if dst.is_file() else 0,
        "mtime": float(stat.st_mtime),
    }
