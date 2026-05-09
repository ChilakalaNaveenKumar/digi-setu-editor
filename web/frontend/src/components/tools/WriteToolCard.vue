<!--
  WriteToolCard — chat-side card for the `write` tool.

  Header row: file glyph + filename + +<lines> + size + status pill.
  Body:       diff2html-rendered "all-lines-added" view of the file content
              (so a brand-new file looks visually identical to an edit, just
              with everything green). Streams during toolcall_delta.
  Click:      focuses the file in the EditorPane (full view).
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useChatStore } from "../../stores/chat";
import { useFilesStore, normalizeWorkspacePath } from "../../stores/files";
import { useSnapshotsStore } from "../../stores/snapshots";
import { fileGlyph } from "../../lib/file-tree";
import { writeContentToUnified } from "../../lib/pi-diff-to-unified";
import type { ToolCall } from "../../types/rpc";
import DiffView from "./DiffView.vue";

const props = defineProps<{ call: ToolCall }>();

const chat = useChatStore();
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

const content = computed(() => {
  const args = props.call.args as { content?: unknown } | undefined;
  return typeof args?.content === "string" ? args.content : "";
});

const lineCount = computed(() => {
  if (!content.value) return 0;
  const lines = content.value.split("\n");
  // Trailing empty from final "\n" doesn't count.
  return lines.length > 1 && lines[lines.length - 1] === ""
    ? lines.length - 1
    : lines.length;
});

const sizeLabel = computed(() => {
  const len = content.value.length;
  if (!len) return "";
  if (len < 1024) return `${len} B`;
  if (len < 1024 * 1024) return `${(len / 1024).toFixed(1)} KB`;
  return `${(len / 1024 / 1024).toFixed(2)} MB`;
});

const statusBadge = computed(() => {
  switch (props.call.status) {
    case "pending":
      return { label: "queued", color: "text-muted-foreground bg-muted" };
    case "running":
      return { label: "saving…", color: "text-warning bg-warning/15" };
    case "success":
      return { label: "done", color: "text-success bg-success/15" };
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

/** Synthetic unified diff: every line as an addition vs /dev/null. */
const unifiedDiff = computed(() =>
  displayPath.value && content.value
    ? writeContentToUnified(content.value, displayPath.value)
    : ""
);

function focus(): void {
  if (!path.value) return;
  chat.focusToolCall(props.call.id);
  if (props.call.status === "success") {
    void files.openFile(path.value);
  }
}

function review(): void {
  void snapshots.enterReviewMode(props.call.id);
}

const restoreBusy = ref(false);
const restoreError = ref<string | null>(null);

async function restore(): Promise<void> {
  if (restoreBusy.value) return;
  const ok = window.confirm(
    `Restore the workspace to BEFORE this write of "${displayPath.value || filename.value}"?\n\n` +
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
    The card is a <div> (not a <button>) so we can host two independent
    click targets without nesting buttons:
      - Header row → focus the file in the editor (Mode A — current).
      - "View diff" button → enter review mode (Mode C — full diff in
                              editor). @click.stop to keep it from
                              bubbling to the header.
    Ring color tells you what the editor is showing right now: primary
    ring = file is open; accent ring = THIS card's diff is in review.
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
        <span class="font-semibold text-foreground/90">write</span>
        <span class="min-w-0 flex-1 truncate text-foreground" :title="path">
          <span class="text-foreground">{{ filename }}</span>
          <span v-if="dir" class="text-muted-foreground"> · {{ dir }}</span>
        </span>
        <span
          v-if="lineCount > 0"
          class="text-caption tabular-nums text-success"
        >+{{ lineCount }}</span>
        <span v-if="sizeLabel" class="text-caption text-muted-foreground">{{ sizeLabel }}</span>
        <span :class="['rounded-sm px-1.5 py-0.5 text-caption', statusBadge.color]">
          {{ statusBadge.label }}
        </span>
      </button>
      <button
        v-if="!isStreaming && unifiedDiff"
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
        v-if="!isStreaming"
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

    <div class="border-t border-border">
      <DiffView
        :diff="unifiedDiff"
        :streaming="isStreaming"
        :max-rows="10"
      />
    </div>
  </div>
</template>
