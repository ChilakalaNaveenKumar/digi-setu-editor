/**
 * Attachments API client.
 *
 * One endpoint, multipart upload. Shared by every "user shared a file"
 * ingress point in the UI:
 *   • composer paperclip button
 *   • clipboard paste in the chat region
 *   • drag-drop onto the chat region
 *   • drag-drop onto a file-tree row (with a custom target_dir)
 *
 * The response carries two paths per file:
 *   • `path`       — workspace-relative, what the file tree uses.
 *                    Example: "uploads/foo.png".
 *   • `agent_path` — agent-cwd-relative, what we feed back to pi in
 *                    the next user prompt. Example: "workspace/uploads/foo.png".
 */

import { apiPostForm } from "./client";

export interface SavedAttachment {
  /** Workspace-relative path (no `workspace/` prefix). Used by the file tree. */
  path: string;
  /** Agent-cwd-relative path. Used by the composer when prepending to the prompt. */
  agent_path: string;
  /** Original basename after sanitisation. */
  name: string;
  /** Bytes written. */
  size: number;
  /** MIME type as reported by the browser. */
  mime: string;
  /** Absolute path on the backend disk (debug; not displayed). */
  absolute?: string;
}

export interface UploadResult {
  saved: SavedAttachment[];
  target_dir: string;
}

/**
 * Upload a list of files to a workspace.
 *
 * @param wsid       target workspace
 * @param files      list of File objects (input picker / drop / clipboard)
 * @param targetDir  workspace-relative folder; backend defaults to "uploads"
 *                   when omitted
 */
export async function uploadAttachments(
  wsid: string,
  files: File[],
  targetDir?: string,
): Promise<UploadResult> {
  if (files.length === 0) {
    return { saved: [], target_dir: targetDir || "uploads" };
  }
  const fd = new FormData();
  for (const f of files) fd.append("files", f, f.name);
  if (targetDir && targetDir.trim()) fd.append("target_dir", targetDir.trim());

  return apiPostForm<UploadResult>(
    `/api/workspaces/${encodeURIComponent(wsid)}/attachments`,
    fd,
  );
}
