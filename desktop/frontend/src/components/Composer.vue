<!--
  Composer — bottom prompt input.

  Cursor-style layout:

      ┌─────────────────────────────────────────────────────────┐
      │ [📎 chips]                                              │
      │ ─────────────────────────────────────────────────────── │
      │ Ask the agent…                                          │
      │                                                         │
      │ ─────────────────────────────────────────────────────── │
      │ [● open] [🛡 Auto] [Opus 4.7]   [⚙]    [📎] [▶ Send]    │
      └─────────────────────────────────────────────────────────┘

  The previous version was a bare textarea with a paperclip on the
  left and a send icon on the right — no inline model / mode controls,
  forcing the user to look up at a separate status row in ChatPane to
  know which model and permission mode they were about to send with.
  The new layout pulls all of those into the composer card itself
  (left side of the toolbar) so the input is self-contained, the way
  Cursor / Claude Code / ChatGPT all render their composers.

  Behaviour (unchanged from the old composer):
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
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";
import { useChatStore } from "../stores/chat";
import { useConfigStore } from "../stores/config";
import { useWorkspaceStore } from "../stores/workspace";
import { useFilesStore } from "../stores/files";
import { useUiStore } from "../stores/ui";
import { uploadAttachments } from "../api/attachments";
import QueueStrip from "./QueueStrip.vue";
import ModelPicker from "./ModelPicker.vue";
import PermissionModePicker from "./PermissionModePicker.vue";
import ChatSettingsMenu from "./ChatSettingsMenu.vue";

const chat = useChatStore();
const cfg = useConfigStore();
const ws = useWorkspaceStore();
const files = useFilesStore();
const ui = useUiStore();
const { pendingAttachments, queuedMessages, connState, isStreaming } = storeToRefs(chat);

const text = ref("");

// Native menu wiring (unchanged).
const composerTextarea = ref<HTMLTextAreaElement | null>(null);
function _onMenuFocusChat(): void {
  composerTextarea.value?.focus();
}
function _onMenuFindInChat(): void {
  composerTextarea.value?.focus();
  composerTextarea.value?.select();
}
onMounted(() => {
  window.addEventListener("menu-focus-chat", _onMenuFocusChat);
  window.addEventListener("menu-find-in-chat", _onMenuFindInChat);
});
onBeforeUnmount(() => {
  window.removeEventListener("menu-focus-chat", _onMenuFocusChat);
  window.removeEventListener("menu-find-in-chat", _onMenuFindInChat);
});

const fileInput = ref<HTMLInputElement | null>(null);
const isDragOver = ref(false);
const isUploading = ref(false);
const dragCounter = ref(0);

const totalPendingBytes = computed(() =>
  pendingAttachments.value.reduce((s, a) => s + (a.size || 0), 0),
);

// Focus state — when true, the composer card grows a stronger ring so
// the user has a clear "you're typing here" affordance. The bare-
// textarea version of this composer relied solely on the textarea's
// default focus outline, which read as "form field" rather than
// "primary chat input".
const focused = ref(false);

const placeholder = computed(() => {
  if (pendingAttachments.value.length > 0) {
    return "Add a question about your attached files…  (⌘/Ctrl + ↵ to send)";
  }
  if (chat.messages.length > 0) {
    return "Add a follow-up…  (⌘/Ctrl + ↵ to send)";
  }
  return "Plan, search, build anything…  (⌘/Ctrl + ↵ to send)";
});

// Color of the connection indicator dot in the toolbar.
const connDotClass = computed(() => {
  switch (connState.value) {
    case "open":
      return "bg-success";
    case "error":
    case "closed":
      return "bg-destructive";
    default:
      return "bg-warning";
  }
});

const connTitle = computed(() => {
  switch (connState.value) {
    case "open":
      return "Connected";
    case "connecting":
      return "Connecting…";
    case "error":
      return "Connection error";
    case "closed":
      return "Disconnected";
    default:
      return String(connState.value);
  }
});

function submit(): void {
  if (isUploading.value) return;
  if (!text.value.trim() && pendingAttachments.value.length === 0) return;
  if (cfg.requiresSetup) {
    ui.toast({
      message: "Sign in or add an AI key to start chatting.",
      kind: "info",
    });
    return;
  }
  if (chat.isStreaming) {
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
  const items = e.clipboardData?.files;
  if (!items || items.length === 0) return;
  e.preventDefault();
  await _uploadAndChip(Array.from(items));
}

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
  return Array.from(types).includes("Files");
}

function removeChip(localId: string): void {
  chat.removePendingAttachment(localId);
}

function isImageMime(mime: string): boolean {
  return mime.startsWith("image/");
}

const inputDisabled = computed(() => connState.value !== "open");
</script>

<template>
  <div
    class="relative border-t border-sidebar-border bg-sidebar px-3 py-2.5"
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

    <!-- Queued-messages tray. Lives above the composer card so an
         expanded queue doesn't push the typing area off-screen. -->
    <QueueStrip />

    <!-- ── Composer card ──────────────────────────────────────────────
         Single rounded container that wraps the textarea AND the
         toolbar so they read as one input surface. The transition
         on `focused` upgrades the border to the primary ring colour
         so the user has a clear "you are typing here" affordance. -->
    <div
      class="rounded-xl border bg-background transition-colors"
      :class="focused ? 'border-primary/60 shadow-sm shadow-primary/10' : 'border-border'"
    >
      <!-- Pending attachment chips — collapse to zero height when none. -->
      <div
        v-if="pendingAttachments.length > 0"
        class="flex flex-wrap items-center gap-1.5 border-b border-border px-3 pt-2 pb-2"
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

      <!-- Textarea row. No visible border here — the parent card owns
           the border, the textarea owns the typing surface. -->
      <textarea
        ref="composerTextarea"
        v-model="text"
        rows="3"
        :placeholder="placeholder"
        class="block w-full resize-none border-0 bg-transparent px-4 py-3 text-lead leading-relaxed text-foreground placeholder:text-muted-foreground/80 focus:outline-none font-sans"
        :disabled="inputDisabled"
        @keydown="onKeydown"
        @paste="onPaste"
        @focus="focused = true"
        @blur="focused = false"
      />

      <!-- Toolbar row. Mode + model + settings on the left, attach +
           send/stop on the right. Same width as the textarea so
           everything reads as one card. -->
      <div class="flex items-center gap-2 border-t border-border px-2 py-1.5">
        <!-- Connection dot — replaces the standalone status row in the
             chat header. Tooltip carries the verbose label. -->
        <span
          class="flex h-6 w-6 shrink-0 items-center justify-center"
          :title="connTitle"
        >
          <span
            class="inline-block h-1.5 w-1.5 rounded-full"
            :class="connDotClass"
            aria-hidden="true"
          />
        </span>

        <!-- Mode (Auto / Ask / Cautious) -->
        <PermissionModePicker />

        <!-- Model -->
        <ModelPicker />

        <!-- Streaming indicator. Sits between the mode/model chips and
             the right-side actions so the user sees instantly when pi
             is in the middle of a turn. -->
        <span
          v-if="isStreaming"
          class="ml-1 inline-flex items-center gap-1 text-caption text-warning"
        >
          <span class="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-warning" />
          streaming…
        </span>

        <span class="ml-auto" />

        <!-- Per-chat settings (permission mode, BYOK routing default,
             credit usage). Lives on the right of the toolbar so it sits
             next to the action cluster, not buried in a separate header. -->
        <ChatSettingsMenu />

        <!-- Attach files. -->
        <button
          type="button"
          class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="inputDisabled || isUploading"
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

        <!-- Send / queue / stop cluster. Same square footprint regardless
             of streaming state so the row width never jitters. -->
        <button
          v-if="!chat.isStreaming"
          type="button"
          :disabled="
            (!text.trim() && pendingAttachments.length === 0) ||
            inputDisabled ||
            isUploading
          "
          class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
          title="Send (⌘/Ctrl + ↵)"
          @click="submit"
        >
          <Icon icon="codicon:send" class="h-3.5 w-3.5" />
        </button>

        <template v-else>
          <button
            type="button"
            :disabled="
              (!text.trim() && pendingAttachments.length === 0) ||
              inputDisabled ||
              isUploading
            "
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-primary/60 bg-primary/15 text-primary transition-colors hover:bg-primary/25 disabled:cursor-not-allowed disabled:opacity-30"
            :title="`Queue (⌘/Ctrl + ↵) — pi will run this after the current turn. ${queuedMessages.length} queued.`"
            @click="submit"
          >
            <Icon icon="codicon:add" class="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-destructive text-destructive-foreground transition-opacity hover:opacity-90"
            title="Abort the current pi turn"
            @click="chat.abort"
          >
            <Icon icon="codicon:debug-stop" class="h-3.5 w-3.5" />
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
