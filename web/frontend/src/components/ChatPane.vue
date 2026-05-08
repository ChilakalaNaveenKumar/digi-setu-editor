<!--
  ChatPane — right column. In web mode: simple header (status dot +
  model picker + settings gear) → MessageList → Composer. In desktop
  mode: a Cursor-style tab strip at the top with all chats in the
  current workspace, plus quick-action icons (+ new, 🕐 history,
  ⋯ overflow) — so the user can hop between threads in the same
  folder without leaving the IDE shell.

  Per-turn token/cost stats live inside each assistant bubble; the user's
  plan-level usage lives in ChatSettingsMenu (gear icon). We deliberately
  no longer render a session-total ticker here — it conflated raw model
  cost with billed usage and read as alarming.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import { useBillingStore } from "../stores/billing";
import { useChatStore } from "../stores/chat";
import { useChatSessionStore } from "../stores/chat-session";
import { useConfigStore } from "../stores/config";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import type { SessionRecord } from "../api/types";
import ChatErrorBanner from "./ChatErrorBanner.vue";
import Composer from "./Composer.vue";
import ChatSettingsMenu from "./ChatSettingsMenu.vue";
import MessageList from "./MessageList.vue";
import ModelPicker from "./ModelPicker.vue";

const chat = useChatStore();
const billing = useBillingStore();
const chatSession = useChatSessionStore();
const cfg = useConfigStore();
const ws = useWorkspaceStore();
const ui = useUiStore();
const router = useRouter();

const { messages, isStreaming, connState, lastError } = storeToRefs(chat);
const { exhausted } = storeToRefs(billing);
const { sessions, activeId: activeSessionId } = storeToRefs(chatSession);
const { mode } = storeToRefs(cfg);

const isDesktopMode = computed(() => mode.value === "desktop");

// History popover (🕐 icon). We render the full list of chats with a
// search box so users with dozens of threads in one workspace don't
// have to horizontally scroll the tab strip to find the right one.
const historyOpen = ref(false);
const historyQuery = ref("");
const filteredHistory = computed<SessionRecord[]>(() => {
  const q = historyQuery.value.trim().toLowerCase();
  if (!q) return sessions.value;
  return sessions.value.filter((s) =>
    (s.title || "Untitled chat").toLowerCase().includes(q),
  );
});

// Overflow popover (⋯ icon) — rename / delete current chat.
const overflowOpen = ref(false);

const busy = ref(false);

function switchTo(sid: string): void {
  if (sid === activeSessionId.value) return;
  const wsid = ws.activeId;
  if (!wsid) return;
  router.push({ name: "chat", params: { sid }, query: { wsid } });
}

async function newChat(): Promise<void> {
  const wsid = ws.activeId;
  if (!wsid || busy.value) return;
  busy.value = true;
  try {
    const s = await chatSession.create(wsid);
    router.push({ name: "chat", params: { sid: s.id }, query: { wsid } });
  } catch (exc) {
    ui.toastError("Could not create chat", exc);
  } finally {
    busy.value = false;
  }
}

async function renameCurrent(): Promise<void> {
  overflowOpen.value = false;
  const sid = activeSessionId.value;
  if (!sid) return;
  const current = sessions.value.find((s) => s.id === sid);
  const next = window.prompt("Rename chat:", current?.title || "Untitled chat");
  if (!next) return;
  try {
    await chatSession.rename(sid, next);
  } catch (exc) {
    ui.toastError("Could not rename", exc);
  }
}

async function deleteCurrent(): Promise<void> {
  overflowOpen.value = false;
  const sid = activeSessionId.value;
  const wsid = ws.activeId;
  if (!sid || !wsid) return;
  const ok = await ui.confirm({
    title: "Delete this chat?",
    description: "Files in the workspace are kept.",
    confirmLabel: "Delete",
    cancelLabel: "Cancel",
    variant: "destructive",
  });
  if (!ok) return;
  try {
    await chatSession.remove(sid);
    // Hop to the next-most-recent chat, or auto-create if this was
    // the last one. Either way the user stays inside the workspace.
    const next = chatSession.sessions[0];
    if (next) {
      router.replace({ name: "chat", params: { sid: next.id }, query: { wsid } });
    } else {
      const fresh = await chatSession.create(wsid);
      router.replace({ name: "chat", params: { sid: fresh.id }, query: { wsid } });
    }
  } catch (exc) {
    ui.toastError("Could not delete", exc);
  }
}

function timeShort(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.valueOf())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pickFromHistory(s: SessionRecord): void {
  historyOpen.value = false;
  historyQuery.value = "";
  switchTo(s.id);
}
</script>

<template>
  <aside
    class="flex h-full w-full min-w-0 flex-col border-l border-border bg-sidebar text-sidebar-foreground"
  >
    <!-- ── DESKTOP HEADER ──────────────────────────────────────────
         Tabs row + quick-action icons, then a thin status row.
         Two rows so we don't crush the model picker against the
         tabs when there are a lot of them. -->
    <template v-if="isDesktopMode">
      <header
        class="flex items-stretch gap-1 border-b border-sidebar-border bg-sidebar/95"
      >
        <!-- Scrollable tab list. `min-w-0 flex-1` lets the row shrink
             below its content size so overflow scrolling kicks in
             instead of pushing the action icons off-screen. -->
        <div
          class="flex min-w-0 flex-1 items-stretch gap-0.5 overflow-x-auto px-1 py-1 [scrollbar-width:thin]"
        >
          <button
            v-for="s in sessions"
            :key="s.id"
            type="button"
            class="group flex min-w-[6.5rem] max-w-[12rem] shrink-0 items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] transition-colors"
            :class="
              s.id === activeSessionId
                ? 'border-primary/50 bg-card text-foreground'
                : 'border-transparent text-muted-foreground hover:border-border hover:bg-card hover:text-foreground'
            "
            :title="s.title || 'Untitled chat'"
            @click="switchTo(s.id)"
          >
            <Icon
              icon="codicon:comment-discussion"
              class="h-3 w-3 shrink-0"
            />
            <span class="truncate">{{ s.title || "Untitled chat" }}</span>
          </button>
          <div
            v-if="!sessions.length"
            class="flex items-center px-2 text-[11px] italic text-muted-foreground"
          >
            no chats yet
          </div>
        </div>

        <!-- Action cluster. Sticky-right via flex-shrink-0; the tab
             list above absorbs all the overflow. -->
        <div class="flex shrink-0 items-center gap-0.5 border-l border-sidebar-border px-1">
          <button
            type="button"
            class="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
            title="New chat in this workspace"
            :disabled="busy || !ws.activeId"
            @click="newChat"
          >
            <Icon icon="codicon:add" class="h-3.5 w-3.5" />
          </button>

          <!-- History popover. We use a controlled v-if + v-on-click-
               outside via a backdrop instead of a real popover lib —
               keeps deps small. -->
          <div class="relative">
            <button
              type="button"
              class="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              title="Chat history"
              @click="historyOpen = !historyOpen; overflowOpen = false"
            >
              <Icon icon="codicon:history" class="h-3.5 w-3.5" />
            </button>
            <Teleport to="body">
              <div
                v-if="historyOpen"
                class="fixed inset-0 z-40"
                @click="historyOpen = false"
              />
            </Teleport>
            <div
              v-if="historyOpen"
              class="absolute right-0 top-full z-50 mt-1 w-72 overflow-hidden rounded-md border border-border bg-card shadow-xl"
              @click.stop
            >
              <div class="flex items-center gap-2 border-b border-border px-2 py-1.5">
                <Icon icon="codicon:search" class="h-3 w-3 text-muted-foreground" />
                <input
                  v-model="historyQuery"
                  type="search"
                  placeholder="Search chats…"
                  class="w-full bg-transparent text-[11px] text-foreground outline-none placeholder:text-muted-foreground"
                />
              </div>
              <div class="max-h-72 overflow-y-auto py-1">
                <button
                  v-for="s in filteredHistory"
                  :key="s.id"
                  type="button"
                  class="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-[11px] hover:bg-muted/60"
                  :class="
                    s.id === activeSessionId
                      ? 'text-foreground bg-muted/40'
                      : 'text-muted-foreground'
                  "
                  @click="pickFromHistory(s)"
                >
                  <span class="truncate">{{ s.title || "Untitled chat" }}</span>
                  <span class="shrink-0 font-mono text-[10px] opacity-60">
                    {{ timeShort(s.last_used) }}
                  </span>
                </button>
                <div
                  v-if="!filteredHistory.length"
                  class="px-2 py-3 text-center text-[11px] text-muted-foreground"
                >
                  No chats match "{{ historyQuery }}"
                </div>
              </div>
            </div>
          </div>

          <!-- Overflow: rename / delete current chat. -->
          <div class="relative">
            <button
              type="button"
              class="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              title="More"
              @click="overflowOpen = !overflowOpen; historyOpen = false"
            >
              <Icon icon="codicon:ellipsis" class="h-3.5 w-3.5" />
            </button>
            <Teleport to="body">
              <div
                v-if="overflowOpen"
                class="fixed inset-0 z-40"
                @click="overflowOpen = false"
              />
            </Teleport>
            <div
              v-if="overflowOpen"
              class="absolute right-0 top-full z-50 mt-1 w-44 overflow-hidden rounded-md border border-border bg-card shadow-xl"
              @click.stop
            >
              <button
                type="button"
                class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-[11px] text-foreground hover:bg-muted/60"
                @click="renameCurrent"
              >
                <Icon icon="codicon:edit" class="h-3 w-3" />
                Rename chat
              </button>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-[11px] text-destructive hover:bg-destructive/10"
                @click="deleteCurrent"
              >
                <Icon icon="codicon:trash" class="h-3 w-3" />
                Delete chat
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- Status / model row. Thin and quiet. The connection dot
           lives here so it doesn't fight the tab text for attention. -->
      <div
        class="flex items-center justify-between gap-2 border-b border-sidebar-border px-3 py-1.5"
      >
        <div class="flex min-w-0 items-center gap-2">
          <span
            class="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
            :class="
              connState === 'open'
                ? 'bg-success'
                : connState === 'error' || connState === 'closed'
                ? 'bg-destructive'
                : 'bg-warning'
            "
            :title="connState"
          />
          <span v-if="isStreaming" class="text-[11px] text-warning">streaming…</span>
        </div>
        <div class="flex items-center gap-2">
          <ModelPicker />
          <ChatSettingsMenu />
        </div>
      </div>
    </template>

    <!-- ── WEB HEADER (original, unchanged) ───────────────────────── -->
    <template v-else>
      <header
        class="flex items-center justify-between gap-2 border-b border-sidebar-border px-3 py-2"
      >
        <div class="flex items-center gap-2 min-w-0">
          <span
            class="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
            :class="
              connState === 'open'
                ? 'bg-success'
                : connState === 'error' || connState === 'closed'
                ? 'bg-destructive'
                : 'bg-warning'
            "
            :title="connState"
          />
          <span class="text-[11px] uppercase tracking-wide text-muted-foreground">chat</span>
          <span v-if="isStreaming" class="text-[11px] text-warning">streaming…</span>
        </div>
        <div class="flex items-center gap-2">
          <ModelPicker />
          <ChatSettingsMenu />
        </div>
      </header>
    </template>

    <MessageList :messages="messages" />

    <Composer />

    <ChatErrorBanner
      v-if="lastError"
      :message="lastError"
      :credit-exhausted="exhausted"
      @dismiss="lastError = null"
    />
  </aside>
</template>
