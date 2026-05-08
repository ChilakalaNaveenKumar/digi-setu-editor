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
  return apiJson(`/api/sessions/${encodeURIComponent(sid)}/history`);
}
