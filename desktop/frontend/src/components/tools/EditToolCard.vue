<!--
  EditToolCard — chat-side card for the `edit` tool.

  Header row: file glyph + filename + +N -M + status pill.
  Body:       diff2html-rendered diff (converted from pi's custom format).
  Click:      opens the post-edit file in the editor pane.

  Streaming: pi runs edit atomically — there's no incremental diff during
  execution. Show a small "applying N edits…" placeholder while
  status==="pending"|"running", flip to the diff view on success.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useFilesStore, normalizeWorkspacePath } from "../../stores/files";
import { useSnapshotsStore } from "../../stores/snapshots";
import { fileGlyph } from "../../lib/file-tree";
import { parseDiff } from "../../lib/diff-parse";
import { piDiffToUnified } from "../../lib/pi-diff-to-unified";
import type { ToolCall } from "../../types/rpc";
import DiffView from "./DiffView.vue";

const props = defineProps<{ call: ToolCall }>();

const files = useFilesStore();
const snapshots = useSnapshotsStore();

const path = computed(() => {
  const args = props.call.args as { path?: unknown } | undefined;
  return typeof args?.path === "string" ? args.path : "";
});

const displayPath = computed(() => (path.value ? normalizeWorkspacePath(path.value) : ""));

const filename = computed(() => {
  const p = displayPath.value;
  if (!p) return "(streaming path…)";
  const idx = p.lastIndexOf("/");
  return idx >= 0 ? p.slice(idx + 1) : p;
});

const dir = computed(() => {
  const p = displayPath.value;
  const idx = p.lastIndexOf("/");
  return idx >= 0 ? p.slice(0, idx) : "";
});

const editsCount = computed(() => {
  const args = props.call.args as { edits?: unknown } | undefined;
  return Array.isArray(args?.edits) ? args.edits.length : 0;
});

const piDiffStr = computed(() => {
  const details = props.call.result?.details as
    | { diff?: unknown }
    | undefined;
  return typeof details?.diff === "string" ? details.diff : "";
});

const stats = computed(() => {
  const parsed = parseDiff(piDiffStr.value);
  return { added: parsed.added, removed: parsed.removed };
});

const unifiedDiff = computed(() => {
  if (!piDiffStr.value || !displayPath.value) return "";
  return piDiffToUnified(piDiffStr.value, displayPath.value);
});

const statusBadge = computed(() => {
  switch (props.call.status) {
    case "pending":
      return { label: "queued", color: "text-muted-foreground bg-muted" };
    case "running":
      return { label: "patching…", color: "text-warning bg-warning/15" };
    case "success":
      return { label: "applied", color: "text-success bg-success/15" };
    case "error":
      return { label: "error", color: "text-destructive bg-destructive/15" };
  }
});

const isStreaming = computed(
  () => props.call.status === "pending" || props.call.status === "running"
);

const isFocused = computed(() => {
  if (!path.value) return false;
  return files.currentFile?.path === normalizeWorkspacePath(path.value);
});

/** True when the editor is currently in review mode pinned to THIS call. */
const isReviewing = computed(
  () => snapshots.editorReview?.toolCallId === props.call.id
);

const glyph = computed(() => (path.value ? fileGlyph(filename.value) : "·"));

function focus(): void {
  if (!path.value) return;
  void files.openFile(path.value);
}

function review(): void {
  void snapshots.enterReviewMode(props.call.id);
}

const restoreBusy = ref(false);
const restoreError = ref<string | null>(null);

async function restore(): Promise<void> {
  if (restoreBusy.value) return;
  const ok = window.confirm(
    `Restore the workspace to BEFORE this edit of "${displayPath.value || filename.value}"?\n\n` +
      `Every change made by this tool call AND every later tool call will be undone. ` +
      `Your manual edits to other files are not affected.`,
  );
  if (!ok) return;
  restoreBusy.value = true;
  restoreError.value = null;
  try {
    const restored = await snapshots.restoreToolCall(props.call.id);
    console.info(`[restore] reverted ${restored.length} file(s)`, restored);
  } catch (exc) {
    restoreError.value = (exc as Error).message;
  } finally {
    restoreBusy.value = false;
  }
}
</script>

<template>
  <!--
    Two click targets, same pattern as WriteToolCard:
      - Header row → open the file in the editor (Mode A — current).
      - "View diff" button → enter review mode (Mode C — full diff in
                              editor). @click.stop keeps it from
                              bubbling to the header.
    "View diff" only appears once the edit has finished (we need pi's
    diff string, which lives in result.details.diff).
  -->
  <div
    :class="[
      'group my-1.5 overflow-hidden rounded-md border border-border bg-card transition-colors hover:border-border/80',
      isReviewing && 'ring-2 ring-primary',
      !isReviewing && isFocused && 'ring-1 ring-primary/60',
    ]"
  >
    <div class="flex items-center gap-2 px-2.5 py-1.5 font-mono text-body">
      <button
        type="button"
        class="flex min-w-0 flex-1 items-center gap-2 text-left"
        :title="`Open ${path} in editor`"
        @click="focus"
      >
        <span
          class="inline-flex h-4 w-4 items-center justify-center rounded-sm bg-muted text-caption text-muted-foreground"
        >{{ glyph }}</span>
        <span class="font-semibold text-foreground/90">edit</span>
        <span class="min-w-0 flex-1 truncate text-foreground" :title="path">
          <span class="text-foreground">{{ filename }}</span>
          <span v-if="dir" class="text-muted-foreground"> · {{ dir }}</span>
        </span>
        <span
          v-if="stats.added > 0"
          class="text-caption tabular-nums text-success"
        >+{{ stats.added }}</span>
        <span
          v-if="stats.removed > 0"
          class="text-caption tabular-nums text-destructive"
        >-{{ stats.removed }}</span>
        <span :class="['rounded-sm px-1.5 py-0.5 text-caption', statusBadge.color]">
          {{ statusBadge.label }}
        </span>
      </button>
      <button
        v-if="call.status === 'success' && unifiedDiff"
        type="button"
        :class="[
          'rounded-sm border px-1.5 py-0.5 text-caption transition-colors',
          isReviewing
            ? 'border-primary bg-primary/15 text-primary'
            : 'border-border bg-background text-muted-foreground hover:border-primary/60 hover:text-foreground',
        ]"
        :title="isReviewing ? 'Review active' : 'Review diff in editor'"
        @click.stop="review"
      >
        {{ isReviewing ? "reviewing ✓" : "view diff" }}
      </button>
      <button
        v-if="call.status === 'success'"
        type="button"
        :disabled="restoreBusy"
        class="rounded-sm border border-border bg-background px-1.5 py-0.5 text-caption text-muted-foreground transition-colors hover:border-destructive/60 hover:text-destructive disabled:cursor-not-allowed disabled:opacity-50"
        title="Rewind workspace to before this tool call"
        @click.stop="restore"
      >
        {{ restoreBusy ? "…" : "↶ restore" }}
      </button>
    </div>
    <div
      v-if="restoreError"
      class="border-t border-destructive/30 bg-destructive/10 px-2.5 py-1 text-caption text-destructive"
    >
      {{ restoreError }}
    </div>

    <div
      v-if="isStreaming"
      class="border-t border-border bg-editor px-3 py-2 font-mono text-caption italic text-muted-foreground"
    >
      <template v-if="editsCount > 0">
        applying {{ editsCount }} edit{{ editsCount === 1 ? "" : "s" }}…
      </template>
      <template v-else>
        collecting edits…
      </template>
    </div>

    <div
      v-else-if="call.status === 'success' && unifiedDiff"
      class="border-t border-border"
    >
      <DiffView :diff="unifiedDiff" :max-rows="10" />
    </div>

    <div
      v-else-if="call.status === 'success'"
      class="border-t border-border bg-editor px-3 py-2 font-mono text-caption italic text-muted-foreground"
    >
      no visible changes
    </div>

    <div
      v-else-if="call.status === 'error'"
      class="border-t border-border bg-destructive/5 px-3 py-2 font-mono text-caption text-destructive"
    >
      {{ call.result?.text || "edit failed" }}
    </div>
  </div>
</template>
