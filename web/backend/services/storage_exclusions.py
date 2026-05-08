"""
Backup / cold-storage exclusion policy for workspace files.

Single source of truth used by:
  * future GCS / GCS-fuse sync (deploy/scripts/sync-data-to-gcs.sh)
  * future tar.zst dehydration step for inactive workspaces
  * `tar` / `rsync` --exclude commands in operator scripts

Why a Python module instead of a YAML / .env file: every consumer is
already a Python process that imports services/, and the list is
short enough to live as a module-level tuple. Keeping it in code
also lets us unit-test "is this path excluded" once and trust it
everywhere.

DESIGN PRINCIPLE: a workspace "loses nothing important" if these
folders are not backed up. They contain:
  * user-supplied attachment payloads (the user keeps the original
    on their own disk; re-uploading is cheap)
  * AI-generated derivatives (PDFs, PNGs, annotated screenshots)
    that can be regenerated from the chat history
  * shadow git's own working dir (the .git folder is what matters,
    not the checkout)

If you add a new always-excluded folder, append it here and document
*why* it's safe to lose. Things that MUST stay backed up (do NOT
add to either list):
  * `chats/`        — chat history JSONL log
  * `registry.json` — workspace + session catalogue
  * `billing.db`    — credit ledger + activity log (events table is
                       the durable record of "what did the user run
                       and what did it cost"; losing it means losing
                       monthly spend tracking and the activity view's
                       history across the restart)
  * `users/`        — per-user preferences (permission_mode, etc.)
"""

from __future__ import annotations

from typing import Iterable

# Workspace-relative path segments that should never be pushed off-VM.
# Matched as exact directory names anywhere under the workspace root.
# (i.e. `workspace/uploads/` matches the rule the same as `uploads/`.)
EXCLUDED_DIR_NAMES: tuple[str, ...] = (
    # User uploads. By policy the original lives on the user's own
    # device — they re-attach if they need it again. Storing
    # multi-MB binaries (PDFs, images, video) in GCS for every
    # workspace would balloon storage cost for zero recovery
    # benefit, since recovery requires the user to re-paste anyway.
    "uploads",
    # Build / tooling caches that regenerate on demand. Not
    # currently created in v1 but listed here so the sync script
    # already does the right thing the day a tool starts using
    # them.
    "node_modules",
    ".cache",
    "__pycache__",
    ".venv",
    ".pytest_cache",
)


# Glob patterns that are also excluded. Use sparingly — a directory
# name in EXCLUDED_DIR_NAMES is faster to evaluate. Patterns are
# matched against POSIX-style relative paths from the workspace root.
EXCLUDED_GLOBS: tuple[str, ...] = (
    # Compiled python artefacts left by ad-hoc scripts.
    "*.pyc",
    # Editor swap files.
    "*.swp",
    ".DS_Store",
    # Lock files for ephemeral processes.
    "*.lock",
)


def rsync_excludes() -> list[str]:
    """Format the exclusion list as `--exclude=...` flags suitable
    for an `rsync` / `gsutil rsync` command line."""
    out: list[str] = []
    for name in EXCLUDED_DIR_NAMES:
        out.extend([f"--exclude={name}/", f"--exclude={name}"])
    for pat in EXCLUDED_GLOBS:
        out.append(f"--exclude={pat}")
    return out


def tar_excludes() -> list[str]:
    """Format the exclusion list as `--exclude=...` flags for GNU
    tar (used by the dehydration step)."""
    out: list[str] = []
    for name in EXCLUDED_DIR_NAMES:
        out.append(f"--exclude=*/{name}")
    for pat in EXCLUDED_GLOBS:
        out.append(f"--exclude={pat}")
    return out


def is_excluded(rel_path: str) -> bool:
    """Quick check: would `rel_path` be skipped by a backup tool?

    `rel_path` is workspace-relative and POSIX-style. Used only by
    tests today; live sync paths shell out to rsync and rely on its
    own matcher.
    """
    parts = [p for p in rel_path.split("/") if p]
    if any(p in EXCLUDED_DIR_NAMES for p in parts):
        return True
    from fnmatch import fnmatch
    return any(fnmatch(rel_path, g) or fnmatch(parts[-1], g) for g in EXCLUDED_GLOBS) if parts else False


def excluded_dir_names() -> Iterable[str]:
    """Iter over the directory names. Useful for shell scripts that
    `printf '%s\n' $(python -c '…')` the list and feed it to find."""
    return EXCLUDED_DIR_NAMES
