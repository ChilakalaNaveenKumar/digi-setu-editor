import { apiDelete, apiJson, apiPost } from "./client";
import type { PtyTerminal, ShellProfile } from "./types";

/**
 * PTY terminal REST endpoints.
 *
 * Shell-profile discovery stays global (it's a host-level question). All
 * other terminal operations are scoped to a workspace, mirroring the
 * server-side per-workspace PtyHub. The byte-stream WS is still
 * `/ws/terminal/{term_id}` (term ids are uuids, no wsid needed in the
 * URL).
 */
export function listShellProfiles(): Promise<{ profiles: ShellProfile[] }> {
  return apiJson("/api/terminals/profiles");
}

export function listTerminals(wsid: string): Promise<{ terminals: PtyTerminal[] }> {
  return apiJson(`/api/workspaces/${encodeURIComponent(wsid)}/terminals`);
}

export function createTerminal(
  wsid: string,
  opts: {
    shell?: string;
    cwd?: string;
    cols?: number;
    rows?: number;
  },
): Promise<PtyTerminal> {
  return apiPost(`/api/workspaces/${encodeURIComponent(wsid)}/terminals`, opts);
}

export function deleteTerminal(wsid: string, termId: string): Promise<{ ok: true }> {
  return apiDelete(
    `/api/workspaces/${encodeURIComponent(wsid)}/terminals/${encodeURIComponent(termId)}`,
  );
}
