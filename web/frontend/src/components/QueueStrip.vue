<!--
  QueueStrip — collapsed/expandable tray showing queued user messages.

  Design intent:

    * Hidden entirely when queue is empty so the composer stays compact
      for typical chat.
    * Collapsed shows ONE line: "▾ N queued" + a thin preview of the
      next item's text. Click anywhere on this strip to expand.
    * Expanded shows each queued message as a card with:
        - the message text (truncated to ~3 lines, click "edit" to
          turn it into an editable textarea)
        - attachment chips (scaled down — same pipeline as Composer)
        - PUSH button (paper-plane icon) — sends NOW, aborting any
          in-flight pi turn first
        - EDIT button — toggles inline textarea
        - DELETE button — removes from queue without sending

    * The first item in the queue is decorated as "next up" with a
      subtle accent ring so the user knows which one will fire when
      pi finishes its current turn.

  Implementation notes:

    * Inline editing is a single-component textarea bound to a local
      `editText` ref. We commit on blur OR on cmd/ctrl + enter, and
      cancel on Esc. We never auto-save while typing — the queue is
      a deliberate "this WILL fire" data store, not a draft area.
    * Push fires the chat-store's `pushQueued(id)` which handles the
      abort + wait-for-isStreaming-false dance internally; the strip
      just shows a tiny spinner during the ~50ms it takes.
-->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";

import { useChatStore } from "../stores/chat";

const chat = useChatStore();
const { queuedMessages, isStreaming } = storeToRefs(chat);

const expanded = ref(false);
const editingId = ref<string | null>(null);
const editText = ref("");
const pushingId = ref<string | null>(null);
const editTextarea = ref<HTMLTextAreaElement | null>(null);

const queueCount = computed(() => queuedMessages.value.length);
const hasQueue = computed(() => queueCount.value > 0);

// Auto-collapse when the queue empties so the next time a user starts
// queueing they see the collapsed peek strip first (less visual
// clutter). Auto-expand on the FIRST enqueue so the user notices their
// message landed somewhere — relying on a tiny "▾ 1 queued" pill alone
// is a recipe for "where did my message go?" confusion.
watch(queueCount, (n, prev) => {
  if (n === 0) {
    expanded.value = false;
    editingId.value = null;
  } else if (prev === 0 && n === 1) {
    expanded.value = true;
  }
});

// Snapshot of the first queued item used for the collapsed preview.
const headPreview = computed(() => {
  const head = queuedMessages.value[0];
  if (!head) return "";
  const text = head.text.replace(/\s+/g, " ").trim();
  if (text.length === 0 && head.attachments.length > 0) {
    return `(attachment only — ${head.attachments.length} file${head.attachments.length === 1 ? "" : "s"})`;
  }
  return text.length > 80 ? text.slice(0, 77) + "…" : text;
});

function toggleExpanded(): void {
  expanded.value = !expanded.value;
  if (!expanded.value) editingId.value = null;
}

function startEdit(id: string, currentText: string): void {
  editingId.value = id;
  editText.value = currentText;
  void nextTick(() => {
    editTextarea.value?.focus();
    // Place cursor at end so they can keep typing without re-selecting.
    if (editTextarea.value) {
      const len = editTextarea.value.value.length;
      editTextarea.value.setSelectionRange(len, len);
    }
  });
}

function commitEdit(id: string): void {
  if (editingId.value !== id) return;
  const trimmed = editText.value.trim();
  // Empty edit means "delete me" — same as clicking the X button. We
  // surface this as an explicit branch so a user who clears the box
  // and clicks away doesn't end up with a literally-empty queued
  // prompt that pi would just skip.
  if (!trimmed) {
    chat.removeQueued(id);
  } else {
    chat.editQueued(id, trimmed);
  }
  editingId.value = null;
  editText.value = "";
}

function cancelEdit(): void {
  editingId.value = null;
  editText.value = "";
}

function onEditKeydown(e: KeyboardEvent, id: string): void {
  if (e.key === "Escape") {
    e.preventDefault();
    cancelEdit();
  } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    commitEdit(id);
  }
}

async function pushNow(id: string): Promise<void> {
  pushingId.value = id;
  try {
    await chat.pushQueued(id);
  } finally {
    pushingId.value = null;
  }
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
</script>

<template>
  <Transition
    enter-active-class="transition-all duration-150 ease-out"
    leave-active-class="transition-all duration-100 ease-in"
    enter-from-class="opacity-0 -translate-y-1"
    leave-to-class="opacity-0 -translate-y-1"
  >
    <!-- We use a single root-level transition so the WHOLE tray
         appears/disappears as one unit when the queue empties. -->
    <div v-if="hasQueue" class="border-b border-sidebar-border bg-sidebar/60">
      <!-- Collapsed peek strip — single line, click to expand. -->
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-muted/40"
        :title="expanded ? 'Hide queue' : 'Show queue'"
        @click="toggleExpanded"
      >
        <Icon
          :icon="expanded ? 'codicon:chevron-down' : 'codicon:chevron-right'"
          class="h-3 w-3 shrink-0 text-muted-foreground"
        />
        <span
          class="shrink-0 rounded bg-primary/15 px-1.5 py-0.5 font-mono text-caption font-semibold text-primary"
          :title="`${queueCount} message${queueCount === 1 ? '' : 's'} waiting to send`"
        >{{ queueCount }} queued</span>
        <span
          v-if="!expanded"
          class="min-w-0 flex-1 truncate text-muted-foreground"
        >{{ headPreview }}</span>
        <span
          v-if="!expanded && isStreaming"
          class="shrink-0 font-mono text-caption text-muted-foreground"
        >will fire after current turn</span>
      </button>

      <!-- Expanded list -->
      <div v-if="expanded" class="max-h-[40vh] overflow-y-auto px-2 pb-2">
        <div
          v-for="(item, idx) in queuedMessages"
          :key="item.id"
          :class="[
            'group mt-1.5 rounded-md border bg-card px-2.5 py-2 text-body transition-colors',
            idx === 0
              ? 'border-primary/40 ring-1 ring-primary/20'
              : 'border-border',
          ]"
        >
          <!-- Header row: index + head badge + actions -->
          <div class="flex items-center gap-1.5">
            <span class="font-mono text-caption text-muted-foreground">#{{ idx + 1 }}</span>
            <span
              v-if="idx === 0"
              class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-caption uppercase tracking-wide text-primary"
              title="This will run as soon as the current pi turn finishes."
            >next up</span>
            <span class="ml-auto flex items-center gap-0.5">
              <button
                type="button"
                class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Edit this queued message"
                :disabled="editingId === item.id"
                @click="startEdit(item.id, item.text)"
              >
                <Icon icon="codicon:edit" class="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                class="rounded p-1 text-success/80 hover:bg-success/10 hover:text-success disabled:opacity-30 disabled:cursor-not-allowed"
                :title="
                  isStreaming
                    ? 'Send now (aborts the current pi turn first)'
                    : 'Send now'
                "
                :disabled="pushingId === item.id"
                @click="pushNow(item.id)"
              >
                <Icon
                  :icon="pushingId === item.id ? 'codicon:loading' : 'codicon:send'"
                  :class="pushingId === item.id && 'animate-spin'"
                  class="h-3.5 w-3.5"
                />
              </button>
              <button
                type="button"
                class="rounded p-1 text-destructive/70 hover:bg-destructive/10 hover:text-destructive"
                title="Remove from queue (do not send)"
                @click="chat.removeQueued(item.id)"
              >
                <Icon icon="codicon:trash" class="h-3.5 w-3.5" />
              </button>
            </span>
          </div>

          <!-- Body: text (read-only OR editable) -->
          <div class="mt-1">
            <textarea
              v-if="editingId === item.id"
              ref="editTextarea"
              v-model="editText"
              rows="3"
              class="w-full resize-y rounded border border-input bg-background px-2 py-1.5 font-sans text-body outline-none focus:border-ring"
              placeholder="Edit your queued message…"
              @keydown="(e) => onEditKeydown(e, item.id)"
              @blur="commitEdit(item.id)"
            />
            <div
              v-else
              class="line-clamp-3 whitespace-pre-wrap break-words text-foreground/90"
            >{{ item.text || "(no text — attachments only)" }}</div>
            <div
              v-if="editingId === item.id"
              class="mt-1 flex items-center gap-2 font-mono text-caption text-muted-foreground"
            >
              <span>⌘/Ctrl + ↵ to save</span>
              <span>·</span>
              <span>Esc to cancel</span>
              <span>·</span>
              <span>blank + save = delete</span>
            </div>
          </div>

          <!-- Attachments bound to this queued item -->
          <div
            v-if="item.attachments.length > 0"
            class="mt-1.5 flex flex-wrap items-center gap-1"
          >
            <div
              v-for="att in item.attachments"
              :key="att.localId"
              class="inline-flex max-w-[14rem] items-center gap-1 rounded border border-border bg-muted/30 px-1.5 py-0.5 text-caption"
              :title="att.agentPath"
            >
              <Icon
                :icon="
                  att.mime.startsWith('image/')
                    ? 'codicon:file-media'
                    : att.mime === 'application/pdf'
                      ? 'codicon:file-pdf'
                      : 'codicon:file'
                "
                class="h-3 w-3 shrink-0 text-muted-foreground"
              />
              <span class="truncate text-foreground/80">{{ att.name }}</span>
              <span class="shrink-0 text-muted-foreground">{{ humanSize(att.size) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>
