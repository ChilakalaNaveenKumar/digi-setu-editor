import { apiJson, apiPost } from "./client";
import type { BackgroundProcessInfo } from "./types";

/**
 * Per-workspace background-process API. The server-side registry is now
 * scoped to a workspace id (every workspace gets its own); listings and
 * kills here are accordingly workspace-targeted. There is no cross-
 * workspace view from the browser.
 */
export function listBgProcesses(
  wsid: string,
): Promise<{ processes: BackgroundProcessInfo[] }> {
  return apiJson(`/api/workspaces/${encodeURIComponent(wsid)}/bg`);
}

export function killBgProcess(
  wsid: string,
  processId: string,
): Promise<{ ok: boolean }> {
  return apiPost(
    `/api/workspaces/${encodeURIComponent(wsid)}/bg/${encodeURIComponent(processId)}/kill`,
  );
}
