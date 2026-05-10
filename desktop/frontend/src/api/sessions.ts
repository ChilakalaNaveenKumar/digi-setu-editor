import type { ChatMessage } from "../types/rpc";
import { apiDelete, apiJson, apiPatch, apiPost } from "./client";
import type { SessionRecord } from "./types";

export function listSessions(wsid: string): Promise<{ sessions: SessionRecord[] }> {
  return apiJson(`/api/workspaces/${encodeURIComponent(wsid)}/sessions`);
}

export function createSession(
  wsid: string,
  title = "",
  model: string | null = null,
): Promise<SessionRecord> {
  return apiPost(`/api/workspaces/${encodeURIComponent(wsid)}/sessions`, {
    title,
    model: model || undefined,
  });
}

export function renameSession(sid: string, title: string): Promise<SessionRecord> {
  return apiPatch(`/api/sessions/${encodeURIComponent(sid)}`, { title });
}

export function deleteSession(sid: string): Promise<{ ok: true; session: SessionRecord }> {
  return apiDelete(`/api/sessions/${encodeURIComponent(sid)}`);
}

/**
 * Fetch the persisted message stream for `sid`, in render-ready ChatMessage
 * shape (the backend projects pi's JSONL log directly into this format —
 * see backend/services/history.py). Used by the chat store on resume to
 * paint old turns before opening a fresh WS.
 */
export function fetchSessionHistory(sid: string): Promise<{ messages: ChatMessage[] }> {
  return apiJson(`/api/sessions/${encodeURIComponent(sid)}/history`, {
    cache: "no-store",
  });
}

// ── Per-workspace storage cleanup (multi-category) ────────────────────────
//
// Each desktop workspace exposes 4 storage categories the user can clean:
//
//   chats   — newest-100 keep; old sessions (rest) are deletion-eligible.
//   audits  — JSONL of every AI tool call. 90-day age trim.
//   uploads — files in <ws>/uploads/. 30-day age trim by mtime.
//   shadows — DESTRUCTIVE. Wipes the AI revert history for this workspace.
//             Surface only behind a prominent confirm dialog.
//
// `getWorkspaceStorage` is safe to call on every panel open — it's a pure
// stat, does NOT delete anything. Returns `{workspace_id, categories: [...]}`,
// where each category carries its own shape (counts, bytes, retention policy).
//
// `cleanupWorkspaceStorage(wsid, categories)` actually deletes. Wire ONLY
// behind explicit user confirmation. Multi-select: `categories` is the
// array of category names the user ticked.
//
// See desktop/backend/services/chat_storage.py for the per-category policy.

export interface ChatsCategoryStats {
  category: "chats";
  keep: number;
  total_chats: number;
  eligible_chats: number;
  eligible_bytes: number;
  scope: "workspace";
  oldest_kept_at?: string | null;
}

export interface AuditsCategoryStats {
  category: "audits";
  days_to_keep: number;
  total_rows: number;
  eligible_rows: number;
  eligible_bytes: number;
  total_bytes: number;
}

export interface UploadsCategoryStats {
  category: "uploads";
  days_to_keep: number;
  total_files: number;
  eligible_files: number;
  eligible_bytes: number;
  total_bytes: number;
}

export interface ShadowsCategoryStats {
  category: "shadows";
  destructive: true;
  total_bytes: number;
  eligible_bytes: number;
}

export type StorageCategoryStats =
  | ChatsCategoryStats
  | AuditsCategoryStats
  | UploadsCategoryStats
  | ShadowsCategoryStats;

export interface WorkspaceStorageSummary {
  workspace_id: string;
  categories: StorageCategoryStats[];
}

export interface CategoryCleanupResult {
  deleted_count: number;
  freed_bytes: number;
  deleted_ids: string[];
}

export interface WorkspaceCleanupResult {
  results: Partial<Record<StorageCategoryStats["category"], CategoryCleanupResult>>;
}

export function getWorkspaceStorage(wsid: string): Promise<WorkspaceStorageSummary> {
  return apiJson(`/api/workspaces/${encodeURIComponent(wsid)}/storage`);
}

export function cleanupWorkspaceStorage(
  wsid: string,
  categories: StorageCategoryStats["category"][],
): Promise<WorkspaceCleanupResult> {
  return apiPost(`/api/workspaces/${encodeURIComponent(wsid)}/storage/cleanup`, {
    categories,
  });
}

/**
 * Returns total bytes a category would free if cleaned now. Centralizes the
 * per-category field name so the UI doesn't have to know that "chats" uses
 * `eligible_bytes` while "shadows" uses `eligible_bytes` (same name, different
 * meaning — for shadows it's "the whole thing"). Future-proofs the panel.
 */
export function eligibleBytesFor(cat: StorageCategoryStats): number {
  return cat.eligible_bytes ?? 0;
}

/**
 * Whether a category currently has anything worth cleaning. The Storage panel
 * uses this to disable the per-row checkbox — there's nothing for the user
 * to tick if there's no data of that kind.
 */
export function hasCleanableContent(cat: StorageCategoryStats): boolean {
  switch (cat.category) {
    case "chats":
      return cat.eligible_chats > 0;
    case "audits":
      return cat.eligible_rows > 0;
    case "uploads":
      return cat.eligible_files > 0;
    case "shadows":
      return cat.total_bytes > 0;
  }
}
