"""
Cheap recursive disk-usage check for a workspace.

Used by the chat WS handler to enforce a per-workspace soft quota
(`WORKSPACE_DISK_QUOTA_MB`). The check is fired *between* prompts —
not on every file write — so we don't bottleneck the agent's tool
calls on `os.walk` for every cat/echo.

Caching:
    `walk` is the expensive part. For a 100 MB cap that means
    walking O(thousands) of files. We cache the result for
    `_TTL_SECONDS` so a fast back-and-forth doesn't re-walk on
    every prompt. The cap is "soft" anyway — being a few seconds
    stale is fine; the worst-case overage is one prompt's worth of
    files, which is bounded by what one tool call can write.

Cross-FS safety:
    `os.walk(followlinks=False)` so a symlink-to-/etc-on-the-host
    doesn't suddenly make a workspace look 30 GB big.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from threading import Lock
from typing import Optional


_TTL_SECONDS = 5.0
_cache: dict[str, tuple[float, int]] = {}
_lock = Lock()


def _bytes_for(path: Path) -> int:
    total = 0
    try:
        for root, _dirs, files in os.walk(path, followlinks=False):
            for name in files:
                fp = os.path.join(root, name)
                try:
                    total += os.lstat(fp).st_size
                except OSError:
                    # File yanked between walk listing and stat —
                    # ignore; we'll catch it on the next pass.
                    continue
    except OSError:
        return total
    return total


def workspace_bytes(path: Path, *, force: bool = False) -> int:
    key = str(path)
    now = time.time()
    if not force:
        with _lock:
            entry = _cache.get(key)
            if entry and now - entry[0] < _TTL_SECONDS:
                return entry[1]
    total = _bytes_for(path)
    with _lock:
        _cache[key] = (now, total)
    return total


def workspace_mb(path: Path, *, force: bool = False) -> float:
    return workspace_bytes(path, force=force) / (1024 * 1024)


def over_quota(path: Path, quota_mb: int, *, force: bool = False) -> Optional[float]:
    """Return current usage in MB if it exceeds quota; else None.
    The float lets the caller surface a precise "you're at 102 of
    100 MB" message in the UI."""
    used = workspace_mb(path, force=force)
    return used if used > quota_mb else None


def invalidate(path: Path) -> None:
    """Drop a cached entry — call after a deliberate cleanup so the
    next check returns the post-deletion size, not the stale one."""
    with _lock:
        _cache.pop(str(path), None)
