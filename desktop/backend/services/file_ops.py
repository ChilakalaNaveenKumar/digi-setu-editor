"""
File-system operations on a workspace's user-files dir.

All public helpers take an explicit `workspace_path` and resolve paths
relative to `<workspace_path>/workspace/`. Path safety is enforced via
`paths.safe_path`, which rejects absolute paths, `..` traversal, and
symlink-out attempts before any I/O happens.

These helpers are pure (no global state, no observer); the watcher in
`file_watcher.py` is responsible for emitting fs_change events when these
mutations land on disk.
"""

from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path

from services.paths import (
    classify_extension,
    safe_path,
    should_ignore,
    unique_dest,
    ws_root,
)


# ── tree listing ─────────────────────────────────────────────────────────
def list_tree(workspace_path: Path) -> list[dict]:
    """
    Flat list of (rel posix path, is_dir, size, mtime) for everything inside
    a workspace's user-files dir. Frontend builds the visual tree.
    """
    items: list[dict] = []
    root = ws_root(workspace_path)
    if not root.exists():
        return items
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if should_ignore(rel):
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


# ── reads ────────────────────────────────────────────────────────────────
def read_file(workspace_path: Path, rel_path: str, max_bytes: int = 2 * 1024 * 1024) -> dict:
    """
    Read a file from a workspace. Returns metadata + content for text files,
    metadata only for previewable binary kinds (image/pdf/audio/video) — the
    UI fetches those via `stream_raw_path` to avoid base64 round-trips.
    """
    abs_path = safe_path(workspace_path, rel_path)
    if not abs_path.exists():
        raise FileNotFoundError(rel_path)
    if abs_path.is_dir():
        raise IsADirectoryError(rel_path)

    size = abs_path.stat().st_size
    kind = classify_extension(abs_path.name)

    if kind in ("image", "pdf", "audio", "video", "office"):
        return {
            "path": rel_path,
            "size": size,
            "kind": kind,
            "binary": True,
            "truncated": False,
            "content": "",
        }
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


def stream_raw_path(workspace_path: Path, rel_path: str) -> tuple[Path, str]:
    """Resolve absolute path + mime for streaming raw bytes via FileResponse."""
    abs_path = safe_path(workspace_path, rel_path)
    if not abs_path.exists():
        raise FileNotFoundError(rel_path)
    if abs_path.is_dir():
        raise IsADirectoryError(rel_path)
    mime, _ = mimetypes.guess_type(abs_path.name)
    if not mime:
        kind = classify_extension(abs_path.name)
        mime = {
            "image": "application/octet-stream",
            "pdf": "application/pdf",
            "svg": "image/svg+xml",
            "audio": "audio/mpeg",
            "video": "video/mp4",
        }.get(kind, "application/octet-stream")
    return abs_path, mime


# ── mutations ────────────────────────────────────────────────────────────
def create_file(workspace_path: Path, rel_path: str, content: str = "", overwrite: bool = False) -> dict:
    if not rel_path or rel_path.endswith("/"):
        raise ValueError("path must be a non-empty file path")
    abs_path = safe_path(workspace_path, rel_path)
    if abs_path.exists() and not overwrite:
        raise FileExistsError(rel_path)
    if abs_path.exists() and abs_path.is_dir():
        raise IsADirectoryError(rel_path)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    stat = abs_path.stat()
    return {"path": rel_path, "is_dir": False, "size": int(stat.st_size), "mtime": float(stat.st_mtime)}


def create_folder(workspace_path: Path, rel_path: str) -> dict:
    if not rel_path:
        raise ValueError("path must be non-empty")
    abs_path = safe_path(workspace_path, rel_path)
    if abs_path.exists() and not abs_path.is_dir():
        raise FileExistsError(rel_path)
    abs_path.mkdir(parents=True, exist_ok=True)
    stat = abs_path.stat()
    return {"path": rel_path, "is_dir": True, "size": 0, "mtime": float(stat.st_mtime)}


def delete_path(workspace_path: Path, rel_path: str) -> dict:
    abs_path = safe_path(workspace_path, rel_path)
    if not abs_path.exists():
        raise FileNotFoundError(rel_path)
    if abs_path.is_dir():
        if abs_path.resolve() == ws_root(workspace_path).resolve():
            raise PermissionError("refusing to delete workspace root")
        shutil.rmtree(abs_path)
        return {"path": rel_path, "deleted": True, "is_dir": True}
    abs_path.unlink()
    return {"path": rel_path, "deleted": True, "is_dir": False}


def rename_path(workspace_path: Path, from_rel: str, to_rel: str) -> dict:
    src = safe_path(workspace_path, from_rel)
    dst = safe_path(workspace_path, to_rel)
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


def copy_path(workspace_path: Path, from_rel: str, to_rel: str | None = None) -> dict:
    src = safe_path(workspace_path, from_rel)
    if not src.exists():
        raise FileNotFoundError(from_rel)
    if to_rel is None:
        dst = unique_dest(src.parent / src.name)
    else:
        dst = safe_path(workspace_path, to_rel)
        if dst.exists() and dst.is_dir():
            dst = unique_dest(dst / src.name)
        elif dst.exists():
            dst = unique_dest(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    rel = dst.resolve().relative_to(ws_root(workspace_path).resolve()).as_posix()
    stat = dst.stat()
    return {
        "path": rel,
        "old_path": from_rel,
        "is_dir": dst.is_dir(),
        "size": int(stat.st_size) if dst.is_file() else 0,
        "mtime": float(stat.st_mtime),
    }


def move_path(workspace_path: Path, from_rel: str, to_rel: str) -> dict:
    src = safe_path(workspace_path, from_rel)
    if not src.exists():
        raise FileNotFoundError(from_rel)
    dst = safe_path(workspace_path, to_rel)
    if dst.exists() and dst.is_dir():
        dst = unique_dest(dst / src.name)
    elif dst.exists():
        dst = unique_dest(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    rel = dst.resolve().relative_to(ws_root(workspace_path).resolve()).as_posix()
    stat = dst.stat()
    return {
        "path": rel,
        "old_path": from_rel,
        "is_dir": dst.is_dir(),
        "size": int(stat.st_size) if dst.is_file() else 0,
        "mtime": float(stat.st_mtime),
    }
