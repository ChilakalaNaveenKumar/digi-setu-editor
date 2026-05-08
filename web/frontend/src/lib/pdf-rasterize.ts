/**
 * PDF page rasterizer.
 *
 * Loads pdfjs-dist on demand (it's ~400 kB gzipped, so we lazy-import
 * it the first time the user clicks "Annotate" on a PDF). Returns a
 * data URL of the requested page rendered at the requested DPR-scaled
 * dimensions.
 *
 * Why not let the user annotate the iframe directly? The browser's
 * built-in PDF viewer is sandboxed inside the <iframe> — we cannot
 * overlay a canvas onto its rendered page without breaking same-origin,
 * and we cannot read the rendered pixels back via html2canvas (it
 * skips iframe content). Re-rendering with pdf.js gives us pixels we
 * fully own.
 *
 * Worker resolution: pdf.js needs a worker URL. Vite's `?worker&url`
 * query gives us a hashed-asset URL that survives the build pipeline,
 * so the worker resolves correctly in dev AND prod without any
 * workerSrc gymnastics.
 */

// Vite-specific syntax — resolves to a build-time asset URL.
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import * as pdfjsLib from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

export interface RasterizeOptions {
  /** 1-based page number. Defaults to the first page. */
  page?: number;
  /** Output bitmap scale. 2 ≈ retina; higher = sharper PNG, larger file. */
  scale?: number;
}

export interface RasterizeResult {
  dataUrl: string;
  page: number;
  pageCount: number;
  width: number;
  height: number;
}

/**
 * Render a single PDF page from a URL into a PNG data URL.
 *
 * Throws if the URL can't be fetched, the PDF is corrupt, or the
 * requested page is out of range. Always-tear-down: the underlying
 * pdf document is destroyed before returning so we don't keep its
 * worker memory live across many invocations.
 */
export async function rasterizePdfPage(
  url: string,
  opts: RasterizeOptions = {},
): Promise<RasterizeResult> {
  const scale = opts.scale ?? 2;
  const requestedPage = Math.max(1, Math.floor(opts.page ?? 1));

  const loadingTask = pdfjsLib.getDocument({
    url,
    // disableFontFace: false is the default; we leave it so embedded
    // fonts render correctly. typst PDFs may reference remote fonts;
    // pdf.js handles those with same-origin policy and falls back to
    // its bundled standard fonts for any that fail.
    disableFontFace: false,
  });
  const doc = await loadingTask.promise;
  try {
    const page = Math.min(requestedPage, doc.numPages);
    const pdfPage = await doc.getPage(page);
    const viewport = pdfPage.getViewport({ scale });
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas 2d context unavailable");

    // pdf.js render() takes a CanvasRenderingContext2D for the canvas
    // we want it to paint into. The promise resolves when the page
    // is fully rendered (text + vector + raster layers).
    await pdfPage.render({ canvas, canvasContext: ctx, viewport }).promise;
    pdfPage.cleanup();

    return {
      dataUrl: canvas.toDataURL("image/png"),
      page,
      pageCount: doc.numPages,
      width: canvas.width,
      height: canvas.height,
    };
  } finally {
    // Destroy the document and its worker so memory doesn't pile up.
    await doc.destroy().catch(() => undefined);
  }
}

/**
 * Quick page-count probe without rendering anything. Used by
 * FilePreview to decide whether to show a page picker.
 */
export async function pdfPageCount(url: string): Promise<number> {
  const doc = await pdfjsLib.getDocument({ url }).promise;
  try {
    return doc.numPages;
  } finally {
    await doc.destroy().catch(() => undefined);
  }
}
