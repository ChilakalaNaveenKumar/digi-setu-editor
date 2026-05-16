<!--
  UserMessage — chat bubble for the user.

  Visual: ChatGPT/Claude-style card on a slightly tinted background
  surface. Rounded card + soft `bg-muted/40` fill + 1 px border, with
  a small "YOU" eyebrow label and a hover-revealed "↶ revert turn"
  button on the right edge of the eyebrow row.

  Earlier passes oscillated between two extremes:
   1. Heavy filled card with strong border — every "Hi" looked like a
      banner announcement next to a plain-text assistant reply.
   2. Bare 2 px left rail with no fill — too minimal, the "user said
      what?" affordance got lost in long threads with lots of tool
      cards in between.
  The current design splits the difference: enough fill that the
  user's prompt is visually anchored as a discrete unit, but soft
  enough (muted, not primary) that the assistant reply still reads
  as the main content of the turn.

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
  <!--
    `group` enables the hover-revealed revert button. The outer wrap
    handles vertical rhythm; the inner card owns the visual weight.
  -->
  <div ref="root" class="user-bubble group my-5">
    <!-- Eyebrow row — speaker label on the left, revert affordance
         (only on hover) on the right. Sitting OUTSIDE the bubble so
         the bubble surface stays a clean rectangle of message text. -->
    <div class="mb-1.5 flex items-center justify-between gap-3 px-1">
      <span class="text-caption font-semibold uppercase tracking-wider text-foreground/70">
        You<span v-if="isLong" class="ml-1.5 font-normal normal-case tracking-normal text-muted-foreground/70">·
          {{ lineCount }} lines, {{ text.length.toLocaleString() }} chars</span>
      </span>
      <button
        type="button"
        :disabled="revertBusy"
        class="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-0.5 text-caption text-muted-foreground opacity-0 transition-all hover:border-destructive/60 hover:text-destructive group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-50"
        title="Revert every file change made in response to this prompt"
        @click="revertTurn"
      >
        <Icon
          :icon="revertBusy ? 'codicon:loading' : 'codicon:discard'"
          :class="revertBusy && 'animate-spin'"
          class="h-3 w-3"
        />
        {{ revertBusy ? "reverting…" : "revert turn" }}
      </button>
    </div>

    <!-- Bubble surface. Solid `bg-muted` fill, NO border. Earlier
         pass used `border-border/70 bg-muted/40` which on a dark
         theme rendered as a thin near-white outline over a barely-
         tinted fill — the user's prompt looked like an empty contour
         box. The tinted fill alone anchors "this is the user's turn"
         and matches the visual style of system / summary bubbles
         elsewhere in the chat. -->
    <div
      class="relative rounded-xl bg-muted px-4 py-3 transition-colors"
    >
      <div class="pi-markdown leading-relaxed text-foreground" v-html="html" />
      <!-- Soft fade at the bottom of the preview gives a visual cue
           that the message is truncated. We fade INTO the bubble's
           own bg colour (muted) so it doesn't look like a stripe. -->
      <div
        v-if="isLong && !expanded"
        class="pointer-events-none absolute inset-x-0 bottom-0 h-10 rounded-b-xl bg-gradient-to-t from-muted to-transparent"
        aria-hidden="true"
      />
    </div>

    <!-- Show-more toggle sits below the bubble in the same gutter as
         the eyebrow. Keeps the bubble surface uncluttered. -->
    <button
      v-if="isLong"
      type="button"
      class="mt-1 inline-flex items-center gap-1 rounded px-1 text-caption font-mono text-muted-foreground hover:text-foreground"
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
      class="mt-1 px-1 text-caption text-success"
    >
      reverted {{ revertedFiles.length }} file{{ revertedFiles.length === 1 ? "" : "s" }}
    </div>
    <div
      v-if="revertError"
      class="mt-1 px-1 text-caption text-destructive"
    >
      {{ revertError }}
    </div>
  </div>
</template>
