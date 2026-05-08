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
import PermissionPrompt from "../components/PermissionPrompt.vue";
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
    if (!ws.workspaces.length) await ws.refresh();
    for (const w of ws.workspaces) {
      try {
        const r = await fetch(`/api/workspaces/${encodeURIComponent(w.id)}/sessions`);
        if (!r.ok) continue;
        const data = (await r.json()) as { sessions: Array<{ id: string }> };
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
    router.replace({ name: "picker" });
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

onBeforeUnmount(() => {
  chat.disconnect();
});

function backToPicker(): void {
  chat.disconnect();
  router.push({ name: "picker" });
}
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background text-foreground">
    <!-- Compact brand header: small logo + back-to-sessions button on
         the leading slot, current workspace name centred (md+ only),
         pricing/privacy/terms + account avatar trailing. -->
    <BrandHeader
      variant="compact"
      :links="[
        { to: '/activity', label: 'Activity' },
        { to: '/pricing', label: 'Pricing' },
        { to: '/privacy', label: 'Privacy' },
        { to: '/terms', label: 'Terms' },
      ]"
      :home-link="false"
    >
      <template #leading>
        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          title="Back to sessions"
          @click="backToPicker"
        >
          <Icon icon="codicon:arrow-left" class="h-3.5 w-3.5" />
          <span class="hidden sm:inline">Sessions</span>
        </button>
      </template>
      <!-- Centre: current chat title. We deliberately show the *session*
           title here (the LLM-generated or heuristic title) rather than
           the workspace id, so the user always knows which thread they
           are in. The title updates live when the background titler
           lands a polished version (see chat.ts → applyTitleUpdate). -->
      <div class="flex min-w-0 items-center justify-center gap-2 text-sm text-foreground">
        <Icon icon="codicon:comment-discussion" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span class="truncate font-medium">
          {{ activeSession?.title || "Untitled chat" }}
        </span>
      </div>
    </BrandHeader>

    <AppShell />

    <div
      v-if="connState === 'closed' || connState === 'error'"
      class="border-t border-destructive/40 bg-destructive/10 px-3 py-1 text-center text-[11px] text-destructive"
    >
      Connection {{ connState }} — bridge is down or pi crashed.
    </div>

    <!-- Per-tool-call approval gate. Renders nothing when there are no
         pending requests; <Teleport> moves the overlay to <body> so it
         escapes any z-index traps inside AppShell. -->
    <PermissionPrompt />
  </div>
</template>
