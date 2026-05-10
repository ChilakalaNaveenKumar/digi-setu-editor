"""
Server-side binary → Markdown extraction via Microsoft's `markitdown`.

What this is:
    A thin, cached wrapper around the `markitdown` library. Used by the
    file-preview endpoint (`routes/files.py:/preview-md`) to render docx /
    xlsx / pptx / pdf / etc. inline in the editor pane, and by the
    pi-coding-agent read-binary tool so the agent can "see" office docs as
    text without us reinventing six different format parsers.

Why a wrapper and not direct `MarkItDown().convert()` calls?
    * Result caching keyed by (path, mtime, size). A typical pptx pass
      takes 2–8 s; without caching every PDF page-flip in the editor
      would re-parse from scratch.
    * Soft import: `markitdown` is an optional install (~30 MB of deps
      with `[all]` minus audio). When it isn't present we degrade
      gracefully — return a friendly "install markitdown" placeholder
      instead of 500-ing.
    * Hard timeout: a malformed XLSX with circular refs can wedge the
      parser. We cap each call at 30 s and return a truncation notice
      so the request loop never hangs forever.
    * Centralised security knob: we always use `convert_local()` (never
      `convert()` / `convert_uri()`) so this helper can never be tricked
      into fetching a remote URL on behalf of the caller.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level singleton so we don't pay the (slow) plugin scan on every call.
_md_singleton: Optional[object] = None
_md_lock = threading.Lock()
_MD_IMPORT_ERR: Optional[str] = None

# Result cache: (abs_path_str, mtime_ns, size, mode_tag) -> markdown.
# ``mode_tag`` is either ``"stripped"`` (no disk extraction; placeholders
# inline) or ``f"extract:{rel_prefix}"`` (images dumped under that
# workspace-relative directory). We MUST include the rel_prefix in the
# key because two callers extracting the same DOCX into different
# workspace dirs produce different markdown bodies (the inline ``![](…)``
# paths differ). Bounded LRU; insertion-ordered dict eviction.
_cache: dict[tuple, str] = {}
_CACHE_MAX = 128
_cache_lock = threading.Lock()

# Hard cap: don't try to extract anything bigger than this. markitdown CAN
# handle larger files but the editor preview UX falls apart past this size
# (browser markdown render also struggles), and on container hosts a
# 500 MB pptx would balloon RSS. The agent read-binary tool reuses the
# same cap.
_SIZE_LIMIT = 50 * 1024 * 1024

# Per-call wall-clock cap. markitdown is sync; we run it on a thread and
# join with a timeout so a stuck parser can never leak.
_TIMEOUT_S = 30.0

# Output-side cap: how many characters of Markdown we hand back to a
# caller. Two reasons we need this on top of the input-size cap:
#   1. A 30-MB XLSX with 1M rows extracts to ~80 MB of pipe-delimited
#      Markdown. The frontend renderer chokes on it AND the AI agent's
#      context window (200k tokens ≈ 800 KB of dense text) can't
#      possibly fit it.
#   2. markitdown for DOCX/PPTX uses mammoth/python-pptx, both of
#      which embed images as base64 ``data:image/png;base64,...`` URIs
#      inside the Markdown. A single moderately-sized photo is 50-200
#      KB of base64 — five of those wipes out half a Haiku context.
#
# 200 KB ≈ ~50k tokens — comfortably under every model's input cap and
# leaves room for the rest of the conversation.
_MAX_OUTPUT_CHARS = 200_000

# Pattern that captures every inline base64 image markitdown emits.
# Groups: alt text, MIME subtype (png / jpeg / svg+xml / …), base64 body.
# Two policies depending on whether ``extract_dir`` is passed:
#
#   * ``extract_dir`` set (read_doc tool, editor preview):
#     decode each blob to disk under ``extract_dir`` as
#     ``image-N.<ext>`` and replace the data URI with a workspace-
#     relative path like ``![](./digi-setu/extracts/foo-ab12cd/image-1.png)``.
#     The AI / editor renderer then reads images on demand.
#
#   * ``extract_dir`` is ``None`` (rare fallback):
#     replace each data URI with a one-line ``[image — N KB stripped]``
#     placeholder so the AI is still aware an image existed.
_IMAGE_DATA_URI_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(data:image/(?P<subtype>[a-zA-Z0-9+.\-]+);base64,(?P<b64>[A-Za-z0-9+/=]+)\)",
    re.MULTILINE,
)

# Map markitdown's data-URI subtypes → canonical file extensions. Anything
# we don't recognise is written with ``.bin`` so the file still gets
# referenced — the AI can probe it with ``file`` if it really wants to
# know. (svg+xml is a happy accident: still a valid image extension.)
_IMAGE_EXT_FOR_SUBTYPE: dict[str, str] = {
    "png": ".png",
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "gif": ".gif",
    "webp": ".webp",
    "bmp": ".bmp",
    "tiff": ".tiff",
    "svg+xml": ".svg",
    "svg": ".svg",
}


@dataclass
class ExtractResult:
    """Either `markdown` is set, or `error` is — never both.

    ``images_extracted`` is the number of inline images written to disk
    on this call (0 if the caller didn't pass ``extract_dir`` or the
    document had no embedded images). The route exposes this so the
    frontend can tell the user "8 images written to ./digi-setu/...".
    """
    markdown: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False
    images_extracted: int = 0


def _get_md():
    """Lazy-init the MarkItDown singleton; return None if not installed."""
    global _md_singleton, _MD_IMPORT_ERR
    if _md_singleton is not None:
        return _md_singleton
    if _MD_IMPORT_ERR is not None:
        return None
    with _md_lock:
        if _md_singleton is not None:
            return _md_singleton
        try:
            from markitdown import MarkItDown  # type: ignore[import-not-found]
        except ImportError as exc:
            _MD_IMPORT_ERR = str(exc)
            logger.warning(
                "markitdown not installed (%s) — binary extraction disabled. "
                "Install with: pip install 'markitdown[pdf,docx,pptx,xlsx,xls,outlook]'",
                exc,
            )
            return None
        # Plugins disabled: we never want a third-party plugin smuggling in
        # arbitrary network calls or dependency installs at runtime.
        _md_singleton = MarkItDown(enable_plugins=False)
    return _md_singleton


def _cache_get(key: tuple) -> Optional[str]:
    with _cache_lock:
        return _cache.get(key)


def _cache_set(key: tuple, md: str) -> None:
    with _cache_lock:
        if key in _cache:
            del _cache[key]
        _cache[key] = md
        if len(_cache) > _CACHE_MAX:
            # Drop oldest entry (insertion-ordered dict).
            oldest = next(iter(_cache))
            del _cache[oldest]


def _strip_inline_images(md: str) -> tuple[str, int]:
    """Fallback used when the caller has no ``extract_dir``.

    Replaces each base64 inline image with a one-line placeholder so the
    AI agent at least KNOWS an image existed at that spot — without
    burning the ~50k tokens a real photo costs.
    """
    count = 0

    def _replace(m: "re.Match[str]") -> str:
        nonlocal count
        count += 1
        approx_kb = max(1, (len(m.group("b64")) * 3) // 4 // 1024)
        alt = (m.group("alt") or "").strip() or "image"
        return f"`[{alt} — {approx_kb} KB inline image, stripped]`"

    return _IMAGE_DATA_URI_RE.sub(_replace, md), count


def _extract_inline_images_to_disk(
    md: str,
    *,
    extract_dir: Path,
    rel_prefix: str,
) -> tuple[str, int]:
    """Decode every ``data:image/...;base64,...`` URI to disk and rewrite
    the markdown URL to a workspace-relative path.

    ``extract_dir`` MUST already exist; we don't ``mkdir`` it here so
    the caller stays in charge of permissions and lifecycle (the route
    handler creates it under the workspace root, where the existing
    file-write permission model already applies).

    ``rel_prefix`` is the workspace-relative path to ``extract_dir``,
    e.g. ``./digi-setu/extracts/report-ab12cd``. Splicing this into the
    markdown lets BOTH callers consume the result without any
    rewriting:

        - The AI agent (cwd == workspace) calls ``read("./digi-setu/…/image-1.png")``
          to vision-load only the images it actually wants to see.
        - The editor preview pane resolves the same path through its
          existing ``/files/raw?path=…`` plumbing.

    Returns ``(rewritten_markdown, images_written)``. We swallow per-
    image write errors — one corrupt blob shouldn't kill the whole
    extraction; we just leave that occurrence as a graceful inline
    placeholder.
    """
    import base64
    import binascii

    rel_prefix = rel_prefix.rstrip("/")
    count = 0

    def _replace(m: "re.Match[str]") -> str:
        nonlocal count
        subtype = (m.group("subtype") or "").lower()
        ext = _IMAGE_EXT_FOR_SUBTYPE.get(subtype, ".bin")
        b64 = m.group("b64")
        try:
            blob = base64.b64decode(b64, validate=False)
        except (binascii.Error, ValueError):
            # Bad base64 — leave the original URI in place; nothing we
            # can do, and writing 0 bytes would be misleading.
            return m.group(0)

        count += 1
        fname = f"image-{count}{ext}"
        out_path = extract_dir / fname
        try:
            out_path.write_bytes(blob)
        except OSError as exc:
            logger.warning(
                "failed to write extracted image %s: %s — falling back to placeholder",
                out_path, exc,
            )
            return f"`[image — {len(blob) // 1024} KB, write failed]`"

        alt = (m.group("alt") or "").strip() or "image"
        return f"![{alt}]({rel_prefix}/{fname})"

    return _IMAGE_DATA_URI_RE.sub(_replace, md), count


def _apply_output_cap(md: str) -> tuple[str, bool]:
    """Truncate at the character cap with a clear marker.

    Returns ``(possibly-truncated-markdown, was_truncated)``.
    """
    if len(md) <= _MAX_OUTPUT_CHARS:
        return md, False
    head = md[:_MAX_OUTPUT_CHARS].rstrip()
    truncated_kb = (len(md) - _MAX_OUTPUT_CHARS) // 1024
    footer = (
        f"\n\n---\n\n"
        f"⚠️ **Output truncated.** "
        f"~{truncated_kb} KB of additional content was dropped to keep this "
        f"response under the {_MAX_OUTPUT_CHARS // 1024} KB cap. "
        f"This typically means the source has too many rows/pages to fit "
        f"in a single response — for spreadsheets with millions of rows, "
        f"use `bash` + `csvkit` / `pandas` against the original file "
        f"instead of asking for the full markdown extraction."
    )
    return head + footer, True


def extract_to_markdown(
    abs_path: Path,
    *,
    extract_dir: Optional[Path] = None,
    rel_prefix: Optional[str] = None,
) -> ExtractResult:
    """
    Convert an office/PDF/etc. file at `abs_path` to Markdown.

    Caller is responsible for path safety; this helper trusts the absolute
    path it's given. Returns an `ExtractResult` with either `markdown` or
    `error` populated.

    Image handling is controlled by the (``extract_dir``, ``rel_prefix``)
    pair, which must be passed together or both be ``None``:

        * Both set — every inline base64 image markitdown emits is
          decoded to ``extract_dir/image-N.<ext>`` and the markdown is
          rewritten to reference ``rel_prefix/image-N.<ext>``. The
          caller is responsible for making sure ``extract_dir`` exists
          and lives under the workspace root (so the AI's path-aware
          tools — and the editor's authed file-serve plumbing — can
          resolve the resulting URLs).

        * Both ``None`` — base64 images are replaced with one-line
          ``[image — N KB stripped]`` placeholders. Use this only when
          there's literally nowhere safe to write (rare; should mostly
          never fire in production).

    Output is hard-capped at ``_MAX_OUTPUT_CHARS`` (200 KB) with a
    truncation marker — guards us against the 1M-row XLSX → 80 MB of
    pipe-delimited markdown failure mode.
    """
    if not abs_path.exists():
        return ExtractResult(error="file not found")
    if not abs_path.is_file():
        return ExtractResult(error="not a regular file")

    stat = abs_path.stat()
    if stat.st_size > _SIZE_LIMIT:
        mb = stat.st_size / (1024 * 1024)
        return ExtractResult(
            error=f"file too large for markdown extraction ({mb:.1f} MB; cap {_SIZE_LIMIT // (1024 * 1024)} MB)"
        )

    # Validate the (extract_dir, rel_prefix) coupling up front so we
    # fail loudly on misuse rather than silently stripping images.
    extract_to_disk = extract_dir is not None or rel_prefix is not None
    if extract_to_disk and (extract_dir is None or rel_prefix is None):
        return ExtractResult(
            error="extract_dir and rel_prefix must be provided together"
        )
    if extract_to_disk and not extract_dir.is_dir():  # type: ignore[union-attr]
        return ExtractResult(
            error=f"extract_dir does not exist: {extract_dir}"
        )

    # Cache key. Different rel_prefix values legitimately produce
    # different markdown bodies (the inline ``![](…)`` paths differ),
    # so we MUST include it. Stripped-mode shares a single bucket.
    if extract_to_disk:
        mode_tag = f"extract:{rel_prefix}"
    else:
        mode_tag = "stripped"
    cache_key = (str(abs_path.resolve()), stat.st_mtime_ns, stat.st_size, mode_tag)
    cached = _cache_get(cache_key)
    if cached is not None:
        # If the extract dir was deleted since we cached, the cached
        # markdown points at non-existent files — treat as a miss so we
        # rewrite both the markdown and the image files together.
        if extract_to_disk and not extract_dir.is_dir():  # type: ignore[union-attr]
            pass
        else:
            return ExtractResult(markdown=cached, cached=True)

    md = _get_md()
    if md is None:
        # Friendly placeholder so the editor pane shows something useful
        # rather than a generic "Can't show this file" — emphasises that
        # this is a SERVER-side install gap, not a corrupt/blocked file.
        return ExtractResult(
            markdown=(
                f"# {abs_path.name}\n\n"
                "> Inline preview for office documents requires the `markitdown` Python package, "
                "which is not installed in this backend.\n\n"
                "**Install:**\n\n"
                "```bash\n"
                "pip install 'markitdown[pdf,docx,pptx,xlsx,xls,outlook]'\n"
                "```\n\n"
                "After installing, restart the backend and reopen this file."
            ),
        )

    # Run conversion on a worker thread with a hard timeout. We can't use
    # asyncio here because callers (FastAPI route handlers) might run us
    # from inside an event loop and we don't want to leak a thread either
    # way: `Thread.join(timeout)` returns even if the worker is still running,
    # and we drop the result + log a warning.
    result_holder: dict[str, object] = {}

    def _worker() -> None:
        try:
            res = md.convert_local(str(abs_path))  # type: ignore[union-attr]
            text = (res.text_content or "").strip()
            if not text:
                # markitdown returned an empty doc — could be a blank xlsx,
                # a scanned PDF without OCR, etc. Tell the user.
                result_holder["error"] = (
                    "markitdown produced no text — the document may be empty, "
                    "scanned-only (no embedded text), or password-protected."
                )
            else:
                result_holder["markdown"] = text
        except Exception as exc:  # noqa: BLE001 - intentional broad catch
            result_holder["error"] = f"markitdown failed: {exc}"

    t = threading.Thread(target=_worker, daemon=True, name=f"markitdown-{abs_path.name}")
    t.start()
    t.join(timeout=_TIMEOUT_S)
    if t.is_alive():
        logger.warning("markitdown timed out after %.1fs on %s", _TIMEOUT_S, abs_path)
        return ExtractResult(error=f"extraction timed out after {_TIMEOUT_S:.0f}s")

    if "error" in result_holder:
        return ExtractResult(error=str(result_holder["error"]))
    md_text = str(result_holder.get("markdown", ""))

    # ── Post-process ─────────────────────────────────────────────────
    # Order matters: handle images FIRST so the output cap doesn't burn
    # its character budget on base64 payloads we'd discard anyway.
    images_n = 0
    if extract_to_disk:
        md_text, images_n = _extract_inline_images_to_disk(
            md_text, extract_dir=extract_dir, rel_prefix=rel_prefix,  # type: ignore[arg-type]
        )
        if images_n:
            logger.info(
                "extracted %d image(s) from %s → %s",
                images_n, abs_path.name, extract_dir,
            )
    else:
        md_text, n_stripped = _strip_inline_images(md_text)
        if n_stripped:
            logger.debug(
                "stripped %d inline image(s) from %s (no extract_dir)",
                n_stripped, abs_path.name,
            )

    md_text, was_truncated = _apply_output_cap(md_text)
    if was_truncated:
        logger.info(
            "markdown output for %s exceeded %d KB cap; truncated",
            abs_path.name,
            _MAX_OUTPUT_CHARS // 1024,
        )

    _cache_set(cache_key, md_text)
    return ExtractResult(markdown=md_text, images_extracted=images_n)


def extractor_available() -> bool:
    """Cheap check used by /healthz-style endpoints."""
    return _get_md() is not None or os.environ.get("MARKITDOWN_BUNDLED") == "1"
