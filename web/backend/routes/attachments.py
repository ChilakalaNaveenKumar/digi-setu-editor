"""
Attachments — multipart upload of user-shared files into the workspace.

Files arrive via three frontend ingress points:

  • The composer's paperclip button (native file picker).
  • Clipboard paste in the chat region (images, files).
  • Drag-and-drop onto the chat pane OR onto a file tree row.

All three paths POST a multipart payload here. We save each part into
`<workspace>/workspace/uploads/<basename>` (or under `target_dir` if the
caller specified a folder, e.g. dropping onto a subfolder of the tree).

The response is `{saved: [{path, size, mime}]}` in the SAME order as the
input parts so the frontend can show a chip per file. The `path` is the
workspace-relative posix path the agent will see (e.g.
`workspace/uploads/my-photo.png`) — that's exactly the string the
composer prepends to the next prompt as "Attached files:\n- ...".

Sandbox: every save goes through `services.paths.safe_path` so a hostile
client can't escape the workspace via `../../etc/passwd` or a symlink
pointing at /tmp.

Filename sanitisation: we drop directory components (`Path(name).name`)
and rewrite anything outside `[A-Za-z0-9._-]` to `_`. If two uploads in
the same call collide we use `unique_dest()` which appends ` (copy)` /
` (copy 2)` etc — same convention as the rest of the file ops.

Size cap: per-file cap defaults to 25 MiB (configurable via env). A 4 GB
PNG paste would otherwise OOM the backend.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from routes._helpers import fs_error, workspace_for_user_or_404
from services.auth import require_user
from services.paths import safe_path, unique_dest
from services.registry import Registry

router = APIRouter(tags=["attachments"])

# Per-file upload cap (bytes). 25 MiB matches the maximum-comfortable
# size for an image paste that round-trips fast over wifi. Override
# via PI_UPLOAD_MAX_BYTES if you have power users uploading datasets.
MAX_UPLOAD_BYTES = int(os.getenv("PI_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))

# Filenames in uploads/ stay simple ASCII so they round-trip cleanly
# through the agent's tool-call protocol (which is JSON-over-stdout
# and therefore happy with any UTF-8, but can choke on backslashes,
# pipes, etc when the agent passes the path to bash).
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_name(raw: str) -> str:
    base = Path(raw or "upload").name.strip()
    if not base:
        base = "upload"
    cleaned = _SAFE_NAME.sub("_", base)
    return cleaned or "upload"


def _resolve_target_dir(workspace_path: Path, target_dir: str | None) -> Path:
    """Decide where the uploads land. Default = workspace/uploads/."""
    rel = (target_dir or "uploads").strip().strip("/")
    # `safe_path` already refuses `..` and absolute paths; but reject the
    # empty target explicitly to keep the default obvious.
    if not rel:
        rel = "uploads"
    abs_dir = safe_path(workspace_path, rel)
    abs_dir.mkdir(parents=True, exist_ok=True)
    return abs_dir


@router.post("/api/workspaces/{wsid}/attachments")
async def upload_attachments(
    wsid: str,
    files: list[UploadFile] = File(...),
    target_dir: str | None = Form(None),
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Multipart upload. `files` is the standard multipart parts list.

    `target_dir` is workspace-relative ("uploads", "src/assets", etc.).
    Defaults to "uploads" — the canonical drop folder for chat-attached
    content.
    """
    rec = workspace_for_user_or_404(wsid, user_id)
    workspace_path = Path(rec["path"])
    # Self-heal uploads/ for any pre-bootstrap workspace, then resolve
    # the actual target (might be a subfolder if user dropped onto one).
    Registry.instance().ensure_uploads_dir(wsid)

    try:
        target_abs = _resolve_target_dir(workspace_path, target_dir)
    except (PermissionError, ValueError) as exc:
        raise fs_error(exc) from exc

    saved: list[dict[str, Any]] = []
    for part in files:
        raw_name = part.filename or "upload"
        clean = _sanitize_name(raw_name)
        # Read in chunks so we can enforce the size cap without loading
        # the whole file into memory. Streaming UploadFile uses a
        # spooled tmpfile under the hood; we re-stream out of it.
        dst = unique_dest(target_abs / clean)
        bytes_written = 0
        try:
            with dst.open("wb") as f:
                while True:
                    chunk = await part.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > MAX_UPLOAD_BYTES:
                        f.close()
                        dst.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"file '{raw_name}' exceeds upload cap "
                                f"({MAX_UPLOAD_BYTES} bytes). "
                                "Increase PI_UPLOAD_MAX_BYTES if you need more."
                            ),
                        )
                    f.write(chunk)
        finally:
            await part.close()

        # We track two related rels because the agent and the HTTP/UI
        # see paths differently:
        #
        #   • agent_path: rooted at pi's cwd (= the workspace folder
        #     itself). The agent's tools read/write via this. Same
        #     convention AGENTS.md teaches: "workspace/foo.typ".
        #
        #   • tree_path:  rooted at the user-files dir (= workspace/).
        #     This is what list_tree, /api/.../fs/* and the file tree
        #     UI use. No "workspace/" prefix.
        #
        # The composer uses agent_path in the "Attached files:" prefix
        # so pi reads it correctly; the file tree uses tree_path to
        # refresh / scroll to the new row.
        agent_path = (
            dst.resolve().relative_to(workspace_path.resolve()).as_posix()
        )
        tree_path = (
            agent_path[len("workspace/"):]
            if agent_path.startswith("workspace/")
            else agent_path
        )

        saved.append(
            {
                "path": tree_path,
                "agent_path": agent_path,
                "absolute": str(dst),
                "size": bytes_written,
                "mime": part.content_type or "application/octet-stream",
                "name": dst.name,
            }
        )

    return {"saved": saved, "target_dir": target_dir or "uploads"}
