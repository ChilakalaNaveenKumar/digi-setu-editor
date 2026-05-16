<!--
  TodoToolCard — dedicated card for pi's bundled `todo` extension.

  Source: pi-mono-main/packages/coding-agent/examples/extensions/todo.ts.
  The extension stores the entire list in `tool_result.details`:

      {
        action:  "list" | "add" | "toggle" | "clear",
        todos:   [{ id, text, done }, …],   // FULL list, always
        nextId:  number,
        error?:  string,
      }

  Each call REPLACES the previous list (pi reconstructs state by replaying
  results in order). So this card just shows the result.details.todos as
  a checklist plus a one-line summary of what changed this turn.
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, ref } from "vue";
import type { ToolCall } from "../../types/rpc";

const props = defineProps<{ call: ToolCall }>();

interface TodoItem {
  id: number;
  text: string;
  done: boolean;
}

interface TodoDetails {
  action: "list" | "add" | "toggle" | "clear";
  todos: TodoItem[];
  nextId?: number;
  error?: string;
}

const details = computed<TodoDetails | null>(() => {
  const d = props.call.result?.details as TodoDetails | undefined;
  if (!d || !Array.isArray(d.todos)) return null;
  return d;
});

const args = computed(() => props.call.args as { action?: string; text?: string; id?: number } | undefined);

/**
 * "Added 'fix billing bug'", "Marked done: 'fix billing bug'", …
 * One line, past-tense, what the AI did this turn.
 */
const actionLabel = computed(() => {
  const d = details.value;
  if (!d) {
    const a = args.value?.action ?? "list";
    return `todo · ${a}`;
  }
  if (d.error) return `error: ${d.error}`;
  switch (d.action) {
    case "list":
      return d.todos.length === 0
        ? "no todos"
        : `${d.todos.length} todo${d.todos.length === 1 ? "" : "s"}`;
    case "add": {
      const last = d.todos[d.todos.length - 1];
      return last ? `added "${last.text}"` : "added";
    }
    case "toggle": {
      const id = args.value?.id;
      const item = typeof id === "number" ? d.todos.find((t) => t.id === id) : undefined;
      return item ? `${item.done ? "✓ done" : "↺ reopened"} "${item.text}"` : "toggled";
    }
    case "clear":
      return "cleared all todos";
  }
  return "todo";
});

const headerState = computed<"pending" | "running" | "success" | "error">(() => {
  if (props.call.status === "pending" || props.call.status === "running") return props.call.status;
  if (details.value?.error || props.call.status === "error") return "error";
  return "success";
});

const headerIconClass = computed(() => {
  switch (headerState.value) {
    case "pending":
      return "text-muted-foreground";
    case "running":
      return "text-primary";
    case "success":
      return "text-success";
    case "error":
      return "text-destructive";
  }
});

// Collapsed by default — todo runs as a stream of single-action calls
// (add → toggle → done), each rendering its own card with the FULL
// list inside. Leaving them all expanded floods the chat. The header
// already shows the action label ("added X" / "✓ done Y") so users
// can scan progress without expanding; click to drill in.
const expanded = ref(false);
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
      <Icon icon="codicon:checklist" :class="['h-4 w-4 shrink-0', headerIconClass]" />
      <span class="font-mono font-semibold text-foreground">todo</span>
      <span class="text-caption text-muted-foreground">·</span>
      <span class="flex-1 truncate text-caption text-muted-foreground">{{ actionLabel }}</span>
      <Icon
        v-if="headerState === 'running' || headerState === 'pending'"
        icon="codicon:loading"
        class="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground"
      />
      <Icon
        v-else
        :icon="expanded ? 'codicon:chevron-up' : 'codicon:chevron-down'"
        class="h-3.5 w-3.5 shrink-0 text-muted-foreground"
      />
    </button>

    <ul v-if="expanded && details && details.todos.length > 0" class="mt-2 space-y-1">
      <li
        v-for="t in details.todos"
        :key="t.id"
        class="flex items-start gap-2 rounded px-1.5 py-0.5 text-body leading-snug"
      >
        <Icon
          :icon="t.done ? 'codicon:check' : 'codicon:circle-large-outline'"
          :class="[
            'mt-[2px] h-3.5 w-3.5 shrink-0',
            t.done ? 'text-success' : 'text-muted-foreground',
          ]"
        />
        <span :class="t.done ? 'text-muted-foreground line-through' : 'text-foreground'">{{ t.text }}</span>
      </li>
    </ul>

    <div
      v-else-if="expanded && details && details.todos.length === 0"
      class="mt-2 px-1.5 py-1 text-caption italic text-muted-foreground"
    >
      list is empty
    </div>

    <div
      v-if="expanded && details?.error"
      class="mt-2 rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-caption text-destructive"
    >
      {{ details.error }}
    </div>
  </div>
</template>
