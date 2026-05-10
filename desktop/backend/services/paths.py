"""
Shared path conventions and safety helpers for everything that touches a
workspace's user-files directory.

DESKTOP fork — workspace layout:

    /the/folder/the/user/picked/    ← THIS IS the workspace.
                                       The user's real files live here
                                       directly. There is NO `workspace/`
                                       subdir like the web sandbox uses
                                       (that subdir was an artefact of
                                       wrapping a ws_id-named sandbox
                                       around the user's content; on
                                       desktop we trust the user's pick
                                       and treat the folder itself as
                                       the working tree).

All path-safety boundaries enforced here are anchored to the picked
folder, so traversal attempts (`..`, absolute paths, symlink-out)
still get rejected before any I/O happens — but they're rejected
relative to the user's folder, not a synthetic subdir.

This module is dependency-free (stdlib only) so both the watcher and
the file-ops helpers can import it without forming cycles.
"""

from __future__ import annotations

from pathlib import Path

# Kept as an empty constant rather than removing it: a couple of legacy
# call sites still reference WORKSPACE_SUBDIR (e.g. log lines, doc
# strings). With the value blank, `Path(workspace_path) / "" == Path(workspace_path)`
# so any code that does `Path(ws) / WORKSPACE_SUBDIR` ends up at the
# same place `ws_root()` returns. Keep this empty until all references
# are flushed; do NOT re-introduce a real subdir on desktop.
WORKSPACE_SUBDIR = ""


def ws_root(workspace_path: Path) -> Path:
    """
    Resolve the user-visible files root inside a workspace folder.

    Desktop semantics: the picked folder IS the working tree. No
    `workspace/` subdir is appended. The agent's cwd, the file watcher's
    root, and the editor's file tree all observe this same path.
    """
    return Path(workspace_path)


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
# "office" = anything we route through markitdown for in-browser preview.
# These have no native browser viewer, so we convert to markdown server-side
# and render that in the editor pane (see services/binary_extract.py).
_OFFICE_EXTS = {
    "docx", "doc", "odt", "rtf",
    "xlsx", "xls", "ods", "csv", "tsv",
    "pptx", "ppt", "odp",
    "epub", "msg", "eml",
}


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
    if ext in _OFFICE_EXTS:
        return "office"
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
