<!--
  DiffView — thin Vue wrapper around diff2html.
  Single rendering pipeline for ALL chat tool card diffs (write & edit).

  Inputs:
    diff:     unified diff string (pre-converted from pi format via
              piDiffToUnified() / writeContentToUnified())
    maxRows:  cap visible rows; over → fade and "+N more" footer
    streaming: while true, pulse a caret at end of last visible row

  Why diff2html: 397K weekly downloads, mature, GitHub-style visuals,
  handles all the gnarly diff layout (line numbers, column alignment,
  context vs change tinting, multi-hunk separators) that we DON'T want
  to reinvent. Themed via overrides in app.css.
-->
<script setup lang="ts">
import { html as d2hHtml } from "diff2html";
import { computed, onUnmounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    diff: string;
    /** Visible row cap. Lines beyond are hidden + summarized in a footer. */
    maxRows?: number;
    /**
     * Hard cap on the number of UNIFIED-DIFF LINES we hand to diff2html.
     * Beyond this we truncate the diff string itself BEFORE rendering, so
     * we never build a 50k-row table in memory for one tool card.
     * Default of 1500 is generous for normal review use; chat cards
     * effectively cap much lower because they pass `maxRows: 10`.
     */
    maxDiffLines?: number;
    streaming?: boolean;
  }>(),
  { maxRows: 10, maxDiffLines: 1500, streaming: false }
);

// 11.5px font × 1.5 line-height ≈ 17.25px per row. Round up + buffer for
// optional hunk-divider rows (we render those at ~6px each).
const ROW_PX = 18;
const HUNK_BUFFER_PX = 24;

const renderedHtml = ref<string>("");
const expanded = ref(false);
const truncatedFromLines = ref<number | null>(null);
let rafId: number | null = null;
let pending = false;

/**
 * Truncate a unified-diff string to at most `limit` lines, preserving
 * file headers (`---` / `+++`) so diff2html can still parse it. We cut
 * mid-hunk and append a synthetic info line so the user sees we trimmed.
 * Pre-truncation keeps diff2html fast — a 1500-line cap is ~50× cheaper
 * than letting it tokenise a 50k-line diff and then clipping with CSS.
 */
function truncateUnifiedDiff(diff: string, limit: number): { diff: string; total: number } {
  const lines = diff.split("\n");
  if (lines.length <= limit) return { diff, total: lines.length };
  const head = lines.slice(0, limit);
  const remaining = lines.length - limit;
  head.push(`@@ ... ${remaining} more diff lines truncated for performance ... @@`);
  return { diff: head.join("\n"), total: lines.length };
}

function renderNow(): void {
  const rawDiff = props.diff;
  if (!rawDiff) {
    renderedHtml.value = "";
    truncatedFromLines.value = null;
    return;
  }
  // Apply diff-line cap unless the user explicitly expanded.
  const effectiveLimit = expanded.value
    ? Number.POSITIVE_INFINITY
    : props.maxDiffLines;
  const { diff: workingDiff, total } = truncateUnifiedDiff(rawDiff, effectiveLimit);
  truncatedFromLines.value = total > effectiveLimit ? total : null;

  try {
    renderedHtml.value = d2hHtml(workingDiff, {
      drawFileList: false,
      matching: "lines",
      outputFormat: "line-by-line",
      colorScheme: "dark",
    });
  } catch (exc) {
    console.warn("[DiffView] diff2html failed", exc);
    renderedHtml.value = "";
  }
}

/** Schedule re-render coalesced via rAF to keep streaming smooth. */
function schedule(): void {
  if (rafId !== null) {
    pending = true;
    return;
  }
  rafId = requestAnimationFrame(() => {
    rafId = null;
    pending = false;
    renderNow();
    if (pending) schedule();
  });
}

watch(
  () => [props.diff, props.maxDiffLines, expanded.value] as const,
  () => schedule(),
  { immediate: true },
);

onUnmounted(() => {
  if (rafId !== null) cancelAnimationFrame(rafId);
});

/**
 * Count CONTENT rows only (skip hunk-header <tr>s tagged d2h-info).
 * Used for the "+N more lines" footer copy and truncation gating.
 */
const totalRows = computed(() => {
  const all = renderedHtml.value.match(/<tr[^>]*>/g) ?? [];
  return all.filter((tag) => !tag.includes("d2h-info")).length;
});

const isOver = computed(() => totalRows.value > props.maxRows);
const hiddenRows = computed(() =>
  Math.max(0, totalRows.value - props.maxRows)
);
</script>

<template>
  <div class="d2h-mount relative">
    <!-- diff2html injects its own <table> structure here. We host it then
         apply CSS overrides in app.css to match the Notion teal palette. -->
    <div
      v-if="renderedHtml"
      :class="[
        'd2h-host',
        isOver && !streaming ? 'd2h-host-truncated' : '',
        streaming ? 'd2h-host-streaming' : '',
      ]"
      :style="{
        maxHeight:
          streaming
            ? 'unset'
            : isOver
              ? `${maxRows * ROW_PX + HUNK_BUFFER_PX}px`
              : 'unset',
        overflow: isOver && !streaming ? 'hidden' : undefined,
      }"
      v-html="renderedHtml"
    />
    <div
      v-else
      class="px-3 py-2 font-mono text-[11px] italic text-muted-foreground"
    >
      no changes
    </div>

    <div
      v-if="isOver && !streaming"
      class="pointer-events-none flex items-center justify-end border-t border-border bg-card px-2 py-1 font-mono text-[10px] text-muted-foreground"
    >
      <span>+{{ hiddenRows }} more line{{ hiddenRows === 1 ? "" : "s" }} · click to open</span>
    </div>

    <!-- Hard-cap notice when we pre-truncated the diff string itself.
         User can opt in to render the full diff (warning: slow on huge diffs). -->
    <div
      v-if="truncatedFromLines !== null"
      class="flex items-center gap-2 border-t border-amber-700/30 bg-amber-950/20 px-2 py-1 font-mono text-[10px] text-amber-200/80"
    >
      <span class="leading-none">⚠</span>
      <span>
        Large diff: showing first
        <strong>{{ maxDiffLines.toLocaleString() }}</strong>
        of <strong>{{ truncatedFromLines.toLocaleString() }}</strong> lines.
      </span>
      <button
        v-if="!expanded"
        type="button"
        class="ml-auto rounded-sm border border-amber-700/40 bg-amber-950/40 px-1.5 py-0.5 text-amber-200 hover:bg-amber-900/60"
        @click="expanded = true"
      >render full</button>
    </div>
  </div>
</template>
