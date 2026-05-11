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
# `.DS_Store` / `.git` are the obvious noise. The remaining names
# (AGENTS.md, package.json, extensions, guides, node_modules) are
# the **agent-metadata symlinks** wired into the sandbox by
# registry._wire_sandbox_symlinks so pi (running with cwd `/workspace`
# = sandbox parent in docker mode, or workspace_path itself in
# subprocess mode) can find them at its cwd. The watcher in
# file_watcher.py also ignores them when scanning the sandbox parent
# for stray writes — they're implementation detail, the user
# shouldn't see them in the file tree mixed with their own files.
# (`.pi/` is already covered by the leading-dot prefix rule.) If
# a real user file happens to share one of these names, that's a
# cost we accept.
_IGNORE_NAMES = {
    ".DS_Store",
    ".git",
    "AGENTS.md",
    "package.json",
    "extensions",
    "guides",
    "node_modules",
}
_IGNORE_PREFIXES = (".",)
_IGNORE_SUFFIXES = (".swp", ".swo", "~")


def should_ignore(rel_path: str) -> bool:
    """True for OS junk, editor swap files, and agent-metadata symlinks
    we hide from the UI. See `_IGNORE_NAMES` for the full list."""
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
# Native in-browser visual viewers (added 2026-05). These render the
# binary FAITHFULLY — same look as Excel / Word — using:
#   - SheetJS / xlsx for spreadsheets (frontend)
#   - docx-preview for Word documents (frontend)
#   - sql.js (SQLite-WASM) for .db browsers (frontend)
# We classify them as their own kinds so the editor pane can dispatch
# to the right viewer instead of falling back to a markdown text dump.
_SPREADSHEET_EXTS = {"xlsx", "xls", "xlsm", "xlsb", "ods", "csv", "tsv"}
_WORD_EXTS = {"docx"}                       # Only docx renders well via docx-preview.
_SLIDES_EXTS = {"pptx"}                      # Reserved for future pptx viewer.
_SQLITE_EXTS = {"db", "sqlite", "sqlite3", "db3", "sdb"}
# Legacy or rarely-used office formats — fall back to server-side
# markdown extraction (markitdown) for inline preview. Browsers have no
# native viewer for these and there isn't a small/free in-browser
# parser we'd trust for them.
_OFFICE_EXTS = {
    "doc", "odt", "rtf",          # legacy Word formats
    "ppt", "odp",                  # legacy PowerPoint
    "epub", "msg", "eml",          # ebook + email
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
    if ext in _SPREADSHEET_EXTS:
        return "spreadsheet"
    if ext in _WORD_EXTS:
        return "word"
    if ext in _SLIDES_EXTS:
        return "slides"
    if ext in _SQLITE_EXTS:
        return "sqlite"
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
