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

// ── Storage rolling 90-day cycle (auto-cleanup) ──────────────────────────
//
// Web policy: every 90 days, sweep all user-removable artifacts (chats,
// audits, uploads) older than the cycle window. The SPA shows a banner
// 5 days before the next sweep with a "you can clean now" / "snooze"
// affordance.
//
//   * `getStorageCycle` is cheap to call on every page-load — it walks
//     records but doesn't touch disk for individual files. Returns the
//     banner state + per-category pending counts.
//   * `runStorageCycle({force: true})` is the manual "Clean now" button:
//     runs immediately even if not due. Without `force`, the call is a
//     scheduled tick — no-ops when the cycle isn't due.
//
// See web/backend/services/chat_storage.py for the cycle math.

export interface CategoryPending {
  count: number;
  bytes: number;
}

export interface CyclePending {
  total_count: number;
  total_bytes: number;
  chats: CategoryPending;
  audits: CategoryPending;
  uploads: CategoryPending;
}

export interface CycleStatus {
  cycle_days: number;
  banner_lead_days: number;
  next_cycle_at: string;
  last_cycle_at: string | null;
  days_until_cycle: number;
  show_banner: boolean;
  pending: CyclePending;
}

export interface CategoryCleanupResult {
  deleted_count: number;
  freed_bytes: number;
  deleted_ids: string[];
}

export interface CycleRunResult {
  ran: boolean;
  reason?: string;
  ran_at?: string;
  next_cycle_at: string;
  results: Partial<Record<"chats" | "audits" | "uploads", CategoryCleanupResult>>;
}

export function getStorageCycle(): Promise<CycleStatus> {
  return apiJson("/api/storage/cycle");
}

export function runStorageCycle(force = true): Promise<CycleRunResult> {
  return apiPost("/api/storage/cycle/run", { force });
}

// Legacy keep-newest-100 endpoints — retained for the period during
// which both old and new SPA bundles may be in user caches. Once the
// cycle UI is everywhere we can drop these.
export interface WorkspaceStorageStats {
  keep: number;
  total_chats: number;
  eligible_chats: number;
  eligible_bytes: number;
  scope: "workspace" | "global";
  oldest_kept_at?: string | null;
}

export interface WorkspaceCleanupResult {
  deleted_count: number;
  freed_bytes: number;
  deleted_ids: string[];
}

export function getWorkspaceStorage(wsid: string): Promise<WorkspaceStorageStats> {
  return apiJson(`/api/workspaces/${encodeURIComponent(wsid)}/storage`);
}

export function cleanupWorkspaceStorage(wsid: string): Promise<WorkspaceCleanupResult> {
  return apiPost(`/api/workspaces/${encodeURIComponent(wsid)}/storage/cleanup`, {});
}
