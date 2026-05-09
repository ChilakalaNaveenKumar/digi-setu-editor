/**
 * Pending tool-call permission requests.
 *
 * The backend forwards every gated tool call (see permission mode
 * matrix below) as a `permission_request` WS event. We queue them
 * here (FIFO) and the <PermissionPrompt /> modal renders the head of
 * the queue.
 *
 * Decisions go back over the same WebSocket via chat.sendPermission-
 * Response. We keep this store dumb on purpose — no fetch, no side
 * effects beyond queue mutation — so the dispatcher in chat.ts is the
 * single chokepoint for incoming events and the modal is the single
 * chokepoint for outgoing decisions.
 *
 * Permission modes (canonical IDs):
 *   auto      Run every tool without asking; audit log records all.
 *   ask       Ask before bash / write / edit / process. Reads silent.
 *             (Default — matches Cursor / Cline / Claude Code default.)
 *   cautious  Ask before every tool call, including reads.
 *
 * Legacy IDs (`approve_risky` ≡ `ask`, `approve_all` ≡ `cautious`)
 * are accepted on input and remapped in the backend's user_prefs
 * service so a stale prefs.json keeps working through the upgrade.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

export type PermissionDecision =
  | "allow_once"
  | "allow_session"
  | "deny_once"
  | "deny_session";

export type PermissionMode = "auto" | "ask" | "cautious";

/** Map any legacy mode ID we receive over the wire to the canonical one. */
export function normalizeMode(raw: string): PermissionMode {
  switch (raw) {
    case "auto":
    case "ask":
    case "cautious":
      return raw;
    case "approve_risky":
      return "ask";
    case "approve_all":
      return "cautious";
    default:
      return "ask";
  }
}

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
  const sessionMode = ref<PermissionMode>("ask");

  const current = computed<PermissionRequest | null>(
    () => queue.value[0] ?? null,
  );
  const pendingCount = computed(() => queue.value.length);

  function enqueue(req: Omit<PermissionRequest, "receivedAt">): void {
    // Defensive: an in-flight server may still emit a legacy mode ID
    // for the first request after upgrade. Normalize before storing
    // so the UI never sees a raw `approve_risky` token.
    const safeMode = normalizeMode(req.mode);
    queue.value = [
      ...queue.value,
      { ...req, mode: safeMode, receivedAt: Date.now() },
    ];
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

  function setMode(mode: PermissionMode | string): void {
    sessionMode.value = normalizeMode(mode);
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
