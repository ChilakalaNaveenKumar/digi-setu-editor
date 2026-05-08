"""
Shared path conventions and safety helpers for everything that touches a
workspace's user-files directory.

A "workspace" looks like:

    web/data/workspaces/<wsid>/        ← the agent's cwd
      workspace/                       ← user files (the only thing the UI sees)
      .pi/        → symlink            ← agent config (read by pi)
      extensions/ → symlink            ← agent tools
      guides/     → symlink            ← agent docs
      AGENTS.md   → symlink            ← agent instructions
      package.json → symlink           ← agent extension manifest

The agent writes inside `workspace/`. All path-safety boundaries enforced
here are anchored to `<workspace_path>/workspace/`, so traversal attempts
(`..`, absolute paths, symlink-out) get rejected before any I/O happens.

This module is dependency-free (stdlib only) so both the watcher and the
file-ops helpers can import it without forming cycles.
"""

from __future__ import annotations

from pathlib import Path

# Subdir the agent uses for its files (`AGENTS.md` tells it to write here).
WORKSPACE_SUBDIR = "workspace"


def ws_root(workspace_path: Path) -> Path:
    """Resolve the user-visible files root inside a workspace folder."""
    return Path(workspace_path) / WORKSPACE_SUBDIR


# ── ignore lists ──────────────────────────────────────────────────────────
_IGNORE_NAMES = {".DS_Store", ".git"}
_IGNORE_PREFIXES = (".",)
_IGNORE_SUFFIXES = (".swp", ".swo", "~")


def should_ignore(rel_path: str) -> bool:
    """True for OS junk and editor swap files we hide from the UI."""
    parts = Path(rel_path).parts
    for p in parts:
        if p in _IGNORE_NAMES:
            return True
        if p.endswith(_IGNORE_SUFFIXES):
            return True
        if p.startswith(_IGNORE_PREFIXES) and p not in (".", ".."):
            return True
    return False


def to_rel(abs_path: str, root: Path) -> str | None:
    """Make an absolute path workspace-relative, or None if outside root."""
    try:
        rel = Path(abs_path).resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    posix = rel.as_posix()
    if posix == "." or posix == "":
        return None
    return posix


def safe_path(workspace_path: Path, rel_path: str) -> Path:
    """
    Resolve a workspace-relative path and refuse anything that escapes the
    workspace's user-files dir. Catches `..` traversal AND symlink-out
    (because `.resolve()` follows symlinks).

    Returns the resolved absolute path on success; raises PermissionError
    on any traversal attempt.
    """
    p = Path(rel_path)
    if p.is_absolute() or any(part == ".." for part in p.parts):
        raise PermissionError("path traversal denied")
    root = ws_root(workspace_path).resolve()
    abs_path = (root / p).resolve()
    if abs_path != root and root not in abs_path.parents:
        raise PermissionError("path escapes workspace")
    return abs_path


# ── extension classification (shared by the file-tree + the editor pane) ──
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "ico", "avif", "apng"}
_PDF_EXTS = {"pdf"}
_SVG_EXTS = {"svg"}
_AUDIO_EXTS = {"mp3", "wav", "ogg", "flac", "m4a", "aac", "opus"}
_VIDEO_EXTS = {"mp4", "mov", "webm", "mkv", "avi", "m4v"}


def classify_extension(name: str) -> str:
    """Bucket a filename by extension into the renderer the editor uses."""
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


def unique_dest(dst: Path) -> Path:
    """If `dst` exists, append " (copy N)" until we find a free name."""
    if not dst.exists():
        return dst
    parent = dst.parent
    stem = dst.stem
    suffix = dst.suffix
    n = 1
    candidate = parent / f"{stem} (copy){suffix}"
    while candidate.exists():
        n += 1
        candidate = parent / f"{stem} (copy {n}){suffix}"
    return candidate
