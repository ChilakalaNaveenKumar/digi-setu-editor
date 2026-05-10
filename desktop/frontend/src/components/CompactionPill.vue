<!--
  CompactionPill — small banner that surfaces pi auto-compaction.

  Pi-mono summarises the conversation when its context approaches
  `contextWindow - reserveTokens` (default ~16k). The summary IS
  persisted to pi's session JSONL and IS what gets sent on subsequent
  prompts — pi handles all of this transparently. This pill exists so
  the user can SEE that history is being summarised; otherwise the
  feature is invisible and users worry that earlier context was lost.

  States rendered (driven by `chat.compactionState`):
    - active=true                  → spinner + "Summarising long history…"
    - active=false, succeeded=true → checkmark + "History summarised"
    - active=false, succeeded=false → warning + error message
  When the post-success badge has been on screen for ~8s the chat
  store auto-clears `compactionState` so the pill disappears.

  Mirrors web/frontend/src/components/CompactionPill.vue.
-->
<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";

import { useChatStore } from "../stores/chat";

const chat = useChatStore();
const { compactionState } = storeToRefs(chat);

const visible = computed(() => compactionState.value !== null);

const tone = computed<"info" | "success" | "error">(() => {
  const cs = compactionState.value;
  if (!cs) return "info";
  if (cs.active) return "info";
  if (cs.succeeded === false) return "error";
  return "success";
});

const icon = computed(() => {
  const cs = compactionState.value;
  if (!cs) return "";
  if (cs.active) return "codicon:sync";
  if (cs.succeeded === false) return "codicon:warning";
  return "codicon:check";
});

const message = computed<string>(() => {
  const cs = compactionState.value;
  if (!cs) return "";
  if (cs.active) {
    return cs.reason === "overflow"
      ? "Conversation hit the context limit — summarising older messages so we can keep going…"
      : "Long chat — summarising older messages so the next reply has room to breathe…";
  }
  if (cs.succeeded === false) {
    return cs.errorMessage
      ? `Couldn't summarise older messages: ${cs.errorMessage}`
      : "Couldn't summarise older messages.";
  }
  return "Older messages were summarised. Pi keeps the summary as context for what comes next.";
});

const toneClass = computed(() => {
  switch (tone.value) {
    case "success":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
    case "error":
      return "border-destructive/40 bg-destructive/10 text-destructive";
    default:
      return "border-amber-500/30 bg-amber-500/10 text-amber-300";
  }
});

function dismiss(): void {
  chat.dismissCompaction();
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0 -translate-y-1"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="visible"
      class="pointer-events-auto mx-auto mt-2 flex w-fit max-w-[36rem] items-center gap-2 rounded-full border px-3 py-1.5 text-xs shadow-sm"
      :class="toneClass"
      role="status"
      aria-live="polite"
    >
      <Icon
        :icon="icon"
        class="h-3.5 w-3.5 flex-none"
        :class="tone === 'info' && compactionState?.active ? 'animate-spin' : ''"
      />
      <span class="leading-snug">{{ message }}</span>
      <button
        v-if="!compactionState?.active"
        type="button"
        class="ml-1 rounded-full p-0.5 text-current/70 transition hover:bg-current/10"
        aria-label="Dismiss summarisation notice"
        @click="dismiss"
      >
        <Icon icon="codicon:close" class="h-3 w-3" />
      </button>
    </div>
  </Transition>
</template>
