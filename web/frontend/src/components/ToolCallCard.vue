<!--
  ToolCallCard — generic chat-side card for any tool call.
    pending  → muted left rail
    running  → warning (amber) left rail + pulsing dot
    success  → success (green) left rail
    error    → destructive (red) left rail
  Per-tool renderers (BashCard, EditCard, etc.) come in the next slice and
  will replace this generic card by tool name. For now everything routes
  through here so we have a stable visual baseline.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { ToolCall } from "../types/rpc";

const props = defineProps<{ call: ToolCall }>();

const expanded = ref(false);

const railClass = computed(() => {
  switch (props.call.status) {
    case "running":
      return "border-l-warning";
    case "success":
      return "border-l-success";
    case "error":
      return "border-l-destructive";
    default:
      return "border-l-border";
  }
});

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
    :class="[
      'my-2 rounded-md border border-border border-l-4 bg-card px-3 py-2 font-mono text-xs shadow-sm',
      railClass,
    ]"
  >
    <div class="flex items-baseline gap-2">
      <button
        type="button"
        class="font-semibold text-foreground hover:text-accent-foreground transition-colors"
        @click="expanded = !expanded"
      >
        {{ expanded ? "▾" : "▸" }} {{ call.name }}
      </button>
      <span :class="['text-[10px]', statusBadge.color]">{{ statusBadge.label }}</span>
      <span class="flex-1 truncate text-muted-foreground">{{ argsSummary }}</span>
    </div>

    <div v-if="expanded" class="mt-2 space-y-2">
      <div v-if="argsJson">
        <div class="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
          args
        </div>
        <pre
          class="whitespace-pre-wrap break-words rounded bg-background px-2 py-1 text-[11px] leading-snug text-foreground"
        >{{ argsJson }}</pre>
      </div>
      <div v-if="call.result">
        <div class="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
          {{ call.result.isError ? "error output" : "output" }}
        </div>
        <pre
          :class="[
            'whitespace-pre-wrap break-words rounded bg-background px-2 py-1 text-[11px] leading-snug',
            call.result.isError ? 'text-destructive' : 'text-foreground',
          ]"
        >{{ call.result.text || "(empty)" }}</pre>
      </div>
    </div>
  </div>
</template>
