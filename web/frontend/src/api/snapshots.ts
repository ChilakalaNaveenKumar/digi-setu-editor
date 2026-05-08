import { apiJson, apiPost } from "./client";

export interface DiffPayload {
  tool_call_id: string;
  diff: string;
  files: string[];
}

export interface RestoreResult {
  restored_files: string[];
}

const _ws = (wsid: string, suffix: string) =>
  `/api/workspaces/${encodeURIComponent(wsid)}${suffix}`;

export function getDiff(wsid: string, toolCallId: string): Promise<DiffPayload> {
  return apiJson(_ws(wsid, `/snapshots/${encodeURIComponent(toolCallId)}/diff`));
}

export function restoreToolCall(wsid: string, toolCallId: string): Promise<RestoreResult> {
  return apiPost(_ws(wsid, `/snapshots/${encodeURIComponent(toolCallId)}/restore`));
}

export function revertTurn(wsid: string, userMessageId: string): Promise<RestoreResult> {
  return apiPost(_ws(wsid, `/turns/${encodeURIComponent(userMessageId)}/revert`));
}
