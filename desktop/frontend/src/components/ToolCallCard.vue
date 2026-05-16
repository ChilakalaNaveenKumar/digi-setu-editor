<!--
  ToolCallCard — generic chat-side card for any tool call we don't ship a
  dedicated card for.

  Visual model mirrors pi-mono-main/packages/web-ui's renderer-registry.ts
  `renderHeader` helper:

      ┌──────────────────────────────────────────────────────────────┐
      │ <icon>  tool_name   running…                       ⟳ / ⌃    │   ← header
      ├──────────────────────────────────────────────────────────────┤
      │   args (json)                                                │
      │   output                                                     │
      └──────────────────────────────────────────────────────────────┘

  - Tool icon (codicon) is coloured by state:
      pending  → muted-foreground
      running  → primary, no spin (the spinner lives on the right)
      success  → green (var(--success))
      error    → destructive
  - Right gutter shows a spinning loader while running, otherwise a
    chevron that flips on expand. NO ASCII `▾`/`▸` here — those competed
    with the actual prose visually.
  - Header is the click target for collapse.
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, ref } from "vue";
import type { ToolCall } from "../types/rpc";

const props = defineProps<{ call: ToolCall }>();

const expanded = ref(false);

/**
 * codicon icon for every tool name we know about. Anything else falls
 * through to the `tools` icon. The mapping is intentionally explicit
 * (no string-template guessing) so renaming a tool on the pi side
 * doesn't silently lose its icon.
 */
const ICON_BY_TOOL: Record<string, string> = {
  bash: "codicon:terminal-bash",
  process: "codicon:pulse",
  edit: "codicon:edit",
  write: "codicon:new-file",
  read: "codicon:file",
  grep: "codicon:search",
  find: "codicon:search-fuzzy",
  ls: "codicon:list-flat",
  todo: "codicon:checklist",
  subagent: "codicon:organization",
  search_docs: "codicon:book",
  read_doc: "codicon:file-pdf",
  structured_output: "codicon:json",
  fetch: "codicon:cloud-download",
};

const toolIcon = computed(() => ICON_BY_TOOL[props.call.name] ?? "codicon:tools");

const state = computed<"pending" | "running" | "success" | "error">(() => props.call.status);

/**
 * Header-status tuple in the same shape pi-mono's `renderHeader` returns:
 * { label, colorClass for the icon }. Keeping it as a single computed
 * object means the template stays tidy and we can flip both pieces in
 * lock-step.
 */
const statusMeta = computed(() => {
  switch (state.value) {
    case "pending":
      return { label: "queued", iconClass: "text-muted-foreground" };
    case "running":
      return { label: "running…", iconClass: "text-primary" };
    case "success":
      return { label: "done", iconClass: "text-success" };
    case "error":
      return { label: "error", iconClass: "text-destructive" };
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
    class="group my-2 rounded-md border border-border bg-card px-3 py-2 text-body shadow-sm transition-colors hover:border-border/80"
  >
    <button
      type="button"
      class="flex w-full items-center gap-2 text-left"
      @click="expanded = !expanded"
    >
      <Icon :icon="toolIcon" :class="['h-4 w-4 shrink-0', statusMeta.iconClass]" />
      <span class="font-mono font-semibold text-foreground">{{ call.name }}</span>
      <span class="text-caption text-muted-foreground">{{ statusMeta.label }}</span>
      <span class="flex-1 truncate font-mono text-caption text-muted-foreground">{{ argsSummary }}</span>
      <Icon
        v-if="state === 'running' || state === 'pending'"
        icon="codicon:loading"
        class="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground"
      />
      <Icon
        v-else
        :icon="expanded ? 'codicon:chevron-up' : 'codicon:chevron-down'"
        class="h-3.5 w-3.5 shrink-0 text-muted-foreground"
      />
    </button>

    <div v-if="expanded" class="mt-2 space-y-2">
      <div v-if="argsJson">
        <div class="mb-1 text-caption uppercase tracking-wide text-muted-foreground">
          args
        </div>
        <pre
          class="whitespace-pre-wrap break-words rounded bg-background px-2 py-1 font-mono text-caption leading-snug text-foreground"
        >{{ argsJson }}</pre>
      </div>
      <div v-if="call.result">
        <div class="mb-1 text-caption uppercase tracking-wide text-muted-foreground">
          {{ call.result.isError ? "error output" : "output" }}
        </div>
        <pre
          :class="[
            'whitespace-pre-wrap break-words rounded bg-background px-2 py-1 font-mono text-caption leading-snug',
            call.result.isError ? 'text-destructive' : 'text-foreground',
          ]"
        >{{ call.result.text || "(empty)" }}</pre>
      </div>
    </div>
  </div>
</template>
