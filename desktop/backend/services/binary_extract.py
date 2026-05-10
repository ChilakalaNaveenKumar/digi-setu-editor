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
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level singleton so we don't pay the (slow) plugin scan on every call.
_md_singleton: Optional[object] = None
_md_lock = threading.Lock()
_MD_IMPORT_ERR: Optional[str] = None

# Result cache: (abs_path_str, mtime_ns, size) -> markdown
# Bounded by `_CACHE_MAX` entries; LRU eviction (insertion-ordered dict).
_cache: dict[tuple[str, int, int], str] = {}
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


@dataclass
class ExtractResult:
    """Either `markdown` is set, or `error` is — never both."""
    markdown: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False


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


def _cache_get(key: tuple[str, int, int]) -> Optional[str]:
    with _cache_lock:
        return _cache.get(key)


def _cache_set(key: tuple[str, int, int], md: str) -> None:
    with _cache_lock:
        if key in _cache:
            del _cache[key]
        _cache[key] = md
        if len(_cache) > _CACHE_MAX:
            # Drop oldest entry (insertion-ordered dict).
            oldest = next(iter(_cache))
            del _cache[oldest]


def extract_to_markdown(abs_path: Path) -> ExtractResult:
    """
    Convert an office/PDF/etc. file at `abs_path` to Markdown.

    Caller is responsible for path safety; this helper trusts the absolute
    path it's given. Returns an `ExtractResult` with either `markdown` or
    `error` populated.
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

    cache_key = (str(abs_path.resolve()), stat.st_mtime_ns, stat.st_size)
    cached = _cache_get(cache_key)
    if cached is not None:
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
    _cache_set(cache_key, md_text)
    return ExtractResult(markdown=md_text)


def extractor_available() -> bool:
    """Cheap check used by /healthz-style endpoints."""
    return _get_md() is not None or os.environ.get("MARKITDOWN_BUNDLED") == "1"
