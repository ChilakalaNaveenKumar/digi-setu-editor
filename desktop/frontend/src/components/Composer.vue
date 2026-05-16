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

  Behaviour:
    Enter            → submit (or queue when pi is busy) — matches
                       ChatGPT / Cursor / Claude conventions so the
                       overwhelming majority of users get the result
                       they expect on the very first keystroke.
    Shift + Enter    → newline (multi-line composition)
    Cmd/Ctrl + Enter → submit (kept as a power-user alias so users
                       who learnt the old binding don't get surprised)
    Cmd/Ctrl + V     → paste text (default), OR paste image/file → upload as attachment
    Drag-drop        → upload to workspace/uploads/, add chip
    Paperclip button → native file picker

  IME composition (CJK / accented input methods) suppresses Enter-to-
  send so confirming a candidate word doesn't accidentally fire the
  message — same guard ChatGPT and Slack use.

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
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";
import { useChatStore } from "../stores/chat";
import { useConfigStore } from "../stores/config";
import { useWorkspaceStore } from "../stores/workspace";
import { useFilesStore } from "../stores/files";
import { useUiStore } from "../stores/ui";
import { apiJson } from "../api/client";
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
const { pendingAttachments, queuedMessages, connState, isStreaming, isAborting, lastErrorCode } = storeToRefs(chat);

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
  // Caret movement that doesn't change the text (arrow keys, mouse
  // click placing the caret) still needs to update the mention popup
  // visibility — textarea has no dedicated event for this so we
  // hook the document-level signal.
  document.addEventListener("selectionchange", onComposerSelectionChange);
});
onBeforeUnmount(() => {
  window.removeEventListener("menu-focus-chat", _onMenuFocusChat);
  window.removeEventListener("menu-find-in-chat", _onMenuFindInChat);
  document.removeEventListener("selectionchange", onComposerSelectionChange);
});

const fileInput = ref<HTMLInputElement | null>(null);
const isDragOver = ref(false);
const isUploading = ref(false);
const dragCounter = ref(0);

// ── @-mention autocomplete state ───────────────────────────────────────
//
// Mirrors the web copy — see `web/frontend/src/components/Composer.vue`.
// On desktop we additionally include workspace-scoped skills (typst
// compile-loop seeded by the env probe + anything the user dropped into
// `<workspace>/.digi-setu/skills/`) by passing `workspace_id` to the
// listing endpoint.
interface SkillSummary {
  name: string;
  description: string;
  source: "global" | "workspace";
}
const skillsLoaded = ref(false);
const skillsCatalogue = ref<SkillSummary[]>([]);
const mentionQuery = ref<string | null>(null);
const mentionStart = ref(0);
const mentionSelectedIdx = ref(0);

const mentionMatches = computed<SkillSummary[]>(() => {
  if (mentionQuery.value === null) return [];
  const q = mentionQuery.value.toLowerCase();
  const all = skillsCatalogue.value;
  if (!q) return all.slice(0, 8);
  const prefix = all.filter((s) => s.name.startsWith(q));
  const sub = all.filter((s) => !s.name.startsWith(q) && s.name.includes(q));
  return [...prefix, ...sub].slice(0, 8);
});

async function loadSkillsCatalogue(): Promise<void> {
  if (skillsLoaded.value) return;
  try {
    const qs = ws.activeId ? `?workspace_id=${encodeURIComponent(ws.activeId)}` : "";
    const r = await apiJson<{ skills: SkillSummary[] }>(`/api/skills${qs}`);
    skillsCatalogue.value = r.skills || [];
  } catch (exc) {
    console.warn("[composer] skills load failed", exc);
  } finally {
    skillsLoaded.value = true;
  }
}

function detectMention(value: string, caret: number): { start: number; query: string } | null {
  if (caret <= 0) return null;
  const minStart = Math.max(0, caret - 64);
  for (let i = caret - 1; i >= minStart; i -= 1) {
    const ch = value[i];
    if (ch === "@") {
      const prev = i === 0 ? "" : value[i - 1];
      if (prev !== "" && !/\s/.test(prev)) return null;
      const query = value.slice(i + 1, caret);
      if (!/^[a-zA-Z0-9-]*$/.test(query)) return null;
      return { start: i, query: query.toLowerCase() };
    }
    if (/\s/.test(ch)) return null;
  }
  return null;
}

function recomputeMentionState(): void {
  const ta = composerTextarea.value;
  if (!ta) return;
  const caret = ta.selectionStart ?? text.value.length;
  const m = detectMention(text.value, caret);
  if (!m) {
    mentionQuery.value = null;
    return;
  }
  if (!skillsLoaded.value) void loadSkillsCatalogue();
  mentionStart.value = m.start;
  mentionQuery.value = m.query;
  mentionSelectedIdx.value = 0;
}

function onComposerInput(): void {
  recomputeMentionState();
}

function onComposerSelectionChange(): void {
  recomputeMentionState();
}

function insertMention(name: string): void {
  const ta = composerTextarea.value;
  if (!ta || mentionQuery.value === null) return;
  const caret = ta.selectionStart ?? text.value.length;
  const before = text.value.slice(0, mentionStart.value);
  const after = text.value.slice(caret);
  const inserted = `@${name} `;
  text.value = before + inserted + after;
  mentionQuery.value = null;
  const newCaret = before.length + inserted.length;
  void nextTick(() => {
    const el = composerTextarea.value;
    if (!el) return;
    el.focus();
    el.setSelectionRange(newCaret, newCaret);
  });
}

function closeMention(): void {
  mentionQuery.value = null;
}

const mentionOpen = computed(
  () => mentionQuery.value !== null && mentionMatches.value.length > 0,
);

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
    return "Add a question about your attached files…  (↵ to send, ⇧↵ for newline)";
  }
  if (chat.messages.length > 0) {
    return "Add a follow-up…  (↵ to send, ⇧↵ for newline)";
  }
  return "Plan, search, build anything…  (↵ to send, ⇧↵ for newline)";
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
  // Three "send-now is unsafe" cases all funnel into the local
  // queue (which the chat store auto-drains the moment pi is free
  // and the SSE stream is open again):
  //   1. pi is mid-turn (existing behaviour);
  //   2. SSE transport is reconnecting after a blip — POST /prompt
  //      would race the new connection and the rate-limiter could
  //      misattribute the slot;
  //   3. the runtime hasn't reported `_session_info` yet (initial
  //      connecting on a brand-new tab).
  // In all three the user keeps their text in the queue strip
  // above the composer, sees it fire automatically, and the
  // "Reconnecting…" pill no longer eats their typing.
  const transportNotReady = connState.value !== "open";
  if (chat.isStreaming || transportNotReady) {
    chat.enqueueMessage(text.value);
  } else {
    chat.sendPrompt(text.value);
  }
  text.value = "";
}

function onKeydown(e: KeyboardEvent): void {
  // Skill-mention popup intercepts navigation keys. Branch BEFORE the
  // submit fallback so Enter inserts the highlighted skill instead of
  // firing the prompt.
  if (mentionOpen.value) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const n = mentionMatches.value.length;
      mentionSelectedIdx.value = (mentionSelectedIdx.value + 1) % n;
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      const n = mentionMatches.value.length;
      mentionSelectedIdx.value = (mentionSelectedIdx.value - 1 + n) % n;
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      closeMention();
      return;
    }
    if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      const pick = mentionMatches.value[mentionSelectedIdx.value];
      if (pick) insertMention(pick.name);
      return;
    }
  }

  if (e.key !== "Enter") return;
  // Don't intercept Enter while the user is committing an IME
  // composition (CJK, accent menus, autocorrect popups). `isComposing`
  // is the modern signal; `keyCode === 229` is the legacy fallback
  // some browsers / IMEs still emit even when isComposing is false.
  if (e.isComposing || e.keyCode === 229) return;
  // Shift+Enter inserts a newline (default textarea behaviour) — we
  // bail out so the browser handles it.
  if (e.shiftKey) return;
  // Plain Enter, or the legacy Cmd/Ctrl+Enter alias, both submit.
  // Alt+Enter is left as a soft newline so users who reach for that
  // muscle memory still get a line break instead of a send.
  if (e.altKey) return;
  e.preventDefault();
  submit();
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

// Composer typing should NEVER be blocked just because the SSE
// transport is mid-reconnect. EventSource flickers between `open`
// and `connecting` on every momentary network blip (Wi-Fi roam,
// laptop wake-from-sleep, server keep-alive miss); blocking input
// on that state made the chat feel broken — users would start
// typing, see "Reconnecting…" appear under the textarea, and lose
// the cursor mid-word until the stream re-opened. Now: typing is
// always allowed; if `submit()` fires while the stream is still
// re-opening, the message goes into the local queue and replays
// the moment the runtime accepts the next prompt (same path as
// "send while pi is mid-turn"). The only state that legitimately
// blocks input is a HARD error surfaced as `lastErrorCode` — at
// that point the SessionDisconnectedCard takes over the UI and
// the composer below is unreachable anyway, so this is more of a
// defensive guard than a UX gate.
const inputDisabled = computed(() => !!lastErrorCode.value);
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
      <div class="relative">
        <textarea
          ref="composerTextarea"
          v-model="text"
          rows="3"
          :placeholder="placeholder"
          class="block w-full resize-none border-0 bg-transparent px-4 py-3 text-lead leading-relaxed text-foreground placeholder:text-muted-foreground/80 focus:outline-none font-sans"
          :disabled="inputDisabled"
          @input="onComposerInput"
          @keydown="onKeydown"
          @paste="onPaste"
          @focus="focused = true"
          @blur="focused = false"
        />

        <!-- @-mention skill picker. Floats above the textarea so it
             never gets clipped by the parent card. `mousedown.prevent`
             keeps the textarea focused while clicking, otherwise the
             blur fires first and the popup disappears before the
             click registers. -->
        <div
          v-if="mentionOpen"
          class="absolute bottom-full left-2 right-2 z-20 mb-1 max-h-64 overflow-y-auto rounded-md border border-border bg-popover shadow-lg ring-1 ring-black/10"
          @mousedown.prevent
        >
          <ul class="py-1">
            <li
              v-for="(sk, idx) in mentionMatches"
              :key="sk.name"
              class="cursor-pointer px-3 py-1.5"
              :class="
                idx === mentionSelectedIdx
                  ? 'bg-primary/10 text-foreground'
                  : 'text-foreground hover:bg-muted'
              "
              @mouseenter="mentionSelectedIdx = idx"
              @click="insertMention(sk.name)"
            >
              <div class="flex items-center gap-2">
                <code class="text-body font-semibold">@{{ sk.name }}</code>
                <span
                  class="rounded bg-muted px-1 text-caption text-muted-foreground"
                >{{ sk.source }}</span>
              </div>
              <p
                v-if="sk.description"
                class="mt-0.5 truncate text-caption text-muted-foreground"
              >{{ sk.description }}</p>
            </li>
          </ul>
        </div>
      </div>

      <!-- Toolbar row. Mode + model + settings on the left, attach +
           send/stop on the right. Same width as the textarea so
           everything reads as one card. -->
      <!-- flex-wrap is critical for narrow windows (11-inch laptops, mobile,
           any time the chat pane is shrunk). Without it the toolbar
           overflows horizontally and the send/queue button gets cut off. -->
      <div
        class="composer-toolbar flex flex-wrap items-center gap-y-1.5 gap-x-2 border-t border-border px-2 py-1.5"
      >
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

        <!-- Stop pill. Stays visible while `isAborting` so the user
             gets clear feedback that their click registered. Backend
             abort has a 4 s grace + force-kill escalation; the
             worst-case pill state is "Stopping…" for ~5 s. See
             stores/chat.ts for the full two-stage abort rationale. -->
        <button
          v-if="isStreaming || isAborting"
          type="button"
          :disabled="isAborting"
          :class="[
            'ml-1 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-caption transition-colors',
            isAborting
              ? 'cursor-wait border-destructive/30 bg-destructive/5 text-destructive/80'
              : 'border-destructive/40 bg-destructive/10 text-destructive hover:border-destructive hover:bg-destructive hover:text-destructive-foreground',
          ]"
          :title="isAborting ? 'Stopping the in-flight response…' : 'Stop the current response'"
          @click="chat.abort"
        >
          <span
            :class="[
              'inline-block h-1.5 w-1.5 animate-pulse rounded-full',
              isAborting ? 'bg-destructive/60' : 'bg-destructive',
            ]"
          />
          <span>{{ isAborting ? "Stopping…" : "Stop" }}</span>
          <Icon
            :icon="isAborting ? 'codicon:loading' : 'codicon:debug-stop'"
            :class="['h-3 w-3', isAborting && 'animate-spin']"
          />
        </button>

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

        <!-- Send button — fired when pi is idle. -->
        <button
          v-if="!chat.isStreaming"
          type="button"
          :disabled="
            (!text.trim() && pendingAttachments.length === 0) ||
            inputDisabled ||
            isUploading
          "
          class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
          title="Send (↵ — use ⇧↵ for a newline)"
          @click="submit"
        >
          <Icon icon="codicon:send" class="h-3.5 w-3.5" />
        </button>

        <!-- Queue button — visually distinct from Send (different icon,
             explicit "Queue" label, count badge) so users notice that
             Enter while pi is streaming enqueues rather than sends. -->
        <button
          v-else
          type="button"
          :disabled="
            (!text.trim() && pendingAttachments.length === 0) ||
            inputDisabled ||
            isUploading
          "
          class="flex h-7 min-w-[3.5rem] shrink-0 items-center justify-center gap-1 rounded-md border border-primary/60 bg-primary/25 px-2 text-primary transition-colors hover:bg-primary/35 disabled:cursor-not-allowed disabled:opacity-30"
          :title="`Queue (↵) — pi will run this after the current turn. ${queuedMessages.length} already queued.`"
          @click="submit"
        >
          <Icon icon="mdi:playlist-plus" class="h-4 w-4" />
          <span class="text-caption font-semibold">
            Queue<span v-if="queuedMessages.length > 0">+{{ queuedMessages.length }}</span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>
