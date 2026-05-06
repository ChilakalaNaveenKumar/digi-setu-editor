<!--
  UserMessage — chat bubble for the user. Compact card with subtle accent
  rail on the left.

  "↶ revert turn" button (visible on hover) wipes every file change made by
  the agent in response to this prompt. Useful when a turn went off the
  rails: undo the whole reply in one click instead of scrubbing through
  every individual tool card. Backed by /api/turns/{id}/revert (opencode
  pattern).
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { renderMarkdown } from "../lib/markdown";
import { useSessionStore } from "../stores/session";

const props = defineProps<{ id: string; text: string }>();
const html = computed(() => renderMarkdown(props.text));

const store = useSessionStore();
const revertBusy = ref(false);
const revertError = ref<string | null>(null);
const revertedFiles = ref<string[] | null>(null);

async function revertTurn(): Promise<void> {
  if (revertBusy.value) return;
  const ok = window.confirm(
    "Revert every file change the agent made in response to this prompt?\n\n" +
      "Files touched only by other turns are not affected. Your manual edits " +
      "are preserved.",
  );
  if (!ok) return;
  revertBusy.value = true;
  revertError.value = null;
  revertedFiles.value = null;
  try {
    const files = await store.revertTurn(props.id);
    revertedFiles.value = files;
    console.info(`[revert-turn] reverted ${files.length} file(s)`, files);
  } catch (exc) {
    revertError.value = (exc as Error).message;
  } finally {
    revertBusy.value = false;
  }
}
</script>

<template>
  <div class="user-bubble group my-3 rounded-md px-3 py-2">
    <div class="mb-1 flex items-center justify-between">
      <span class="text-[10px] uppercase tracking-wide text-muted-foreground">
        you
      </span>
      <button
        type="button"
        :disabled="revertBusy"
        class="rounded-sm border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground opacity-0 transition-opacity hover:border-destructive/60 hover:text-destructive group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-50"
        title="Revert every file change made in response to this prompt"
        @click="revertTurn"
      >
        {{ revertBusy ? "reverting…" : "↶ revert turn" }}
      </button>
    </div>
    <div class="pi-markdown text-foreground" v-html="html" />
    <div
      v-if="revertedFiles"
      class="mt-1 text-[10px] text-success"
    >
      reverted {{ revertedFiles.length }} file{{ revertedFiles.length === 1 ? "" : "s" }}
    </div>
    <div
      v-if="revertError"
      class="mt-1 text-[10px] text-destructive"
    >
      {{ revertError }}
    </div>
  </div>
</template>
