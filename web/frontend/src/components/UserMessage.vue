<!--
  UserMessage — chat bubble for the user. Compact card with subtle accent
  rail on the left.

  Long messages (>~12 lines or 1500 chars of source) auto-collapse to a
  preview with a "Show more / less" toggle, so a single 100k-char paste
  doesn't drown the chat thread. Threshold is intentionally on the
  source text, not the rendered HTML, so a giant code-block paste also
  collapses cleanly.

  "↶ revert turn" button (visible on hover) wipes every file change made by
  the agent in response to this prompt. Useful when a turn went off the
  rails: undo the whole reply in one click instead of scrubbing through
  every individual tool card. Backed by /api/turns/{id}/revert (opencode
  pattern).
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUpdated, ref } from "vue";
import { Icon } from "@iconify/vue";
import { renderMarkdown } from "../lib/markdown";
import { enhanceCodeBlocks } from "../lib/code-block-enhance";
import { useSnapshotsStore } from "../stores/snapshots";

const props = defineProps<{ id: string; text: string }>();

// Collapse heuristics: a message is "long" if it spans many lines OR has
// a lot of total characters. Both bound, otherwise a single 100k-char
// blob (one line, no \n) would slip through the line-count check.
const COLLAPSE_LINES = 12;
const COLLAPSE_CHARS = 1500;
const PREVIEW_LINES = 8;

const lineCount = computed(() => (props.text.match(/\n/g)?.length ?? 0) + 1);
const isLong = computed(
  () => lineCount.value > COLLAPSE_LINES || props.text.length > COLLAPSE_CHARS,
);

// User messages start collapsed when long. The user typed it themselves
// — they don't usually need to re-read the entire prompt, but they
// often do want to glance at the head of it as context.
const expanded = ref(false);

const previewText = computed(() => {
  if (!isLong.value) return props.text;
  const lines = props.text.split("\n").slice(0, PREVIEW_LINES).join("\n");
  if (lines.length > COLLAPSE_CHARS) return lines.slice(0, COLLAPSE_CHARS);
  return lines;
});

const html = computed(() =>
  renderMarkdown(expanded.value || !isLong.value ? props.text : previewText.value),
);

const snapshots = useSnapshotsStore();
const revertBusy = ref(false);
const revertError = ref<string | null>(null);
const revertedFiles = ref<string[] | null>(null);

const root = ref<HTMLElement | null>(null);
onMounted(() => {
  void nextTick(() => enhanceCodeBlocks(root.value));
});
onUpdated(() => {
  void nextTick(() => enhanceCodeBlocks(root.value));
});

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
    const files = await snapshots.revertTurn(props.id);
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
  <div ref="root" class="user-bubble group my-5 rounded-md px-4 py-3">
    <div class="mb-1 flex items-center justify-between">
      <span class="text-caption uppercase tracking-wide text-muted-foreground">
        you<span v-if="isLong" class="ml-1.5 normal-case opacity-60">·
          {{ lineCount }} lines, {{ text.length.toLocaleString() }} chars</span>
      </span>
      <button
        type="button"
        :disabled="revertBusy"
        class="rounded-sm border border-border bg-background px-1.5 py-0.5 text-caption text-muted-foreground opacity-0 transition-opacity hover:border-destructive/60 hover:text-destructive group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-50"
        title="Revert every file change made in response to this prompt"
        @click="revertTurn"
      >
        {{ revertBusy ? "reverting…" : "↶ revert turn" }}
      </button>
    </div>
    <!--
      Soft fade at the bottom of the preview gives a clear visual cue
      that the message is truncated, without needing scroll bars or a
      hard cut-off line. Disabled when expanded so the full text reads
      cleanly.
    -->
    <div class="relative">
      <div class="pi-markdown text-foreground" v-html="html" />
      <div
        v-if="isLong && !expanded"
        class="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-[var(--user-bubble-bg,theme(colors.muted.DEFAULT))] to-transparent"
        aria-hidden="true"
      />
    </div>
    <button
      v-if="isLong"
      type="button"
      class="mt-1 inline-flex items-center gap-1 rounded text-caption font-mono text-muted-foreground hover:text-foreground"
      @click="expanded = !expanded"
    >
      <Icon
        :icon="expanded ? 'codicon:chevron-up' : 'codicon:chevron-down'"
        class="h-3 w-3"
      />
      {{ expanded ? "Show less" : "Show full message" }}
    </button>
    <div
      v-if="revertedFiles"
      class="mt-1 text-caption text-success"
    >
      reverted {{ revertedFiles.length }} file{{ revertedFiles.length === 1 ? "" : "s" }}
    </div>
    <div
      v-if="revertError"
      class="mt-1 text-caption text-destructive"
    >
      {{ revertError }}
    </div>
  </div>
</template>

<style scoped>
/* Pull the bubble's exact background colour into the fade gradient via
   a CSS variable, so the fade reads as "fading into the bubble" rather
   than fading into a generic surface. Falls back to muted when the
   bubble doesn't expose its own bg variable. */
.user-bubble {
  --user-bubble-bg: hsl(var(--card));
}
</style>
