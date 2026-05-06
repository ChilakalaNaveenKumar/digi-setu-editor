<!--
  Composer — bottom prompt input.
    Enter            → newline
    Cmd/Ctrl + Enter → submit
  Disabled while streaming; replaces Send with Abort during a turn.
-->
<script setup lang="ts">
import { ref } from "vue";
import { useSessionStore } from "../stores/session";

const store = useSessionStore();
const text = ref("");

function submit(): void {
  const value = text.value.trim();
  if (!value) return;
  if (store.isStreaming) return;
  store.sendPrompt(value);
  text.value = "";
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    submit();
  }
}
</script>

<template>
  <div class="border-t border-sidebar-border bg-sidebar px-3 py-2">
    <div class="flex items-end gap-2">
      <textarea
        v-model="text"
        rows="3"
        placeholder="Ask the agent…  (⌘/Ctrl + ↵ to send)"
        class="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-ring font-sans"
        :disabled="store.connState !== 'open'"
        @keydown="onKeydown"
      />
      <button
        v-if="!store.isStreaming"
        type="button"
        :disabled="!text.trim() || store.connState !== 'open'"
        class="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition-opacity disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90"
        @click="submit"
      >
        Send
      </button>
      <button
        v-else
        type="button"
        class="rounded-md bg-destructive px-3 py-2 text-sm font-semibold text-destructive-foreground hover:opacity-90"
        @click="store.abort"
      >
        Abort
      </button>
    </div>
  </div>
</template>
