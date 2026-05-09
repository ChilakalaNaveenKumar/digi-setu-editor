<!--
  Composer — bottom prompt input.

  Behaviour:
    Enter            → newline
    Cmd/Ctrl + Enter → submit (or queue when pi is busy)
    Cmd/Ctrl + V     → paste text (default), OR paste image/file → upload as attachment
    Drag-drop        → upload to workspace/uploads/, add chip
    Paperclip button → native file picker

  When attachments are pending, the chip strip above the textarea shows
  one chip per file with a remove (×) button. On submit, the chat
  store's sendPrompt prepends an "I just uploaded N files…" preamble
  (with agent-cwd-relative paths) so the agent reads them in its turn.

  Queueing: while pi is streaming, hitting submit *queues* the message
  + its current attachments. The queue is rendered by <QueueStrip />
  above the textarea (collapsed by default, expandable). The user can
  push (force-send-now), edit, or delete queued items. The chat store
  auto-flushes the head of the queue when the previous turn ends.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";
import { useChatStore } from "../stores/chat";
import { useWorkspaceStore } from "../stores/workspace";
import { useFilesStore } from "../stores/files";
import { useUiStore } from "../stores/ui";
import { uploadAttachments } from "../api/attachments";
import QueueStrip from "./QueueStrip.vue";

const chat = useChatStore();
const ws = useWorkspaceStore();
const files = useFilesStore();
const ui = useUiStore();
const { pendingAttachments, queuedMessages } = storeToRefs(chat);

const text = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
const isDragOver = ref(false);
const isUploading = ref(false);
const dragCounter = ref(0);

const totalPendingBytes = computed(() =>
  pendingAttachments.value.reduce((s, a) => s + (a.size || 0), 0),
);

function submit(): void {
  if (isUploading.value) return;
  // Allow submit when text is empty *as long as* there are pending
  // attachments — that's a valid intent (user dropped files, hit send
  // to ask "look at these").
  if (!text.value.trim() && pendingAttachments.value.length === 0) return;
  if (chat.isStreaming) {
    // Pi is mid-turn: enqueue instead of sending. The store snapshots
    // the current pendingAttachments onto the queued item and clears
    // the composer's chip strip so the next message starts fresh.
    chat.enqueueMessage(text.value);
  } else {
    chat.sendPrompt(text.value);
  }
  text.value = "";
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    submit();
  }
}

// ── attachment ingress: paste, drop, picker ────────────────────────────

async function _uploadAndChip(filesArr: File[]): Promise<void> {
  if (filesArr.length === 0) return;
  if (!ws.activeId) {
    ui.toastError("Upload attachments", new Error("no active workspace"));
    return;
  }
  isUploading.value = true;
  try {
    const result = await uploadAttachments(ws.activeId, filesArr);
    chat.addPendingAttachments(
      result.saved.map((s) => ({
        localId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: s.name,
        size: s.size,
        mime: s.mime,
        path: s.path,
        agentPath: s.agent_path,
      })),
    );
    // Refresh the file tree so the new files in workspace/uploads/
    // show up immediately. The watcher will eventually sync this on
    // its own, but the round-trip is annoying without an immediate
    // update.
    void files.refreshTree();
  } catch (exc) {
    ui.toastError("Upload failed", exc);
  } finally {
    isUploading.value = false;
  }
}

function openPicker(): void {
  fileInput.value?.click();
}

async function onPickerChange(e: Event): Promise<void> {
  const target = e.target as HTMLInputElement;
  const list = target.files;
  if (!list || list.length === 0) return;
  await _uploadAndChip(Array.from(list));
  target.value = "";
}

async function onPaste(e: ClipboardEvent): Promise<void> {
  // Only intercept when the clipboard carries actual files. Plain text
  // / HTML paste falls through to the default textarea handler so the
  // user can still paste their question normally.
  const items = e.clipboardData?.files;
  if (!items || items.length === 0) return;
  e.preventDefault();
  await _uploadAndChip(Array.from(items));
}

// Drag counter: dragenter/leave events fire on every child element
// during a drag, so a naive boolean flicker on/off as the cursor
// crosses internal nodes. Tracking enter/leave delta-style (industry
// standard for "real" drop zones) keeps the highlight stable for the
// entire hover.
function onDragEnter(e: DragEvent): void {
  if (!_dragHasFiles(e)) return;
  dragCounter.value += 1;
  isDragOver.value = true;
  e.preventDefault();
}
function onDragLeave(e: DragEvent): void {
  if (!_dragHasFiles(e)) return;
  dragCounter.value = Math.max(0, dragCounter.value - 1);
  if (dragCounter.value === 0) isDragOver.value = false;
}
function onDragOver(e: DragEvent): void {
  if (!_dragHasFiles(e)) return;
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
}
async function onDrop(e: DragEvent): Promise<void> {
  if (!_dragHasFiles(e)) return;
  e.preventDefault();
  dragCounter.value = 0;
  isDragOver.value = false;
  const list = e.dataTransfer?.files;
  if (!list || list.length === 0) return;
  await _uploadAndChip(Array.from(list));
}
function _dragHasFiles(e: DragEvent): boolean {
  const types = e.dataTransfer?.types;
  if (!types) return false;
  // "Files" is what browsers report for OS-level file drags; this
  // filters out internal HTML5 drag (e.g. the file tree's own intra-
  // tree drag-to-move). Internal drags use a custom MIME type which
  // we never set to "Files".
  return Array.from(types).includes("Files");
}

// ── chip helpers ───────────────────────────────────────────────────────

function removeChip(localId: string): void {
  chat.removePendingAttachment(localId);
}

function isImageMime(mime: string): boolean {
  return mime.startsWith("image/");
}
</script>

<template>
  <div
    class="relative border-t border-sidebar-border bg-sidebar"
    :class="isDragOver && 'ring-2 ring-primary ring-offset-0'"
    @dragenter="onDragEnter"
    @dragleave="onDragLeave"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <!-- Drop overlay — only shown while dragging files over the
         composer. Big, obvious, clearly says what's about to happen. -->
    <div
      v-if="isDragOver"
      class="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-primary/10 backdrop-blur-[1px]"
    >
      <div
        class="flex items-center gap-2 rounded-md border border-primary bg-card px-3 py-2 text-lead font-medium text-foreground shadow"
      >
        <Icon icon="codicon:cloud-upload" class="h-4 w-4 text-primary" />
        Drop to upload to workspace/uploads/
      </div>
    </div>

    <!-- Queued-messages tray. Lives above the attachment chips and the
         textarea so it doesn't push the typing area off-screen when
         expanded. Hidden entirely when the queue is empty. -->
    <QueueStrip />

    <!-- Pending attachment chips. Hidden when none pending so the
         composer's vertical footprint stays compact for typical chat. -->
    <div
      v-if="pendingAttachments.length > 0"
      class="flex flex-wrap items-center gap-1.5 px-3 pt-2"
    >
      <div
        v-for="att in pendingAttachments"
        :key="att.localId"
        class="group inline-flex max-w-[18rem] items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-body"
        :title="att.agentPath"
      >
        <Icon
          :icon="
            isImageMime(att.mime)
              ? 'codicon:file-media'
              : att.mime === 'application/pdf'
                ? 'codicon:file-pdf'
                : 'codicon:file'
          "
          class="h-3.5 w-3.5 shrink-0 text-muted-foreground"
        />
        <span class="truncate text-foreground">{{ att.name }}</span>
        <span class="shrink-0 text-caption text-muted-foreground">
          {{
            att.size < 1024
              ? `${att.size} B`
              : att.size < 1024 * 1024
                ? `${(att.size / 1024).toFixed(1)} KB`
                : `${(att.size / 1024 / 1024).toFixed(1)} MB`
          }}
        </span>
        <button
          type="button"
          class="ml-0.5 rounded-sm p-0.5 text-muted-foreground opacity-60 transition-opacity hover:bg-muted hover:text-foreground hover:opacity-100"
          :title="`Remove ${att.name}`"
          @click="removeChip(att.localId)"
        >
          <Icon icon="codicon:close" class="h-3 w-3" />
        </button>
      </div>
      <span
        v-if="pendingAttachments.length > 1"
        class="ml-1 text-caption text-muted-foreground"
        :title="`Total ${totalPendingBytes} bytes across ${pendingAttachments.length} files`"
      >
        {{ pendingAttachments.length }} files queued
      </span>
    </div>

    <!-- All action buttons are icon-only square affordances (h-9 w-9)
         so the row stays compact and consistent. Tooltips carry the
         label. Paperclip on the left; on the right the row morphs
         based on streaming state:
              idle      → [send]
              streaming → [queue] [abort]
         Same square footprint regardless, so the textarea width never
         jumps when pi starts/stops streaming. -->
    <div class="flex items-end gap-2 px-4 py-3">
      <button
        type="button"
        class="flex h-9 w-9 shrink-0 items-center justify-center self-end rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
        :disabled="chat.connState !== 'open' || isUploading"
        :title="isUploading ? 'Uploading…' : 'Attach files (⌘/Ctrl + V to paste)'"
        @click="openPicker"
      >
        <Icon
          :icon="isUploading ? 'codicon:loading' : 'mdi:paperclip'"
          :class="isUploading && 'animate-spin'"
          class="h-4 w-4"
        />
      </button>
      <input
        ref="fileInput"
        type="file"
        multiple
        class="hidden"
        @change="onPickerChange"
      />

      <textarea
        v-model="text"
        rows="3"
        :placeholder="
          pendingAttachments.length > 0
            ? 'Add a question about your attached files…  (⌘/Ctrl + ↵ to send)'
            : 'Ask the agent…  (⌘/Ctrl + ↵ to send)'
        "
        class="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-lead leading-relaxed text-foreground placeholder:text-muted-foreground outline-none focus:border-ring font-sans"
        :disabled="chat.connState !== 'open'"
        @keydown="onKeydown"
        @paste="onPaste"
      />

      <!-- Idle: single primary Send icon button. -->
      <button
        v-if="!chat.isStreaming"
        type="button"
        :disabled="
          (!text.trim() && pendingAttachments.length === 0) ||
          chat.connState !== 'open' ||
          isUploading
        "
        class="flex h-9 w-9 shrink-0 items-center justify-center self-end rounded-md bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
        title="Send (⌘/Ctrl + ↵)"
        @click="submit"
      >
        <Icon icon="codicon:send" class="h-4 w-4" />
      </button>

      <!-- Streaming: queue + abort, both icon-only and same square
           footprint as Send so the row width is identical idle vs
           streaming (no jitter). -->
      <template v-else>
        <button
          type="button"
          :disabled="
            (!text.trim() && pendingAttachments.length === 0) ||
            chat.connState !== 'open' ||
            isUploading
          "
          class="flex h-9 w-9 shrink-0 items-center justify-center self-end rounded-md border border-primary/60 bg-primary/15 text-primary transition-colors hover:bg-primary/25 disabled:cursor-not-allowed disabled:opacity-30"
          :title="`Queue (⌘/Ctrl + ↵) — pi will run this after the current turn. ${queuedMessages.length} queued.`"
          @click="submit"
        >
          <Icon icon="codicon:add" class="h-4 w-4" />
        </button>
        <button
          type="button"
          class="flex h-9 w-9 shrink-0 items-center justify-center self-end rounded-md bg-destructive text-destructive-foreground transition-opacity hover:opacity-90"
          title="Abort the current pi turn"
          @click="chat.abort"
        >
          <Icon icon="codicon:debug-stop" class="h-4 w-4" />
        </button>
      </template>
    </div>
  </div>
</template>
