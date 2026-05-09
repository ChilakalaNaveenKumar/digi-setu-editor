<!--
  ToolCallCard — generic chat-side card for any tool call.

  Status is conveyed by an inline coloured badge ("running…", "done",
  "error") next to the tool name; we deliberately removed the chunky
  left rail (`border-l-4 border-l-success/...`) because it dominated
  the chat visually and competed with the agent's actual prose. The
  per-tool cards (BashToolCard, EditToolCard, …) follow the same
  borderless convention.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { ToolCall } from "../types/rpc";

const props = defineProps<{ call: ToolCall }>();

const expanded = ref(false);

const statusBadge = computed(() => {
  switch (props.call.status) {
    case "pending":
      return { label: "queued", color: "text-muted-foreground" };
    case "running":
      return { label: "running…", color: "text-warning" };
    case "success":
      return { label: "done", color: "text-success" };
    case "error":
      return { label: "error", color: "text-destructive" };
  }
});

const argsJson = computed(() => {
  if (props.call.args !== undefined) {
    try {
      return JSON.stringify(props.call.args, null, 2);
    } catch {
      return String(props.call.args);
    }
  }
  return props.call.argsPartial || "";
});

const argsSummary = computed(() => {
  const text = argsJson.value.replace(/\s+/g, " ").trim();
  if (text.length <= 80) return text;
  return text.slice(0, 80) + "…";
});
</script>

<template>
  <div
    class="my-2 rounded-md border border-border bg-card px-3 py-2 font-mono text-body shadow-sm"
  >
    <div class="flex items-baseline gap-2">
      <button
        type="button"
        class="font-semibold text-foreground hover:text-accent-foreground transition-colors"
        @click="expanded = !expanded"
      >
        {{ expanded ? "▾" : "▸" }} {{ call.name }}
      </button>
      <span :class="['text-caption', statusBadge.color]">{{ statusBadge.label }}</span>
      <span class="flex-1 truncate text-muted-foreground">{{ argsSummary }}</span>
    </div>

    <div v-if="expanded" class="mt-2 space-y-2">
      <div v-if="argsJson">
        <div class="mb-1 text-caption uppercase tracking-wide text-muted-foreground">
          args
        </div>
        <pre
          class="whitespace-pre-wrap break-words rounded bg-background px-2 py-1 text-caption leading-snug text-foreground"
        >{{ argsJson }}</pre>
      </div>
      <div v-if="call.result">
        <div class="mb-1 text-caption uppercase tracking-wide text-muted-foreground">
          {{ call.result.isError ? "error output" : "output" }}
        </div>
        <pre
          :class="[
            'whitespace-pre-wrap break-words rounded bg-background px-2 py-1 text-caption leading-snug',
            call.result.isError ? 'text-destructive' : 'text-foreground',
          ]"
        >{{ call.result.text || "(empty)" }}</pre>
      </div>
    </div>
  </div>
</template>
