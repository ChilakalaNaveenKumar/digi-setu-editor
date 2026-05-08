/**
 * Pending tool-call permission requests.
 *
 * The backend forwards every approve_risky / approve_all gate as a
 * `permission_request` WS event. We queue them here (FIFO) and the
 * <PermissionPrompt /> modal renders the head of the queue.
 *
 * Decisions go back over the same WebSocket via chat.sendPermissionResponse.
 * We keep this store dumb on purpose — no fetch, no side effects beyond
 * queue mutation — so the dispatcher in chat.ts is the single chokepoint
 * for incoming events and the modal is the single chokepoint for outgoing
 * decisions.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

export type PermissionDecision =
  | "allow_once"
  | "allow_session"
  | "deny_once"
  | "deny_session";

export type PermissionMode = "auto" | "approve_risky" | "approve_all";

export interface PermissionPreview {
  kind: "diff";
  oldText: string;
  newText: string;
  filePath: string;
}

export interface PermissionRequest {
  id: string;
  tool: string;
  toolCallId?: string;
  input: Record<string, unknown>;
  intent: string;
  preview?: PermissionPreview;
  mode: PermissionMode;
  receivedAt: number;
}

export const usePermissionsStore = defineStore("permissions", () => {
  const queue = ref<PermissionRequest[]>([]);
  const sessionMode = ref<PermissionMode>("approve_risky");

  const current = computed<PermissionRequest | null>(
    () => queue.value[0] ?? null,
  );
  const pendingCount = computed(() => queue.value.length);

  function enqueue(req: Omit<PermissionRequest, "receivedAt">): void {
    queue.value = [...queue.value, { ...req, receivedAt: Date.now() }];
  }

  /** Drop the head of the queue. Caller is responsible for sending the
   * decision over the WS first — we just manage local state. */
  function dequeue(id: string): PermissionRequest | null {
    const idx = queue.value.findIndex((r) => r.id === id);
    if (idx < 0) return null;
    const taken = queue.value[idx];
    queue.value = queue.value.filter((_, i) => i !== idx);
    return taken;
  }

  /** Wipe everything. Called when the chat session disconnects so a
   * stale modal doesn't survive into the next session. */
  function clear(): void {
    queue.value = [];
  }

  function setMode(mode: PermissionMode): void {
    sessionMode.value = mode;
  }

  return {
    queue,
    sessionMode,
    current,
    pendingCount,
    enqueue,
    dequeue,
    clear,
    setMode,
  };
});
