/**
 * Workspace file operations. Every endpoint is workspace-scoped, so we
 * accept `wsid` first; callers pass the active workspace from the store.
 */

import { apiDelete, apiJson, apiPost } from "./client";
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
