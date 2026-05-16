<!--
  Workspace — active chat session. URL: /chat/:sid?wsid=...

  Resolves the parent workspace from the query string (set by the picker
  on navigation). Bookmarking the URL works because the chat WS handler
  resolves the workspace from the session id; we only need wsid in the
  URL so the UI's REST calls (file tree, snapshots) know where to point
  before the WS handshake completes.
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import AppShell from "../components/AppShell.vue";
import BrandHeader from "../components/BrandHeader.vue";
import { listSessions } from "../api/sessions";
import { useChatStore } from "../stores/chat";
import { useChatSessionStore } from "../stores/chat-session";
import { useWorkspaceStore } from "../stores/workspace";

const props = defineProps<{ sid: string }>();
const route = useRoute();
const router = useRouter();
const chat = useChatStore();
const chatSession = useChatSessionStore();
const ws = useWorkspaceStore();

const { connState } = storeToRefs(chat);
const { active: activeSession } = storeToRefs(chatSession);

async function open(): Promise<void> {
  const wsidQ = route.query.wsid;
  let wsid = typeof wsidQ === "string" ? wsidQ : null;

  if (!wsid) {
    // Bookmark: resolve wsid from the session record by listing workspaces
    // and asking each one for its sessions until we find a match. Cheap
    // for typical N (handful of workspaces, dozens of sessions).
    //
    // Use `listSessions()` (api/sessions.ts) instead of bare `fetch()` so
    // the API base prefix is applied — desktop runs the SPA at
    // tauri://localhost and a relative `/api/...` URL would resolve
    // against that origin and 404 instead of hitting the loopback
    // FastAPI sidecar.
    if (!ws.workspaces.length) await ws.refresh();
    for (const w of ws.workspaces) {
      try {
        const data = await listSessions(w.id);
        if (data.sessions.some((s) => s.id === props.sid)) {
          wsid = w.id;
          break;
        }
      } catch {
        /* try next */
      }
    }
    if (wsid) {
      router.replace({ name: "chat", params: { sid: props.sid }, query: { wsid } });
    }
  }

  if (!wsid) {
    router.replace({ name: "sessions" });
    return;
  }

  // Make sure the chat-session store has this workspace's sessions
  // loaded so the brand header can show the session title (and so
  // background `_session_titled` events from chat.ts have a record to
  // patch). On a fresh page load the picker hasn't run, so this is a
  // first-time fetch; if the picker did run, this is a quick re-list.
  chatSession.setActive(props.sid);
  if (!chatSession.sessions.some((s) => s.id === props.sid)) {
    await chatSession.refresh(wsid);
  }

  await chat.connect(props.sid, wsid);
}

onMounted(open);
watch(() => props.sid, open);

/**
 * Wired to the bottom-bar Reconnect button. Drops the dead bridge
 * and re-spawns pi for the active session. No-op if the chat store
 * has no active session (e.g. user clicked Reconnect on a stale tab).
 */
async function onReconnect(): Promise<void> {
  chat.clearError();
  await chat.reconnect();
}

onBeforeUnmount(() => {
  chat.disconnect();
});
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background text-foreground">
    <!-- Compact brand header for the IDE shell. The back-to-sessions
         affordance lives in the file-tree sidebar (FileTreePane) where
         it sits directly above the session ID — that's the more
         contextual location. We deliberately do NOT add a second back
         button to this top bar.

         The global brand header (mounted in App.vue) is hidden on this
         route — see App.vue's `showHeader` computed — because the IDE
         shell needs a purpose-built top bar with the chat title in the
         centre slot. We render the same `<BrandHeader>` component here
         in `compact` variant so the visible chrome (logo + nav + account)
         stays consistent with every other page. -->
    <BrandHeader variant="compact">
      <!-- Centre: current chat title. The title updates live when the
           background titler lands a polished version (see chat.ts →
           applyTitleUpdate). -->
      <div class="flex min-w-0 items-center justify-center gap-2 text-lead text-foreground">
        <Icon icon="codicon:comment-discussion" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span class="truncate font-medium">
          {{ activeSession?.title || $t("workspace.untitledChat") }}
        </span>
      </div>
    </BrandHeader>

    <AppShell />

    <!-- Bottom-of-Workspace connection bar. Old version surfaced
         "Something's not working. Please try again." with no recovery
         affordance — users had no idea what to do. New version pairs
         the message with an icon + a one-click "Reconnect" button so
         they can recover without having to navigate away. The chat
         pane already shows a more detailed `ChatErrorBanner` for the
         specific WS error code; this thinner row is the persistent
         indicator that lives outside the chat scroll area. -->
    <div
      v-if="connState === 'closed' || connState === 'error'"
      class="flex items-center justify-center gap-2 border-t border-destructive/40 bg-destructive/10 px-3 py-1 text-caption text-destructive"
    >
      <Icon
        :icon="connState === 'error' ? 'codicon:debug-disconnect' : 'codicon:circle-slash'"
        class="h-3.5 w-3.5 shrink-0"
      />
      <span>
        {{ connState === "closed" ? $t("workspace.connectionClosed") : $t("workspace.connectionError") }}
      </span>
      <button
        type="button"
        class="ml-1 rounded border border-destructive/40 bg-destructive/20 px-2 py-0.5 text-caption font-semibold text-destructive hover:bg-destructive/30"
        @click="onReconnect"
      >
        {{ $t("chat.error.action.reconnect") }}
      </button>
    </div>

    <!-- Per-tool-call approval banner is now mounted INSIDE ChatPane
         (between header and message list) so it anchors visually at
         the top of the chat column where the user's eye actually is.
         The old bottom-right overlay went unnoticed on long turns. -->
  </div>
</template>
