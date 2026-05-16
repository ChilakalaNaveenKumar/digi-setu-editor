/**
 * subagent-panel — single-source-of-truth for "which subagent card is
 * currently expanded in the right-side live drawer?".
 *
 * Why a dedicated store and not local component state:
 *   - SubagentToolCard lives deep inside MessageList; the drawer that
 *     renders the live transcript lives at ChatPane root. Lifting the
 *     state into a store is shorter than prop-drilling 4 layers + an
 *     emit back up.
 *   - Only ONE drawer can be open at a time across the whole chat
 *     (no overlapping side-panels), so a singleton ref is the right
 *     shape — not a Map.
 *   - The chat store already exposes `messages` and `toolCallIndex`
 *     reactively, so the drawer just reads `openCallId`, looks up the
 *     ToolCall, and re-renders on its own when `details.results[*]`
 *     mutates from pi's onUpdate stream. We don't need to push the
 *     details into THIS store.
 *
 * Stays outside `useUiStore` because that one is for toasts + confirm
 * dialogs; keeping subagent-panel separate means a future refactor
 * (e.g. tab-style multi-panel) doesn't have to touch toast plumbing.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

export const useSubagentPanelStore = defineStore("subagent-panel", () => {
  /** ToolCall.id of the subagent card currently shown in the drawer, or null. */
  const openCallId = ref<string | null>(null);

  function open(callId: string): void {
    openCallId.value = callId;
  }

  function close(): void {
    openCallId.value = null;
  }

  /**
   * Open if closed (or showing a different call); close if already
   * showing this exact call. The card's "view live" button uses this
   * so a second click on the same card collapses the drawer.
   */
  function toggle(callId: string): void {
    openCallId.value = openCallId.value === callId ? null : callId;
  }

  return { openCallId, open, close, toggle };
});
