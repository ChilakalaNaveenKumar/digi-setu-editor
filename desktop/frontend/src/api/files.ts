/**
 * Workspace file operations. Every endpoint is workspace-scoped, so we
 * accept `wsid` first; callers pass the active workspace from the store.
 */

import { apiDelete, apiJson, apiPost, authBlobUrl, downloadAuthed, getApiBase } from "./client";
import type { FileContent, FileEntry } from "./types";

const _ws = (wsid: string, suffix: string) =>
  `/api/workspaces/${encodeURIComponent(wsid)}${suffix}`;

export function listFiles(wsid: string): Promise<{ items: FileEntry[] }> {
  return apiJson(_ws(wsid, "/files"));
}

export function readFile(wsid: string, path: string): Promise<FileContent> {
  return apiJson(_ws(wsid, `/files/content?path=${encodeURIComponent(path)}`));
}

/**
 * Build an absolute URL to the workspace's raw-file endpoint.
 *
 * IMPORTANT: this URL is consumed by `<img>`, `<iframe>`, `<audio>`,
 * `<video>` and similar elements that set `src` directly. Those tags
 * resolve relative URLs against `window.location`, which in the
 * Tauri webview is `tauri://localhost/...` — NOT the loopback FastAPI
 * sidecar. Without the API-base prefix, every binary preview ends up
 * fetching `tauri://localhost/api/workspaces/.../files/raw` and the
 * browser shows a broken-image / empty-PDF placeholder.
 *
 * `apiJson` callers don't need this because `_request()` rewrites the
 * URL via `_absolutize()` before calling `fetch`. `<img>` doesn't have
 * that hook so we have to embed the absolute base ourselves.
 *
 * In web mode `getApiBase()` returns "" and the URL stays relative —
 * which is the right answer there because Caddy reverse-proxies
 * `/api/*` same-origin.
 */
export function rawFileUrl(wsid: string, path: string): string {
  return `${getApiBase()}${_ws(wsid, `/files/raw?path=${encodeURIComponent(path)}`)}`;
}

/**
 * Auth-aware preview URL. Fetches `/files/raw` with the Bearer token,
 * wraps the response Blob in `URL.createObjectURL()`. Used for elements
 * that can't carry custom headers (`<iframe>`, `<audio>`, `<video>`).
 *
 * In desktop mode the sidecar is on a localhost port without strict auth
 * (Clerk is bypassed when CLERK_SECRET_KEY is unset), so this still
 * works there even if the auth header is empty — the relative path goes
 * through `_request()` which `_absolutize`s it to the sidecar.
 *
 * Caller MUST `URL.revokeObjectURL()` when the preview unmounts.
 */
export function rawFileBlobUrl(wsid: string, path: string): Promise<string> {
  return authBlobUrl(_ws(wsid, `/files/raw?path=${encodeURIComponent(path)}`));
}

/**
 * Trigger a browser download of a workspace file with auth. Same behaviour
 * as the web edition; on desktop the Save-As dialog is rendered by the
 * Tauri webview which forwards to the OS file picker.
 */
export function downloadFile(wsid: string, path: string): Promise<void> {
  return downloadAuthed(
    _ws(wsid, `/files/raw?path=${encodeURIComponent(path)}&download=1`),
    path.split("/").pop() || "file"
  );
}

/**
 * Markdown preview for office documents (docx/xlsx/pptx/csv/eml/...).
 * Backend runs Microsoft's markitdown server-side and returns the
 * markdown string for the frontend to render with the chat-message
 * markdown renderer.
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
