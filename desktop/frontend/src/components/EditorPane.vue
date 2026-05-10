<!--
  EditorPane — center column. Cursor-style three-mode editor:

    Mode A (current file)  — source="static". User clicked a file in the
                              tree (or AI just finished writing/editing
                              and we re-fetched). Plain syntax-highlighted
                              source.
    Mode B (live streaming) — source="live". An active write tool is
                              filling this file char-by-char. Pulsing
                              caret, status pill streaming → writing →
                              done | error.
    Mode C (diff review)   — store.editorReview is non-null. Pinned by
                              clicking "View diff" on a tool card. Shows
                              the FULL unified diff for that one
                              operation. "← Back to file" header button
                              (or any other file click) returns to A.

  Mode C ALWAYS wins when active — it's an explicit user intent. Streaming
  writes still update store.currentFile in the background; the moment the
  user exits review mode they're back on the latest file state.

  Syntax highlighting (Modes A & B):
    Powered by Shiki (singleton, lazy-loaded). Re-tokenization is throttled
    via requestAnimationFrame so a stream of toolcall_delta events doesn't
    re-highlight per byte. If language isn't recognized (unknown extension)
    we show plain HTML-escaped lines — never crash.
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";
import { useFilesStore } from "../stores/files";
import { useSnapshotsStore } from "../stores/snapshots";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import { downloadFile as apiDownloadFile } from "../api/files";
import { highlightLines, langForPath } from "../lib/highlighter";
import DiffView from "./tools/DiffView.vue";
import CodeEditor from "./CodeEditor.vue";
import EditorTabs from "./EditorTabs.vue";
import FilePreview from "./FilePreview.vue";

const files = useFilesStore();
const snapshots = useSnapshotsStore();
const ui = useUiStore();
const workspace = useWorkspaceStore();
const { currentFile } = storeToRefs(files);
const { editorReview } = storeToRefs(snapshots);

const inReview = computed(() => editorReview.value !== null);
/**
 * Mode A → editable. Mode B (agent is actively writing) and Mode C (diff
 * review) stay read-only. Non-text files (images, PDFs, audio, video)
 * always preview — never editable here. SVG opens in preview mode and
 * the user can flip to "view as code" via the FilePreview toolbar.
 */
const isEditableMode = computed(() => {
  const f = currentFile.value;
  if (!f || inReview.value) return false;
  if (f.binary || f.reason) return false;
  if (previewKind.value !== null) return false;
  return f.source === "static" && (f.status === "loaded" || f.status === "done");
});

/** SVG users can toggle between preview and source. Tracked here so we
 *  remember the choice while they're on this file. */
const svgShowAsCode = ref(false);

/** Which preview component (if any) should render this file. */
const previewKind = computed<"image" | "pdf" | "svg" | "audio" | "video" | "office" | null>(() => {
  const f = currentFile.value;
  if (!f) return null;
  if (inReview.value) return null;
  const k = f.kind;
  if (k === "image" || k === "pdf" || k === "audio" || k === "video" || k === "office") return k;
  if (k === "svg" && !svgShowAsCode.value) return "svg";
  return null;
});

// Reset svg-as-code mode when switching files.
watch(
  () => currentFile.value?.path,
  () => (svgShowAsCode.value = false),
);

// ── Editable-pane: dirty + save wiring ────────────────────────────────
const dirty = ref(false);
const saving = ref(false);
const saveError = ref<string | null>(null);
const codeEditorRef = ref<InstanceType<typeof CodeEditor> | null>(null);

function onDirty(next: boolean): void {
  dirty.value = next;
  saveError.value = null;
  // Mirror the dirty flag onto the corresponding tab so the strip can
  // show a ● indicator and prompt before close.
  const p = currentFile.value?.path;
  if (p) files.setTabDirty(p, next);
}

async function onSave(content: string): Promise<void> {
  const path = currentFile.value?.path;
  if (!path) return;
  saving.value = true;
  saveError.value = null;
  try {
    await files.saveFile(path, content);
  } catch (exc) {
    saveError.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}

function manualSave(): void {
  codeEditorRef.value?.save();
}

// Reset dirty state when switching files.
watch(
  () => currentFile.value?.path,
  () => {
    dirty.value = false;
    saveError.value = null;
  },
);

// ── Header actions: close, copy content, copy path, delete ────────────
function closeFile(): void {
  // closeCurrentFile() routes through closeTab() which already runs the
  // dirty-state confirm; nothing more to do here.
  files.closeCurrentFile();
}

const copyFlash = ref<"content" | "path" | null>(null);
async function copyContent(): Promise<void> {
  const c = currentFile.value?.content ?? "";
  if (!c) return;
  try {
    await navigator.clipboard.writeText(c);
    copyFlash.value = "content";
    setTimeout(() => (copyFlash.value = null), 1200);
  } catch {
    /* ignore */
  }
}
async function copyPath(): Promise<void> {
  const p = currentFile.value?.path ?? "";
  if (!p) return;
  try {
    await navigator.clipboard.writeText(p);
    copyFlash.value = "path";
    setTimeout(() => (copyFlash.value = null), 1200);
  } catch {
    /* ignore */
  }
}
async function deleteOpenFile(): Promise<void> {
  const f = currentFile.value;
  if (!f?.path) return;
  const ok = await ui.confirm({
    title: "Delete file?",
    description: `"${f.path}" will be deleted from the workspace. This cannot be undone.`,
    confirmLabel: "Delete",
    variant: "destructive",
  });
  if (!ok) return;
  await files.deletePath(f.path);
}

// Download — works for any kind. For text files this saves the on-disk
// version (the agent's view), not the in-editor dirty buffer.
const downloading = ref(false);
async function downloadOpenFile(): Promise<void> {
  const f = currentFile.value;
  if (!f?.path || !workspace.activeId) return;
  downloading.value = true;
  try {
    await apiDownloadFile(workspace.activeId, f.path);
  } catch (exc) {
    ui.toastError("Download", exc instanceof Error ? exc : new Error(String(exc)));
  } finally {
    downloading.value = false;
  }
}

/** Esc to exit review mode — matches Cursor's keymap. */
function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Escape" && inReview.value) {
    snapshots.exitReviewMode();
  }
}
onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => window.removeEventListener("keydown", onKeydown));

const scroller = ref<HTMLDivElement | null>(null);
const stickToBottom = ref(true);

/** Highlighted line HTML (one entry per source line). */
const highlightedLines = ref<string[]>([]);

const fileSize = computed(() => {
  const c = currentFile.value?.content ?? "";
  if (!c) return "";
  const bytes = new Blob([c]).size;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
});

const statusBadge = computed(() => {
  const f = currentFile.value;
  if (!f) return null;
  switch (f.status) {
    case "streaming":
      return { label: "writing…", color: "text-warning bg-warning/10" };
    case "writing":
      return { label: "saving…", color: "text-warning bg-warning/10" };
    case "done":
      return {
        label: f.isNew ? "created" : "updated",
        color: "text-success bg-success/10",
      };
    case "loaded":
      return null;
    case "loading":
      return { label: "loading…", color: "text-muted-foreground bg-muted" };
    case "error":
      return { label: "error", color: "text-destructive bg-destructive/10" };
  }
});

const isStreamingNow = computed(
  () =>
    currentFile.value?.status === "streaming" ||
    currentFile.value?.status === "writing"
);

/**
 * "Unviewable" only applies to truly opaque binaries — NOT to media we
 * have a renderer for. Without this guard the binary fallback ("Can't
 * show this file") would steal images / PDFs / audio / video before
 * FilePreview gets a chance to render them.
 */
const isUnviewable = computed(() => {
  const f = currentFile.value;
  if (!f) return false;
  if (previewKind.value !== null) return false;
  return Boolean(f.binary || f.reason);
});

const langLabel = computed(() => {
  const f = currentFile.value;
  if (!f) return "";
  // For known media kinds, show the extension (PNG / PDF / SVG / MP3…)
  // instead of falling back to "text" which is misleading for previews.
  if (f.kind && f.kind !== "text") {
    const ext = f.path.includes(".") ? f.path.split(".").pop()?.toUpperCase() : null;
    return ext ?? f.kind.toUpperCase();
  }
  const lang = langForPath(f.path);
  return lang ?? "text";
});

// ── Highlight pipeline ───────────────────────────────────────────────────
//
// Why a hard cap?
//   Shiki tokenises the WHOLE document each time, then we render every
//   line as a separate <div> via v-for. For a 50k-line file that's
//   200ms+ of main-thread work per update AND tens of thousands of DOM
//   nodes — the browser stalls and memory balloons. CodeMirror (Mode A)
//   handles this natively via line virtualization; the Shiki path is
//   only used in Mode B (live streaming) and falls back to plain text
//   beyond this threshold so huge file writes never freeze the UI.
const HIGHLIGHT_LINE_CAP = 5000;
const HIGHLIGHT_BYTE_CAP = 1_500_000; // ~1.5 MB

const highlightTruncated = ref<{ totalLines: number } | null>(null);

// One pending raf at a time; coalesces bursts of streaming updates into a
// single re-tokenization.
let rafId: number | null = null;
let pending = false;
let inFlight = false;

function scheduleHighlight(): void {
  if (rafId !== null) {
    pending = true;
    return;
  }
  rafId = requestAnimationFrame(async () => {
    rafId = null;
    pending = false;
    if (inFlight) {
      // Re-trigger after the current run finishes.
      pending = true;
      return;
    }
    inFlight = true;
    const f = currentFile.value;
    const fullSource = f?.content ?? "";
    const lang = langForPath(f?.path);

    // Decide if we need to truncate. Shorter of (line cap, byte cap).
    let source = fullSource;
    let truncatedTo: { totalLines: number } | null = null;
    if (fullSource.length > HIGHLIGHT_BYTE_CAP) {
      source = fullSource.slice(0, HIGHLIGHT_BYTE_CAP);
      truncatedTo = { totalLines: fullSource.split("\n").length };
    } else {
      const totalLines = fullSource.split("\n").length;
      if (totalLines > HIGHLIGHT_LINE_CAP) {
        source = fullSource
          .split("\n")
          .slice(0, HIGHLIGHT_LINE_CAP)
          .join("\n");
        truncatedTo = { totalLines };
      }
    }

    try {
      const lines = await highlightLines(source, lang);
      // Only commit if the file we highlighted is still the one in view.
      if (currentFile.value && currentFile.value.path === f?.path) {
        highlightedLines.value = lines;
        highlightTruncated.value = truncatedTo;
      }
    } finally {
      inFlight = false;
      if (pending) scheduleHighlight();
    }
  });
}

watch(
  () => [currentFile.value?.path, currentFile.value?.content?.length ?? 0],
  () => {
    if (!currentFile.value || isUnviewable.value) {
      highlightedLines.value = [];
      return;
    }
    scheduleHighlight();
  },
  { immediate: true }
);

onUnmounted(() => {
  if (rafId !== null) cancelAnimationFrame(rafId);
});

// ── Scrolling ────────────────────────────────────────────────────────────
function onScroll(): void {
  const el = scroller.value;
  if (!el) return;
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
  stickToBottom.value = distanceFromBottom < 60;
}

watch(
  () => currentFile.value?.path,
  () => {
    stickToBottom.value = true;
    void nextTick(() => {
      const el = scroller.value;
      if (el) el.scrollTop = 0;
    });
  }
);

watch(
  () => highlightedLines.value.length,
  async () => {
    if (!stickToBottom.value || !isStreamingNow.value) return;
    await nextTick();
    const el = scroller.value;
    if (el) el.scrollTop = el.scrollHeight;
  }
);
</script>

<template>
  <!--
    `min-w-0` here is critical: this section sits inside a Splitpanes
    Pane that gives it a percentage width. If a child wants more width
    (long code line, wide tab strip), the pane would grow past its
    allocation and squeeze the chat pane. min-w-0 + overflow-hidden on
    the section forces children to scroll inside the section instead.
  -->
  <section class="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-editor">
    <!-- VS Code-style tab strip — only renders when there are open tabs. -->
    <EditorTabs />

    <!-- ── Mode C header: review mode (back button + op label + stats) ── -->
    <header
      v-if="inReview && editorReview"
      class="flex items-center justify-between border-b border-border bg-card px-3 py-1.5 text-body"
    >
      <div class="flex min-w-0 items-center gap-2">
        <button
          type="button"
          class="rounded-sm border border-border bg-background px-1.5 py-0.5 font-mono text-caption text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          title="Back to file (Esc)"
          @click="snapshots.exitReviewMode()"
        >
          ← back
        </button>
        <span
          class="rounded-sm bg-primary/10 px-1.5 py-0.5 font-mono text-caption uppercase tracking-wide text-primary"
        >
          diff · {{ editorReview.toolName }}
        </span>
        <span class="truncate font-mono text-muted-foreground">
          {{ editorReview.path }}
        </span>
      </div>
      <div class="flex items-center gap-3 font-mono text-caption tabular-nums">
        <span v-if="editorReview.added > 0" class="text-success">+{{ editorReview.added }}</span>
        <span v-if="editorReview.removed > 0" class="text-destructive">-{{ editorReview.removed }}</span>
      </div>
    </header>

    <!-- ── Mode A/B header: file path + status + lang/size + save ──────── -->
    <header
      v-else
      class="editor-header flex items-center justify-between gap-2 border-b border-border bg-card px-3 py-1.5 text-body"
    >
      <div class="flex min-w-0 flex-1 items-center gap-2">
        <span class="min-w-0 truncate font-mono text-muted-foreground" :title="currentFile?.path">
          {{ currentFile ? currentFile.path : "no file open" }}
        </span>
        <!-- Dirty indicator (Mode A only) -->
        <span
          v-if="isEditableMode && dirty"
          class="inline-flex h-2 w-2 shrink-0 rounded-full bg-warning"
          title="Unsaved changes — press ⌘/Ctrl+S to save"
        ></span>
        <span
          v-if="statusBadge"
          :class="['shrink-0 rounded-sm px-1.5 py-0.5 text-caption font-mono', statusBadge.color]"
        >
          {{ statusBadge.label }}
        </span>
      </div>
      <div class="flex shrink-0 items-center gap-1.5 text-caption text-muted-foreground">
        <span
          v-if="saveError"
          class="hide-on-narrow rounded-sm bg-destructive/15 px-1.5 py-0.5 text-caption text-destructive"
          :title="saveError"
        >save failed</span>

        <button
          v-if="isEditableMode"
          type="button"
          :class="[
            'rounded-sm border px-1.5 py-0.5 font-mono text-caption transition-colors',
            dirty
              ? 'border-primary/50 bg-primary/10 text-primary hover:bg-primary/20'
              : 'border-border bg-background text-muted-foreground',
          ]"
          :disabled="!dirty || saving"
          :title="dirty ? 'Save (⌘/Ctrl+S)' : 'No changes to save'"
          @click="manualSave"
        >
          {{ saving ? "saving…" : dirty ? "● save" : "saved" }}
        </button>

        <span v-if="currentFile" class="hide-on-narrow font-mono uppercase tracking-wide">
          {{ langLabel }}
        </span>
        <span v-if="currentFile && fileSize" class="hide-on-narrow font-mono">{{ fileSize }}</span>

        <!-- Per-file actions — ALWAYS visible (small icons, ~120px total).
             At very narrow widths (<280px) the label badges above hide via
             container queries; the actions stay so the user is never stuck
             without close/copy/delete. -->
        <div v-if="currentFile" class="ml-1 flex items-center gap-0.5 border-l border-border/60 pl-1.5">
          <button
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
            :title="copyFlash === 'content' ? 'Copied!' : 'Copy file content'"
            @click="copyContent"
          >
            <Icon
              :icon="copyFlash === 'content' ? 'codicon:check' : 'codicon:copy'"
              class="h-[14px] w-[14px]"
            />
          </button>
          <button
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
            :title="copyFlash === 'path' ? 'Path copied!' : 'Copy file path'"
            @click="copyPath"
          >
            <Icon
              :icon="copyFlash === 'path' ? 'codicon:check' : 'codicon:link'"
              class="h-[14px] w-[14px]"
            />
          </button>
          <button
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="downloading"
            title="Download this file"
            @click="downloadOpenFile"
          >
            <Icon
              :icon="downloading ? 'codicon:loading' : 'codicon:cloud-download'"
              :class="downloading && 'animate-spin'"
              class="h-[14px] w-[14px]"
            />
          </button>
          <button
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-destructive/15 hover:text-destructive"
            title="Delete this file"
            @click="deleteOpenFile"
          >
            <Icon icon="codicon:trash" class="h-[14px] w-[14px]" />
          </button>
          <button
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
            title="Close file"
            @click="closeFile"
          >
            <Icon icon="codicon:close" class="h-[14px] w-[14px]" />
          </button>
        </div>
      </div>
    </header>

    <!-- ── Mode C body: full diff view (no truncation) ─────────────────── -->
    <div
      v-if="inReview && editorReview"
      class="flex-1 overflow-auto bg-editor"
    >
      <!-- Review mode: show all rows (no fade clip), but still defer to
           DiffView's `maxDiffLines` cap so a 50k-line diff doesn't freeze
           the UI. User can hit "render full" to opt in if they really need it. -->
      <DiffView
        :diff="editorReview.unifiedDiff"
        :max-rows="100000"
        :max-diff-lines="3000"
      />
    </div>

    <div
      v-else-if="!currentFile"
      class="flex flex-1 flex-col items-center justify-center text-center text-lead text-muted-foreground"
    >
      <div class="mb-2 text-h1 opacity-30">⌘</div>
      <p class="mb-1 text-foreground">No file open</p>
      <p class="max-w-xs text-body">
        Click any file in the left tree, or ask the agent to
        <span class="font-mono text-foreground">write</span>,
        <span class="font-mono text-foreground">read</span>, or
        <span class="font-mono text-foreground">edit</span> a file.
      </p>
    </div>

    <!-- IMAGE / PDF / SVG-preview / AUDIO / VIDEO viewer.
         MUST come before the unviewable fallback or PNGs/PDFs would
         render as "Can't show this file". -->
    <div
      v-else-if="previewKind && currentFile"
      class="flex flex-1 min-h-0 min-w-0 overflow-hidden bg-editor"
    >
      <FilePreview
        :key="currentFile.path + ':' + (svgShowAsCode ? 'code' : 'render')"
        :path="currentFile.path"
        :kind="previewKind"
        :show-as-code="svgShowAsCode"
        @toggle-svg-mode="(asCode: boolean) => (svgShowAsCode = asCode)"
      />
    </div>

    <div
      v-else-if="isUnviewable"
      class="flex flex-1 flex-col items-center justify-center text-center text-lead text-muted-foreground"
    >
      <div class="mb-2 text-h1 opacity-30">⊘</div>
      <p class="mb-1 text-foreground">Can't show this file</p>
      <p class="max-w-xs text-body">
        {{ currentFile.reason ?? "Binary content not displayed." }}
      </p>
    </div>

    <!--
      Mode A — editable. CodeMirror 6 with full editing, autocomplete,
      multi-cursor, Cmd/Ctrl+S to save. Re-mounts when the path changes
      so language pack + history reset cleanly.
    -->
    <div
      v-else-if="isEditableMode && currentFile"
      class="flex flex-1 min-h-0 min-w-0 overflow-hidden bg-editor"
    >
      <CodeEditor
        ref="codeEditorRef"
        :key="currentFile.path"
        :path="currentFile.path"
        :initial-content="currentFile.content ?? ''"
        @update:dirty="onDirty"
        @save="onSave"
      />
    </div>

    <!-- Mode B (live streaming) and Mode A fallback (loading/empty) — Shiki HTML -->
    <div
      v-else
      ref="scroller"
      class="flex-1 overflow-auto bg-editor"
      @scroll="onScroll"
    >
      <div
        v-if="highlightedLines.length === 0"
        class="px-4 py-3 text-body text-muted-foreground"
      >
        <span class="font-mono italic">
          {{ currentFile.status === "loading" ? "loading…" : "waiting for content…" }}
        </span>
      </div>
      <!--
        IMPORTANT: long source lines must SCROLL horizontally, not wrap.
        - <pre> gets `min-w-max` so it grows to fit the widest line.
        - Outer scroller already has `overflow-auto`, which then yields a
          horizontal scrollbar when the pre exceeds the column width.
        - Inner content uses `whitespace-pre` (preserves spaces, no wrap).
        - Line number column is sticky so it stays visible while scrolling
          right (Cursor / VSCode behavior).
      -->
      <pre
        v-else
        class="m-0 px-0 py-2 font-mono text-[12.5px] leading-[1.6] text-foreground"
        style="min-width: max-content;"
      ><code><div
          v-for="(line, i) in highlightedLines"
          :key="i"
          class="flex items-start"
        ><span
            class="sticky left-0 z-10 select-none pl-3 pr-3 text-right text-editor-line tabular-nums"
            :style="{
              minWidth: '3.2rem',
              backgroundColor: 'var(--editor-bg)',
              borderRight: '1px solid var(--border)',
            }"
          >{{ i + 1 }}</span><span class="whitespace-pre pl-3 pr-6"><span v-html="line || '&#8203;'" /><span
              v-if="isStreamingNow && i === highlightedLines.length - 1"
              class="ml-0.5 inline-block h-3 w-1.5 align-middle bg-foreground animate-pulse"
            /></span></div></code></pre>
      <!--
        Truncation banner — shown when the file exceeds HIGHLIGHT_LINE_CAP
        or HIGHLIGHT_BYTE_CAP. We highlighted the visible portion only so
        the browser stays responsive on huge pastes / generated files.
        Users can still open the full file in CodeMirror (Mode A) by
        navigating to its tab — that path uses native line virtualization.
      -->
      <div
        v-if="highlightTruncated"
        class="sticky bottom-0 z-20 mx-3 mb-3 flex items-center gap-2 rounded-md border border-amber-700/30 bg-amber-950/30 px-3 py-2 text-caption text-amber-200/80 shadow-lg"
      >
        <span class="text-lead leading-none">⚠</span>
        <span>
          Streaming preview truncated to first
          <strong class="font-semibold">{{ highlightedLines.length.toLocaleString() }}</strong>
          of <strong class="font-semibold">{{ highlightTruncated.totalLines.toLocaleString() }}</strong> lines for performance.
          Open the file from the tree to view in the full editor.
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
/*
  Container queries on the editor header. When the pane gets narrow
  (e.g. user drags the chat pane wider), the lang/size badges and the
  "save failed" pill hide so the action icons stay visible. Path is
  always truncated, so it shrinks gracefully.

  Container queries are native in modern browsers — no Tailwind plugin
  needed. The query unit `cqw` references the header's own width.
*/
.editor-header {
  container-type: inline-size;
  container-name: editor-header;
}
@container editor-header (max-width: 480px) {
  .hide-on-narrow {
    display: none !important;
  }
}
</style>
