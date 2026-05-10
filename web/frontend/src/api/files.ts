/**
 * Workspace file operations. Every endpoint is workspace-scoped, so we
 * accept `wsid` first; callers pass the active workspace from the store.
 */

import { apiDelete, apiJson, apiPost, authArrayBuffer, authBlobUrl, downloadAuthed } from "./client";
import type { FileContent, FileEntry } from "./types";

const _ws = (wsid: string, suffix: string) =>
  `/api/workspaces/${encodeURIComponent(wsid)}${suffix}`;

export function listFiles(wsid: string): Promise<{ items: FileEntry[] }> {
  return apiJson(_ws(wsid, "/files"));
}

export function readFile(wsid: string, path: string): Promise<FileContent> {
  return apiJson(_ws(wsid, `/files/content?path=${encodeURIComponent(path)}`));
}

export function rawFileUrl(wsid: string, path: string): string {
  return _ws(wsid, `/files/raw?path=${encodeURIComponent(path)}`);
}

/**
 * Auth-aware preview URL. Fetches `/files/raw` with the current Bearer
 * token, wraps the response Blob in `URL.createObjectURL()`, and returns
 * the resulting `blob:` URL. Use this for `<iframe>`/`<audio>`/`<video>`
 * elements which can't carry custom headers — without this hop the
 * backend rejects the request with 401 and the browser surfaces it as
 * "refused to connect" / a blank PDF area.
 *
 * Callers MUST call `URL.revokeObjectURL()` on the returned URL when
 * the element is unmounted; otherwise the underlying Blob stays in
 * memory for the lifetime of the document. See FilePreview.vue's
 * `onBeforeUnmount` for the canonical pattern.
 */
export function rawFileBlobUrl(wsid: string, path: string): Promise<string> {
  return authBlobUrl(_ws(wsid, `/files/raw?path=${encodeURIComponent(path)}`));
}

/**
 * Fetch the raw bytes of a workspace file with auth and return them as
 * an ArrayBuffer. Used by the in-browser visual viewers
 * (`SpreadsheetPreview`, `WordPreview`, `SqlitePreview`) that need to
 * parse the file directly with `xlsx`, `docx-preview`, or `sql.js`.
 */
export function rawFileBytes(wsid: string, path: string): Promise<ArrayBuffer> {
  return authArrayBuffer(_ws(wsid, `/files/raw?path=${encodeURIComponent(path)}`));
}

/**
 * Trigger a browser download of a workspace file with auth. Drops a
 * temporary `<a download="filename">` link, clicks it, then revokes
 * the blob URL. The user gets the file via the same Save-As dialog as
 * any other web download.
 */
export function downloadFile(wsid: string, path: string): Promise<void> {
  // We hit the same `/files/raw` route but with `download=1` so the
  // backend swaps `Content-Disposition: inline` → `attachment`. The
  // browser uses the filename from there as the suggested download
  // name (so a "report.docx" inside a workspace stays "report.docx").
  return downloadAuthed(
    _ws(wsid, `/files/raw?path=${encodeURIComponent(path)}&download=1`),
    path.split("/").pop() || "file"
  );
}

/**
 * Markdown preview for office documents (docx/xlsx/pptx/csv/eml/...).
 * The backend runs Microsoft's markitdown server-side and returns
 * `{ markdown, error, cached }`. Caller renders the markdown string
 * with the same `renderMarkdown()` we use for chat messages.
 */
export function previewMarkdown(
  wsid: string,
  path: string
): Promise<{ path: string; markdown: string | null; error: string | null; cached: boolean }> {
  return apiJson(_ws(wsid, `/files/preview-md?path=${encodeURIComponent(path)}`));
}

export function writeFile(
  wsid: string,
  path: string,
  content: string,
  overwrite = true
): Promise<FileEntry> {
  return apiPost(_ws(wsid, "/fs/file"), { path, content, overwrite });
}

export function createFile(wsid: string, path: string, content = ""): Promise<FileEntry> {
  return apiPost(_ws(wsid, "/fs/file"), { path, content, overwrite: false });
}

export function createFolder(wsid: string, path: string): Promise<FileEntry> {
  return apiPost(_ws(wsid, "/fs/folder"), { path });
}

export function deletePath(wsid: string, path: string): Promise<{ deleted: true }> {
  return apiDelete(_ws(wsid, `/fs/path?path=${encodeURIComponent(path)}`));
}

export function renamePath(wsid: string, from: string, to: string): Promise<FileEntry> {
  return apiPost(_ws(wsid, "/fs/rename"), { from, to });
}

export function copyPath(wsid: string, from: string, to?: string): Promise<FileEntry> {
  return apiPost(_ws(wsid, "/fs/copy"), { from, to });
}

export function movePath(wsid: string, from: string, to: string): Promise<FileEntry> {
  return apiPost(_ws(wsid, "/fs/move"), { from, to });
}
