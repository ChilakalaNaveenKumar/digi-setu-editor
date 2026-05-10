"""
Loopback-only internal routes consumed by the spawned pi process.

These endpoints are NOT used by the browser — they're called from the
pi-coding-agent extension (see `extensions/typst-tools.ts:read_doc`) so
the AI can read PDF / DOCX / XLSX / PPTX documents through the
backend's `markitdown` service instead of feeding raw binary bytes
into its `read` tool (which produces UTF-8 garbage for non-text
formats).

Auth model — deliberately separate from Clerk:
  * Clerk fronts every user-facing route. The spawned pi child has no
    Clerk session and no way to obtain one (it isn't a browser).
  * Instead, the backend mints a per-process random token at startup
    (services/internal_auth.py:get_internal_token), publishes it to
    the spawned pi via the `PI_INTERNAL_TOKEN` env var, and validates
    incoming requests against `Authorization: Bearer <token>`.
  * The token never leaves localhost: this router enforces a 127.0.0.1
    / ::1 client-IP check and rejects everything else with 403, so a
    leaked token alone is not enough to call the endpoint from the
    public internet (Caddy in production also strips this prefix and
    refuses to proxy it — see deploy/Caddyfile).

Route surface (kept tiny on purpose):
  POST /api/internal/extract-md
        body: { "abs_path":      "/abs/path/to/file.docx",
                "workspace_cwd": "/abs/path/to/workspace" }
        returns: { markdown, error, cached, images_extracted, extract_dir_rel }

About `workspace_cwd`:
  Markitdown emits embedded photos in DOCX / PPTX as huge inline
  ``data:image/png;base64,...`` URIs. Even one of those (~50k tokens)
  blows out an LLM context window. Instead of stripping them, we
  decode them to a workspace-local sidecar directory:

      <workspace_cwd>/digi-setu/extracts/<stem-slug>-<hash8>/image-N.<ext>

  …and rewrite the markdown to reference workspace-relative paths
  (``./digi-setu/extracts/foo-ab12cd/image-1.png``). The AI can then
  call ``read("./digi-setu/.../image-1.png")`` ONLY for images it
  actually wants to look at — same path also resolves against the
  editor's authed file-serve plumbing, so the human renders the same
  preview the AI sees.

  The `<hash8>` is `sha1(abs_path + mtime_ns + size)[:8]` — stable per
  file revision, so re-opening the same DOCX reuses the same dir
  (idempotent) but a real edit minted a new dir (no stale references).

  Files outside the workspace fall back to no-extract mode (images get
  one-line stripped placeholders) because we never want pi extracting
  /etc/foo.docx and dumping bytes into the user's workspace.

Why POST + body instead of GET + query? The path can be long enough to
trip URL-length caps on some intermediaries; we never want a tool call
to silently 414. Also keeps the path out of access logs.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from services.binary_extract import extract_to_markdown
from services.internal_auth import get_internal_token

# Slug regex used to derive the extract-dir name from the document stem.
# We collapse any run of non-(alphanumeric + ``._-``) bytes into a single
# hyphen so we never write a path component containing whitespace or
# shell-special characters — those would break the AI's downstream
# ``read("./digi-setu/...")`` call as soon as it tried to quote it.
_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _slug(s: str) -> str:
    out = _SLUG_RE.sub("-", s).strip("-")
    return out or "doc"

router = APIRouter(prefix="/api/internal", tags=["internal"])


# Match the wall-clock cap inside binary_extract. Surface it on the
# health response so an operator (or a smoke-test script) can confirm
# the env injection actually worked without sniffing internals.
class ExtractRequest(BaseModel):
    abs_path: str = Field(..., description="Absolute filesystem path of the document to extract.")
    workspace_cwd: str | None = Field(
        default=None,
        description=(
            "Absolute path of the calling pi's cwd (the workspace root). "
            "When provided AND `abs_path` lives inside it, embedded images "
            "are decoded to `<workspace_cwd>/digi-setu/extracts/<slug>-<hash>/` "
            "and the markdown references workspace-relative paths the "
            "agent can hand straight to its `read` tool."
        ),
    )


class ExtractResponse(BaseModel):
    markdown: str | None = None
    error: str | None = None
    cached: bool = False
    # 0 when the document had no embedded images, the caller didn't pass
    # a workspace_cwd, or the file was outside the workspace.
    images_extracted: int = 0
    # Workspace-relative path where images were dumped (None if no
    # extraction happened). The frontend uses this to render an
    # "extracted N images to ./digi-setu/..." status line; the AI sees
    # the same paths inline in the markdown.
    extract_dir_rel: str | None = None


def _require_loopback(request: Request) -> None:
    """Reject any request from a non-loopback client.

    In production Caddy never proxies /api/internal/* — the route is
    only reachable via the localhost socket — but enforcing this in
    code makes the contract explicit and protects against a future
    operator accidentally exposing it. ``client.host`` is whatever
    Starlette assigns; we check the literal IPs because the env can
    be IPv4-only or dual-stack and we want both to work.
    """
    host = (request.client.host if request.client else "") or ""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="loopback only")


def _require_internal_bearer(authorization: str | None) -> None:
    expected = get_internal_token()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing internal bearer token")
    presented = authorization.split(" ", 1)[1].strip()
    # Constant-time comparison so timing doesn't leak which prefix
    # bytes match. The standard library's `secrets.compare_digest` is
    # the canonical helper.
    import secrets as _sec

    if not _sec.compare_digest(presented, expected):
        raise HTTPException(status_code=403, detail="bad internal bearer token")


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    """Smoke-check the route is reachable and the env token is present.
    No bearer required — this is loopback-only and we want operators to
    be able to curl it during diagnostics without juggling the token."""
    _require_loopback(request)
    return {"ok": True, "has_token": bool(get_internal_token(allow_empty=True))}


@router.post("/extract-md", response_model=ExtractResponse)
def extract_md(
    body: ExtractRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> ExtractResponse:
    """Extract a binary document at `abs_path` to Markdown via markitdown.

    Designed for the pi-coding-agent's `read_doc` tool. The caller has
    already resolved + sanity-checked the absolute path (workspace
    boundary checks happen there); this route trusts the path and only
    validates loopback + bearer.

    Errors are returned in-band (200 with `error` populated) for the
    expected failure modes (timeout, parser error, missing file) so
    the agent can surface them as a tool-call result rather than as a
    stack-trace. We still 4xx on auth/bad-request for the same reason
    every other endpoint does — those are caller bugs.
    """
    _require_loopback(request)
    _require_internal_bearer(authorization)

    raw = (body.abs_path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="abs_path is required")

    p = Path(raw)
    if not p.is_absolute():
        # An accidental relative path here would resolve against the
        # backend's cwd, NOT the workspace — and could escape into
        # /srv/pi/data. Force callers to send absolute paths and let
        # the agent compute them from its own cwd.
        raise HTTPException(status_code=400, detail="abs_path must be absolute")

    # ── Resolve the (optional) extract-to-disk plan ────────────────
    extract_dir: Path | None = None
    rel_prefix: str | None = None
    extract_dir_rel: str | None = None

    ws_raw = (body.workspace_cwd or "").strip()
    if ws_raw:
        ws_p = Path(ws_raw)
        if not ws_p.is_absolute():
            raise HTTPException(
                status_code=400,
                detail="workspace_cwd must be absolute",
            )
        # Resolve symlinks once so the containment check below can't
        # be fooled by a workspace that's actually a symlink into
        # /tmp or wherever.
        try:
            ws_resolved = ws_p.resolve(strict=True)
            doc_resolved = p.resolve(strict=True)
        except (FileNotFoundError, RuntimeError):
            # File or workspace doesn't exist (or symlink loop). Let
            # extract_to_markdown surface the precise error so we
            # don't fork the diagnostic message in two places.
            ws_resolved = None
            doc_resolved = None

        if ws_resolved and doc_resolved:
            try:
                # is_relative_to was added in 3.9 but Path.relative_to
                # raising ValueError works on 3.8+.
                doc_resolved.relative_to(ws_resolved)
                inside_workspace = True
            except ValueError:
                inside_workspace = False
        else:
            inside_workspace = False

        if inside_workspace:
            try:
                stat = doc_resolved.stat()  # type: ignore[union-attr]
                digest = hashlib.sha1(
                    f"{doc_resolved}:{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8"),
                ).hexdigest()[:8]
                stem_slug = _slug(p.stem)
                extract_dir_rel = f"digi-setu/extracts/{stem_slug}-{digest}"
                extract_dir = ws_resolved / extract_dir_rel  # type: ignore[union-attr]
                extract_dir.mkdir(parents=True, exist_ok=True)
                # Workspace-relative path the AGENT will see. The
                # leading "./" makes it unambiguous: the agent's cwd
                # IS the workspace, so this resolves identically.
                rel_prefix = "./" + extract_dir_rel
            except OSError as exc:
                # mkdir or stat failed — fall back to no-extract mode
                # rather than 500ing. The user can still read the doc.
                extract_dir = None
                rel_prefix = None
                extract_dir_rel = None
                # Surface in the response so the frontend can show a
                # toast; not fatal enough to fail the whole extraction.
                # (We can't return early because we still want the
                # markdown.)
                _mkdir_error = f"could not prepare extract dir: {exc}"
            else:
                _mkdir_error = None
        else:
            _mkdir_error = None
    else:
        _mkdir_error = None

    res = extract_to_markdown(p, extract_dir=extract_dir, rel_prefix=rel_prefix)

    err = res.error
    if _mkdir_error and not err:
        err = _mkdir_error

    return ExtractResponse(
        markdown=res.markdown,
        error=err,
        cached=res.cached,
        images_extracted=res.images_extracted,
        extract_dir_rel=extract_dir_rel if res.images_extracted > 0 else None,
    )
