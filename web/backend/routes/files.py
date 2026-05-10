"""
Read-only views over a workspace's user-files dir: tree, content, raw bytes.

Mutating endpoints live in `routes/fs.py` (POST/DELETE) — keeping the
read-only surface separate makes it trivial to add e.g. a "read-only
viewer" mode for shared sessions later.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from routes._helpers import fs_error, workspace_path_for_user_or_404
from services.auth import require_user
from services.binary_extract import extract_to_markdown
from services.file_ops import list_tree, read_file, stream_raw_path
from services.paths import safe_path

router = APIRouter(prefix="/api/workspaces/{wsid}/files", tags=["files"])


@router.get("")
async def get_tree(wsid: str, user_id: str = Depends(require_user)) -> dict[str, Any]:
    return {"items": list_tree(workspace_path_for_user_or_404(wsid, user_id))}


@router.get("/content")
async def get_content(
    wsid: str, path: str = Query(...), user_id: str = Depends(require_user)
) -> dict[str, Any]:
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        return read_file(ws, path)
    except (PermissionError, FileNotFoundError, IsADirectoryError, OSError) as exc:
        raise fs_error(exc)


@router.get("/raw")
async def get_raw(
    wsid: str,
    path: str = Query(...),
    download: bool = Query(False),
    user_id: str = Depends(require_user),
) -> FileResponse:
    """
    Stream the file's raw bytes back. Used for two distinct things:

      1. Inline preview (default) — `Content-Disposition: inline` so the
         browser shows it in <iframe>/<img>/<audio>/<video>.
      2. Download (`?download=1`) — `Content-Disposition: attachment` so
         the browser saves it to disk via the editor's download button.

    Either way, auth is enforced; the frontend wraps every request in an
    auth'd fetch + blob URL because <iframe> can't carry a Bearer header.
    """
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        abs_path, mime = stream_raw_path(ws, path)
    except (PermissionError, FileNotFoundError, IsADirectoryError) as exc:
        raise fs_error(exc)
    disposition = "attachment" if download else "inline"
    return FileResponse(
        path=str(abs_path),
        media_type=mime,
        headers={"Content-Disposition": f'{disposition}; filename="{abs_path.name}"'},
    )


@router.get("/preview-md")
async def get_preview_markdown(
    wsid: str, path: str = Query(...), user_id: str = Depends(require_user)
) -> dict[str, Any]:
    """
    Convert an office / PDF / etc. document to Markdown via markitdown.

    Frontend calls this for files where `kind == "office"` (docx, xlsx,
    pptx, csv, eml, …) and renders the returned `markdown` string with
    the same renderer used for chat messages. PDFs continue to use the
    browser's native viewer (richer fidelity); they only hit this endpoint
    when the user clicks "Read as text" for a scanned/searchable PDF.

    Embedded images: for DOCX/PPTX, markitdown emits inline base64 photos
    by default. We extract those to a workspace sidecar dir
    (``digi-setu/extracts/<stem>-<hash>/``) and rewrite the markdown to
    reference them via workspace-relative paths. The frontend's markdown
    renderer resolves those paths through the same authed
    ``/files/raw?path=…`` plumbing it uses everywhere else, so the human
    sees the photos inline AND the AI's read_doc tool sees the exact
    same paths it can hand to its `read` tool. One source of truth.

    Returns:
        {
            "path": "...",
            "markdown": "...",          # only if extraction succeeded
            "error":    "...",          # only if it failed
            "cached":   true/false,
            "imagesExtracted": int,     # 0 when no images found
            "extractDirRel":   "..."    # workspace-relative; null if 0 images
        }
    """
    ws = workspace_path_for_user_or_404(wsid, user_id)
    try:
        abs_path = safe_path(ws, path)
    except PermissionError as exc:
        raise fs_error(exc)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"file not found: {path}")
    if not abs_path.is_file():
        raise HTTPException(status_code=400, detail=f"not a regular file: {path}")

    # Build a deterministic per-revision extract dir under the workspace.
    # Same hash scheme the internal AI route uses, so a DOCX previewed
    # by the human and read_doc'd by the AI hits the same dir → same
    # image paths → no duplication on disk.
    import hashlib as _hashlib
    import re as _re

    stat = abs_path.stat()
    digest = _hashlib.sha1(
        f"{abs_path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8"),
    ).hexdigest()[:8]
    stem_slug = _re.sub(r"[^a-zA-Z0-9._-]+", "-", abs_path.stem).strip("-") or "doc"
    extract_dir_rel = f"digi-setu/extracts/{stem_slug}-{digest}"
    extract_dir = ws / extract_dir_rel
    rel_prefix: str | None
    try:
        extract_dir.mkdir(parents=True, exist_ok=True)
        # Workspace-relative (no leading "./") so the markdown
        # renderer's URL resolver sees a path it can hand straight to
        # the /files/raw endpoint without any cleanup.
        rel_prefix = extract_dir_rel
    except OSError:
        # Filesystem RO or no perms — fall back to no-extract mode
        # rather than 500ing. The user still gets the text.
        extract_dir = None  # type: ignore[assignment]
        rel_prefix = None

    res = extract_to_markdown(
        abs_path,
        extract_dir=extract_dir,
        rel_prefix=rel_prefix,
    )
    return {
        "path": path,
        "markdown": res.markdown,
        "error": res.error,
        "cached": res.cached,
        "imagesExtracted": res.images_extracted,
        "extractDirRel": rel_prefix if res.images_extracted > 0 else None,
    }
