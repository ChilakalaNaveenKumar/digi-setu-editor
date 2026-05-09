<!--
  CompactToolChip — one-line, low-key chip used for tools whose value is
  the *fact* the agent ran them (read / grep / ls / find / web_search /
  list_fonts / search_docs …) rather than any rich result preview.

  Visual layout:
        ▸ <verb> <main>            <status dot>  [↗] [⧉]
                                    pid 234   etc.

  Behaviour:
    • Hover the verb/main span → tooltip = `tooltip` prop (e.g. full path).
    • Click the verb/main span → `select` event (callers wire to "open in
      editor pane" when applicable).
    • Click the [⧉] copy button → writes `copyValue` to clipboard, briefly
      flashes "✓".
    • Click the chevron → toggles inline expansion of result text.

  Status colors mirror the rail colors used elsewhere (rail-running etc.)
  so the whole chat keeps a single visual language.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { ToolCall } from "../../types/rpc";

const props = defineProps<{
  call: ToolCall;
  /** Verb shown bold. e.g. "Read", "Grepped", "Listed", "Found". */
  verb: string;
  /** Main argument shown next to verb. e.g. "src/foo.ts:1-200". */
  main: string;
  /** Optional tooltip on hover (typically the full path / pattern). */
  tooltip?: string;
  /** Optional value to copy when the user clicks the copy icon. */
  copyValue?: string;
  /** Optional: if true, clicking the verb fires `select`. */
  selectable?: boolean;
}>();

const emit = defineEmits<{
  select: [];
}>();

const expanded = ref(false);
const copyFlash = ref(false);

const statusDot = computed(() => {
  switch (props.call.status) {
    case "running":
      return "bg-warning animate-pulse";
    case "success":
      return "bg-success";
    case "error":
      return "bg-destructive";
    default:
      return "bg-muted-foreground/40";
  }
});

const statusLabel = computed(() => {
  switch (props.call.status) {
    case "pending":
      return "queued";
    case "running":
      return "…";
    case "success":
      return "";
    case "error":
      return "error";
  }
});

const resultText = computed(() => props.call.result?.text ?? "");

async function copy(): Promise<void> {
  const value = props.copyValue ?? props.main;
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    copyFlash.value = true;
    setTimeout(() => (copyFlash.value = false), 900);
  } catch {
    // Clipboard API blocked — silently noop. (Could add a fallback prompt.)
  }
}
</script>

<template>
  <div class="my-0.5 px-1 font-mono text-body text-foreground/85">
    <div class="flex items-center gap-1.5">
      <button
        type="button"
        class="text-muted-foreground hover:text-foreground"
        :title="expanded ? 'Hide output' : 'Show output'"
        @click="expanded = !expanded"
      >{{ expanded ? "▾" : "▸" }}</button>

      <button
        type="button"
        :class="[
          'inline-flex min-w-0 flex-1 items-baseline gap-1.5 truncate text-left',
          selectable ? 'hover:text-primary cursor-pointer' : 'cursor-default',
        ]"
        :title="tooltip || main"
        @click="selectable && emit('select')"
      >
        <span class="font-semibold text-foreground">{{ verb }}</span>
        <span class="truncate text-foreground/85">{{ main }}</span>
      </button>

      <span :class="['inline-block h-1.5 w-1.5 shrink-0 rounded-full', statusDot]" :title="call.status"></span>
      <span
        v-if="statusLabel"
        class="text-caption text-muted-foreground"
      >{{ statusLabel }}</span>

      <button
        v-if="copyValue || main"
        type="button"
        class="rounded-sm px-1 text-caption text-muted-foreground hover:bg-accent hover:text-foreground"
        :title="copyFlash ? 'Copied!' : `Copy: ${copyValue ?? main}`"
        @click.stop="copy"
      >{{ copyFlash ? "✓" : "⧉" }}</button>
    </div>

    <pre
      v-if="expanded && resultText"
      :class="[
        'mt-1 ml-5 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded border border-border/50 bg-background px-2 py-1.5 text-caption leading-snug',
        call.result?.isError ? 'text-destructive' : 'text-foreground/90',
      ]"
    >{{ resultText }}</pre>
    <div
      v-else-if="expanded"
      class="mt-1 ml-5 text-caption italic text-muted-foreground"
    >no output</div>
  </div>
</template>
