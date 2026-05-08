/**
 * Per-tool-call diff review + restore + revert.
 *
 * Source of truth = backend shadow-git (Cline / Roo Code / Aider pattern).
 * We never reconstruct diffs locally except as a fallback when the
 * backend has no snapshot (legacy session, in-flight write, error case).
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import * as snapshotsApi from "../api/snapshots";
import { parseDiff } from "../lib/diff-parse";
import { piDiffToUnified, writeContentToUnified } from "../lib/pi-diff-to-unified";
import type { ToolCall } from "../types/rpc";

import { useChatStore } from "./chat";
import { useFilesStore, normalizeWorkspacePath } from "./files";
import { useUiStore } from "./ui";
import { useWorkspaceStore } from "./workspace";

export interface EditorReview {
  toolCallId: string;
  toolName: "write" | "edit";
  path: string;
  unifiedDiff: string;
  added: number;
  removed: number;
  status: ToolCall["status"];
}

function _countDiffStats(unified: string): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  for (const line of unified.split("\n")) {
    if (line.startsWith("+++") || line.startsWith("---")) continue;
    if (line.startsWith("+")) added++;
    else if (line.startsWith("-")) removed++;
  }
  return { added, removed };
}

export const useSnapshotsStore = defineStore("snapshots", () => {
  const ui = useUiStore();
  const workspace = useWorkspaceStore();
  const files = useFilesStore();

  const editorReview = ref<EditorReview | null>(null);

  function _wsid(): string {
    const id = workspace.activeId;
    if (!id) throw new Error("no active workspace");
    return id;
  }

  function _findToolCall(toolCallId: string): ToolCall | null {
    const chat = useChatStore();
    for (const m of chat.messages) {
      if (m.kind !== "assistant") continue;
      const tc = m.toolCalls.find((c) => c.id === toolCallId);
      if (tc) return tc;
    }
    return null;
  }

  /**
   * Show the full unified diff for a single write/edit call in the editor
   * pane. Tries the backend snapshot first; falls back to synthesizing
   * one from the call's args if the snapshot is missing.
   */
  async function enterReviewMode(toolCallId: string): Promise<void> {
    const tc = _findToolCall(toolCallId);
    if (!tc || (tc.name !== "write" && tc.name !== "edit")) return;

    let path = "";
    let unifiedDiff = "";
    let added = 0;
    let removed = 0;

    try {
      const payload = await snapshotsApi.getDiff(_wsid(), toolCallId);
      const ud = (payload as { unified_diff?: string }).unified_diff ?? "";
      const ph = (payload as { path?: string }).path ?? "";
      if (typeof ud === "string" && ud.trim()) {
        unifiedDiff = ud;
        path = normalizeWorkspacePath(ph);
        const stats = _countDiffStats(unifiedDiff);
        added = stats.added;
        removed = stats.removed;
      }
    } catch (err) {
      console.warn(`[review] snapshot fetch failed for ${toolCallId}:`, err);
    }

    if (!unifiedDiff) {
      if (tc.name === "write") {
        const args = tc.args as { path?: unknown; content?: unknown } | undefined;
        const rawPath = typeof args?.path === "string" ? args.path : "";
        const content = typeof args?.content === "string" ? args.content : "";
        path = normalizeWorkspacePath(rawPath);
        if (!path || !content) return;
        unifiedDiff = writeContentToUnified(content, path);
        const lines = content.split("\n");
        added = lines.length > 1 && lines[lines.length - 1] === "" ? lines.length - 1 : lines.length;
      } else {
        const args = tc.args as { path?: unknown } | undefined;
        const rawPath = typeof args?.path === "string" ? args.path : "";
        path = normalizeWorkspacePath(rawPath);
        const details = tc.result?.details as { diff?: unknown } | undefined;
        const piDiff = typeof details?.diff === "string" ? details.diff : "";
        if (!path || !piDiff) return;
        unifiedDiff = piDiffToUnified(piDiff, path);
        const parsed = parseDiff(piDiff);
        added = parsed.added;
        removed = parsed.removed;
      }
    }

    if (!unifiedDiff) return;

    editorReview.value = {
      toolCallId,
      toolName: tc.name as "write" | "edit",
      path,
      unifiedDiff,
      added,
      removed,
      status: tc.status,
    };
  }

  function exitReviewMode(): void {
    editorReview.value = null;
  }

  async function _refreshAfterMutation(restored: string[]): Promise<void> {
    editorReview.value = null;
    await files.refreshTree();
    const open = files.currentFile;
    if (open && restored.includes(open.path)) {
      await files.openFile(open.path).catch(() => {
        /* openFile sets status='error' itself. */
      });
    }
  }

  async function restoreToolCall(toolCallId: string): Promise<string[]> {
    try {
      const data = await snapshotsApi.restoreToolCall(_wsid(), toolCallId);
      const restored = data.restored_files ?? [];
      await _refreshAfterMutation(restored);
      return restored;
    } catch (exc) {
      ui.toastError("Restore failed", exc);
      return [];
    }
  }

  async function revertTurn(userMessageId: string): Promise<string[]> {
    try {
      const data = await snapshotsApi.revertTurn(_wsid(), userMessageId);
      const restored = data.restored_files ?? [];
      await _refreshAfterMutation(restored);
      return restored;
    } catch (exc) {
      ui.toastError("Revert failed", exc);
      return [];
    }
  }

  return {
    editorReview,
    enterReviewMode,
    exitReviewMode,
    restoreToolCall,
    revertTurn,
  };
});
