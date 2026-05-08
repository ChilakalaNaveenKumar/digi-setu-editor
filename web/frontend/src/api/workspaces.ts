import { apiDelete, apiJson, apiPatch, apiPost } from "./client";
import type { WorkspaceRecord } from "./types";

export function listWorkspaces(): Promise<{ workspaces: WorkspaceRecord[] }> {
  return apiJson("/api/workspaces");
}

export function createWorkspace(opts: { name?: string; path?: string } = {}): Promise<WorkspaceRecord> {
  return apiPost("/api/workspaces", opts);
}

export function renameWorkspace(wsid: string, name: string): Promise<WorkspaceRecord> {
  return apiPatch(`/api/workspaces/${encodeURIComponent(wsid)}`, { name });
}

export function deleteWorkspace(wsid: string): Promise<{ ok: true; workspace: WorkspaceRecord }> {
  return apiDelete(`/api/workspaces/${encodeURIComponent(wsid)}`);
}
