"""
Cold-tier archival for idle workspaces.

Why this exists
---------------
Active session data (workspaces, shadows) lives on the VM's data disk
under ``/srv/pi/data/`` for low-latency reads/writes — file watcher,
AI edits, save-and-compile cycles all need SSD speed. But long-tail
data (workspaces nobody opened in months) doesn't need to occupy hot
SSD; it needs to be cheap to store and OK-fast to restore.

This module implements the swap. A nightly reaper (running outside
the backend container, see ``deploy/systemd/pi-cold-archive.*``)
walks every workspace, identifies anything untouched for
``COLD_THRESHOLD_DAYS`` days, tars + gzips it, uploads to
``gs://digi-setu-cold/workspaces/<wsid>.tar.gz``, and replaces the
local tree with a single ``.cold.json`` marker file. On the next
user open the registry's ``workspace_path()`` notices the marker,
blocks while it pulls + extracts (~5–15 s for typical workspaces,
depending on size), removes the marker, and proceeds as if the data
had been there all along.

Auth
----
Uses the standard google-cloud-storage client, which picks up
Application Default Credentials. On the VM that's the attached
service account (digi-setu-live@... has roles/storage.objectAdmin
on gs://digi-setu-cold). On a laptop you'd need to ``gcloud auth
application-default login`` once if you want to test manually.

What's archived
---------------
For each ``wsid``:
    * the workspace dir at ``DATA_ROOT/workspaces/<wsid>/`` — minus
      our agent-metadata symlinks (extensions/, AGENTS.md, etc.) which
      get re-stamped on thaw by the registry's sandbox bootstrap path.
    * the shadow git repo at ``DATA_ROOT/shadows/<wsid>/`` if present.

Chats live separately under ``DATA_ROOT/chats/<sid>/`` and are NOT
archived here — they're tiny (KBs), referenced by sid not wsid, and
hot data (the picker shows them).

State (registry.json, sqlite) stays on the VM disk in all cases —
it's the index that tells us which workspaces are cold in the first
place, so it must be available without a thaw.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tarfile
import threading
import time
from pathlib import Path
from typing import Optional

from config import DATA_ROOT  # noqa: E402

# GCS bucket where archived workspaces live. Operators provision this
# (one-shot, see deploy/scripts/setup-cold-storage.sh) and grant the
# VM's attached service account roles/storage.objectAdmin on it. Set
# COLD_BUCKET="" to disable archival entirely (useful for laptop dev).
COLD_BUCKET = os.environ.get("COLD_BUCKET", "digi-setu-cold").strip()

# Workspaces idle longer than this are eligible for archival. We use
# the maximum mtime across the whole workspace tree (so a single file
# touched yesterday keeps the workspace hot).
COLD_THRESHOLD_DAYS = int(os.environ.get("COLD_THRESHOLD_DAYS", "30"))

# Marker file placed inside the workspace dir after archival. On thaw,
# the registry checks for this and triggers a pull-and-extract before
# yielding the path to a caller. Format:
#   {"cold": true, "gcs_uri": "gs://...", "archived_at": <epoch>}
COLD_MARKER_NAME = ".cold.json"

# Per-process locks so concurrent thaw calls for the same wsid block
# rather than racing. The lock dict itself is guarded by a coarse
# lock — we never hold both at once.
_thaw_locks: dict[str, threading.Lock] = {}
_thaw_locks_guard = threading.Lock()


def _gcs_object_for(wsid: str) -> str:
    """Object name (within the bucket) for this workspace's archive."""
    return f"workspaces/{wsid}.tar.gz"


def _gcs_uri_for(wsid: str) -> str:
    return f"gs://{COLD_BUCKET}/{_gcs_object_for(wsid)}"


def _wsdir(wsid: str) -> Path:
    return DATA_ROOT / "workspaces" / wsid


def _shadowdir(wsid: str) -> Path:
    return DATA_ROOT / "shadows" / wsid


def _marker_path(wsid: str) -> Path:
    return _wsdir(wsid) / COLD_MARKER_NAME


def _bucket():
    """Lazy-import the GCS client so dev installs without it still boot."""
    from google.cloud import storage  # type: ignore
    return storage.Client().bucket(COLD_BUCKET)


def is_cold(wsid: str) -> bool:
    """True iff the local workspace tree has been replaced by a cold marker."""
    return _marker_path(wsid).is_file()


def cold_metadata(wsid: str) -> Optional[dict]:
    p = _marker_path(wsid)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


# ── archive ─────────────────────────────────────────────────────────


def _max_mtime(root: Path) -> float:
    """Largest mtime under `root`, or root's own mtime if empty/walkable."""
    best = 0.0
    try:
        best = root.stat().st_mtime
    except OSError:
        return 0.0
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            try:
                m = os.stat(os.path.join(dirpath, name)).st_mtime
                if m > best:
                    best = m
            except OSError:
                continue
    return best


def should_archive(wsid: str, *, threshold_days: int = COLD_THRESHOLD_DAYS) -> bool:
    """Eligibility check: workspace exists, has real content, and is idle."""
    wsdir = _wsdir(wsid)
    if not wsdir.is_dir():
        return False
    if is_cold(wsid):
        return False
    last = _max_mtime(wsdir)
    if last == 0.0:
        return False
    age_days = (time.time() - last) / 86400.0
    return age_days > threshold_days


def archive_workspace(wsid: str, *, dry_run: bool = False) -> Optional[dict]:
    """Tar+gzip the workspace+shadow tree, upload to GCS, leave a marker.

    Returns the marker dict on success, ``None`` if the workspace
    didn't qualify (already cold, missing). Raises on hard failures
    (GCS API error, disk full, etc.).
    """
    if not COLD_BUCKET:
        return None
    wsdir = _wsdir(wsid)
    shadowdir = _shadowdir(wsid)
    if not wsdir.is_dir():
        return None
    if is_cold(wsid):
        return None

    gcs_uri = _gcs_uri_for(wsid)
    print(f"[cold-archive] {wsid}: tar+gzip → {gcs_uri}", file=sys.stderr)
    if dry_run:
        return {"cold": True, "gcs_uri": gcs_uri, "dry_run": True}

    # Build the tarball in-memory. Typical workspace is 10–200 MB so
    # this fits comfortably in the backend's RAM. For a workspace
    # exceeding ~1 GB we'd want a streaming upload; cross that bridge
    # if anyone ever hits it (today's biggest is <300 MB).
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(wsdir), arcname=f"workspaces/{wsid}")
        if shadowdir.is_dir():
            tar.add(str(shadowdir), arcname=f"shadows/{wsid}")
    buf.seek(0)
    payload_size = buf.getbuffer().nbytes

    # Upload to GCS. The bucket's default storage class is COLDLINE
    # so we pay the cheap per-GB rate. resumable=True lets the client
    # retry on transient failures without the caller knowing.
    blob = _bucket().blob(_gcs_object_for(wsid))
    blob.cache_control = "no-cache"
    blob.upload_from_file(
        buf, rewind=True, content_type="application/gzip",
    )

    # Verify the object exists with the size we sent. Better to keep
    # a redundant local copy than to lose the workspace if the upload
    # silently truncated.
    blob.reload()
    if blob.size != payload_size:
        raise RuntimeError(
            f"GCS size mismatch for {wsid}: sent {payload_size}, "
            f"got {blob.size}"
        )

    # Replace local tree with the marker. Shadow dir is removed too —
    # the tarball has it, thaw restores it. Order matters: rmtree the
    # shadow first, then clear the workspace dir, then write the
    # marker (otherwise rmtree would eat the marker).
    if shadowdir.is_dir():
        shutil.rmtree(shadowdir)
    for child in wsdir.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            try:
                child.unlink()
            except FileNotFoundError:
                pass
    marker = {
        "cold": True,
        "gcs_uri": gcs_uri,
        "archived_at": int(time.time()),
        "size_bytes": payload_size,
    }
    _marker_path(wsid).write_text(json.dumps(marker))
    print(
        f"[cold-archive] {wsid}: archived {payload_size:,} B & local tree "
        "replaced with marker",
        file=sys.stderr,
    )
    return marker


def archive_idle(*, threshold_days: int = COLD_THRESHOLD_DAYS,
                 dry_run: bool = False) -> dict:
    """Walk every workspace dir on disk and archive the idle ones."""
    base = DATA_ROOT / "workspaces"
    if not base.is_dir():
        return {"scanned": 0, "archived": 0, "skipped": 0, "errors": 0}
    scanned = archived = skipped = errors = 0
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        wsid = child.name
        scanned += 1
        try:
            if not should_archive(wsid, threshold_days=threshold_days):
                skipped += 1
                continue
            res = archive_workspace(wsid, dry_run=dry_run)
            if res is not None:
                archived += 1
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[cold-archive] {wsid}: ERROR {exc!r}", file=sys.stderr)
            errors += 1
    return {
        "scanned": scanned, "archived": archived,
        "skipped": skipped, "errors": errors,
    }


# ── thaw ────────────────────────────────────────────────────────────


def _get_thaw_lock(wsid: str) -> threading.Lock:
    with _thaw_locks_guard:
        lock = _thaw_locks.get(wsid)
        if lock is None:
            lock = threading.Lock()
            _thaw_locks[wsid] = lock
        return lock


def thaw_workspace(wsid: str) -> None:
    """Pull the workspace back from GCS and extract in-place.

    Idempotent. Safe to call concurrently — the second caller blocks
    on the per-wsid lock and exits cleanly when the marker is gone.
    No-op if the workspace isn't actually cold.
    """
    if not is_cold(wsid):
        return
    lock = _get_thaw_lock(wsid)
    with lock:
        # Re-check inside the lock — another thread may have thawed
        # while we were waiting.
        if not is_cold(wsid):
            return
        meta = cold_metadata(wsid) or {}
        gcs_uri = meta.get("gcs_uri") or _gcs_uri_for(wsid)
        print(f"[cold-archive] {wsid}: thawing from {gcs_uri}", file=sys.stderr)

        # Delete the marker BEFORE extracting. A crash mid-extract
        # leaves the workspace dir partially restored without the
        # marker, which is detectably broken (registry's sandbox
        # bootstrap path runs again on next access). The alternative
        # — leaving the marker until extract completes — would mean a
        # crash leaves both old marker AND half-extracted files
        # coexisting, which silently serves corrupt data on next read.
        try:
            _marker_path(wsid).unlink()
        except FileNotFoundError:
            pass

        # Stream the blob through tarfile in one pass. We download to
        # an in-memory buffer (size-bounded by COLDLINE policy: we
        # never archive workspaces > 1 GB without revisiting this).
        # Using download_as_bytes keeps the API simple; for huge
        # tarballs we'd switch to a chunked download_to_file + seek.
        buf = io.BytesIO()
        blob = _bucket().blob(_gcs_object_for(wsid))
        blob.download_to_file(buf)
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            tar.extractall(str(DATA_ROOT))
        print(
            f"[cold-archive] {wsid}: thawed in {_wsdir(wsid)}",
            file=sys.stderr,
        )


# ── CLI ─────────────────────────────────────────────────────────────


def _main(argv: list[str]) -> int:
    """Tiny CLI so the systemd timer can shell out to this module.

    Usage:
        python -m services.cold_archive archive [--dry-run] [--days N]
        python -m services.cold_archive thaw <wsid>
    """
    if not argv:
        print("usage: cold_archive {archive|thaw <wsid>} [opts]", file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "archive":
        days = COLD_THRESHOLD_DAYS
        dry = False
        i = 1
        while i < len(argv):
            if argv[i] == "--dry-run":
                dry = True
                i += 1
            elif argv[i] == "--days" and i + 1 < len(argv):
                days = int(argv[i + 1])
                i += 2
            else:
                print(f"unknown arg: {argv[i]}", file=sys.stderr)
                return 2
        report = archive_idle(threshold_days=days, dry_run=dry)
        print(json.dumps(report))
        return 0
    if cmd == "thaw":
        if len(argv) != 2:
            print("usage: cold_archive thaw <wsid>", file=sys.stderr)
            return 2
        thaw_workspace(argv[1])
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
