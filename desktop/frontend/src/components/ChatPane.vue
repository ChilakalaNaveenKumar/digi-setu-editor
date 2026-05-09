<!--
  ChatPane — right column.

  Desktop mode renders a Cursor-style tab strip at the top with every
  chat in the current workspace, plus quick-action icons (+ new,
  🕐 history, ⋯ overflow) — so the user can hop between threads in the
  same folder without leaving the IDE shell. Web mode renders a thinner
  header with just the workspace label.

  Connection state, model picker, permission mode, settings gear, and
  send/stop now ALL live inside the Composer card at the bottom. The
  status row that previously lived between the tabs and the message
  list is gone — it duplicated controls and competed with the composer
  for the user's eye. Credit chip stays in the header so plan + usage
  is visible from the very top of the chat surface.

  Per-turn token/cost stats live inside each assistant bubble.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink, useRouter } from "vue-router";
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
import CreditChip from "./CreditChip.vue";
import MessageList from "./MessageList.vue";
import UpgradeModal from "./UpgradeModal.vue";

const chat = useChatStore();
const billing = useBillingStore();
const chatSession = useChatSessionStore();
const cfg = useConfigStore();
const ws = useWorkspaceStore();
const ui = useUiStore();
const router = useRouter();

const { messages, lastError } = storeToRefs(chat);
const { exhausted, wantsAutoUpgrade, enabled: billingEnabled } = storeToRefs(billing);
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

/**
 * Wired to <ChatErrorBanner @reconnect>. Clears the inline error and
 * asks the chat store to drop the dead WebSocket and re-spawn pi for
 * the active session. Idempotent — chat.reconnect() no-ops when no
 * session is loaded.
 */
async function onReconnect(): Promise<void> {
  chat.lastError = null;
  await chat.reconnect();
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
  if (!sid) return;
  await closeTab(sid, { confirmFirst: true });
}

// Cursor-style per-tab close. Called both by the × button on each
// chat tab and by the overflow "Delete chat" action above (which
// also asks for confirmation). We always navigate the user somewhere
// sensible afterwards so they never end up on a dead chat id.
async function closeTab(
  sid: string,
  opts: { confirmFirst?: boolean } = {},
): Promise<void> {
  const wsid = ws.activeId;
  if (!sid || !wsid) return;
  if (opts.confirmFirst) {
    const ok = await ui.confirm({
      title: "Delete this chat?",
      description: "Files in the workspace are kept.",
      confirmLabel: "Delete",
      cancelLabel: "Cancel",
      variant: "destructive",
    });
    if (!ok) return;
  }
  try {
    const wasActive = sid === activeSessionId.value;
    await chatSession.remove(sid);
    if (!wasActive) return;
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
             instead of pushing the action icons off-screen.
             Scrolling stays on (mouse wheel / horizontal swipe / drag)
             but the bar itself is hidden — Cursor-style. -->
        <div
          class="flex min-w-0 flex-1 items-stretch gap-0.5 overflow-x-auto px-1 py-1 chat-tabs-scroll"
        >
          <div
            v-for="s in sessions"
            :key="s.id"
            class="group relative flex min-w-[6.5rem] max-w-[12rem] shrink-0 items-stretch rounded-md border transition-colors"
            :class="
              s.id === activeSessionId
                ? 'border-primary/50 bg-card text-foreground'
                : 'border-transparent text-muted-foreground hover:border-border hover:bg-card hover:text-foreground'
            "
          >
            <button
              type="button"
              class="flex flex-1 min-w-0 items-center gap-1.5 px-2 py-1 pr-1 text-caption"
              :title="s.title || 'Untitled chat'"
              @click="switchTo(s.id)"
            >
              <Icon
                icon="codicon:comment-discussion"
                class="h-3 w-3 shrink-0"
              />
              <span class="truncate">{{ s.title || "Untitled chat" }}</span>
            </button>
            <!-- Per-tab close (×). Only revealed on hover for inactive
                 tabs to keep the strip visually quiet; always shown on
                 the active tab so it's discoverable. Clicking does NOT
                 trigger the parent's @click="switchTo" because we stop
                 propagation. We don't ask for confirmation here — that's
                 reserved for the overflow "Delete chat" path. The
                 close-the-current-tab case re-routes to the next-most-
                 recent chat (handled inside closeTab). -->
            <button
              type="button"
              class="flex shrink-0 items-center justify-center px-1.5 mr-0.5 my-0.5 rounded text-muted-foreground/70 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-muted hover:text-foreground"
              :class="s.id === activeSessionId ? 'opacity-100' : ''"
              :title="`Close ${s.title || 'Untitled chat'}`"
              :aria-label="`Close ${s.title || 'Untitled chat'}`"
              @click.stop="closeTab(s.id)"
            >
              <Icon icon="codicon:close" class="h-3 w-3" />
            </button>
          </div>
          <div
            v-if="!sessions.length"
            class="flex items-center px-2 text-caption italic text-muted-foreground"
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
                  class="w-full bg-transparent text-caption text-foreground outline-none placeholder:text-muted-foreground"
                />
              </div>
              <div class="max-h-72 overflow-y-auto py-1">
                <button
                  v-for="s in filteredHistory"
                  :key="s.id"
                  type="button"
                  class="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-caption hover:bg-muted/60"
                  :class="
                    s.id === activeSessionId
                      ? 'text-foreground bg-muted/40'
                      : 'text-muted-foreground'
                  "
                  @click="pickFromHistory(s)"
                >
                  <span class="truncate">{{ s.title || "Untitled chat" }}</span>
                  <span class="shrink-0 font-mono text-caption opacity-60">
                    {{ timeShort(s.last_used) }}
                  </span>
                </button>
                <div
                  v-if="!filteredHistory.length"
                  class="px-2 py-3 text-center text-caption text-muted-foreground"
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
                class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-caption text-foreground hover:bg-muted/60"
                @click="renameCurrent"
              >
                <Icon icon="codicon:edit" class="h-3 w-3" />
                Rename chat
              </button>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-caption text-destructive hover:bg-destructive/10"
                @click="deleteCurrent"
              >
                <Icon icon="codicon:trash" class="h-3 w-3" />
                Delete chat
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- Credit chip strip. Connection dot, model picker and settings
           gear moved INTO the Composer card — see Composer.vue. We
           keep credit visible up here so plan + usage reads at a glance
           from the top of the pane without opening the gear menu. -->
      <div
        class="flex items-center justify-end gap-2 border-b border-sidebar-border px-3 py-1.5"
      >
        <CreditChip />
      </div>
    </template>

    <!-- ── WEB HEADER ─────────────────────────────────────────────── -->
    <template v-else>
      <header
        class="flex items-center justify-between gap-2 border-b border-sidebar-border px-3 py-2"
      >
        <span class="text-caption uppercase tracking-wide text-muted-foreground">chat</span>
        <CreditChip />
      </header>
    </template>

    <MessageList :messages="messages" />

    <!-- Setup gate: when the user has neither signed in nor dropped a
         BYOK key (cfg.requires_setup), there's no usable AI backend.
         We render a clear inline banner directly above the composer
         instead of letting the user type into a void and crash the
         WebSocket bridge with a confusing error. The Composer stays
         on screen below — disabled — so the user sees what's about
         to be possible the moment they sign in. -->
    <div
      v-if="cfg.requiresSetup"
      class="border-t border-sidebar-border bg-card/60 px-4 py-3"
    >
      <div class="flex flex-wrap items-center gap-3">
        <Icon
          icon="codicon:account"
          class="h-5 w-5 shrink-0 text-primary"
          aria-hidden="true"
        />
        <p class="min-w-0 flex-1 text-body text-foreground">
          {{ $t("errors.setup_required") }}
        </p>
        <RouterLink
          to="/login"
          class="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-body font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
        >{{ $t("nav.signIn") }}</RouterLink>
        <RouterLink
          to="/login"
          class="text-body text-muted-foreground hover:text-foreground hover:underline"
        >{{ $t("login.byok.title") }}</RouterLink>
      </div>
    </div>

    <Composer />

    <ChatErrorBanner
      v-if="lastError"
      :message="lastError"
      :credit-exhausted="exhausted"
      @dismiss="lastError = null"
      @reconnect="onReconnect"
    />

    <!-- Auto-pop the upgrade modal once when the user first crosses
         into exhausted. The store guards against re-popping after
         dismiss, so closing this returns the user to a normal chat
         surface (with the bottom banner still showing the Upgrade CTA
         in case they change their mind). -->
    <UpgradeModal
      v-if="wantsAutoUpgrade"
      :enabled="billingEnabled"
      @close="billing.dismissAutoUpgrade()"
    />
  </aside>
</template>
