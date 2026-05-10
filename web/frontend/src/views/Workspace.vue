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

onBeforeUnmount(() => {
  chat.disconnect();
});

</script>

<template>
  <!--
    Layout — full-viewport IDE shell.

    Outer  : `h-full` chains from App.vue's middle div (which is the
             flex-grow child of the `h-screen` root on the chat route);
             gives this view a definite 100vh height to lay out
             children against.
    Header : intrinsic height (~40px).
    AppShell wrapper: `flex-1 min-h-0` is the canonical "give me the
             remaining height" pattern. Without it, AppShell's inner
             `h-full` resolves against the ENTIRE 100vh (not the
             post-header remainder), so the splitpanes overflow by
             the header's height and either get clipped or, depending
             on the parent flex layout, collapse to less than full
             height — which is exactly what produced the giant black
             void below the chat panes the user reported.
    Conn banner / PermissionPrompt: intrinsic height after the panes.
  -->
  <div class="flex h-full w-full flex-col bg-background text-foreground">
    <!-- Compact brand header for the IDE shell. Same global BrandHeader
         used everywhere else (the FIXED nav set keeps the user oriented
         no matter what view they're in), shrunk via variant=compact and
         given a centre slot with the chat title. The back-to-sessions
         affordance lives in the file-tree sidebar (FileTreePane), where
         it sits directly above the session ID — that's the more
         contextual location. We deliberately do NOT add a second back
         button to this top bar. -->
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

    <div class="flex min-h-0 w-full flex-1 flex-col">
      <AppShell />
    </div>

    <div
      v-if="connState === 'closed' || connState === 'error'"
      class="border-t border-destructive/40 bg-destructive/10 px-3 py-1 text-center text-caption text-destructive"
    >
      {{ connState === "closed" ? $t("workspace.connectionClosed") : $t("workspace.connectionError") }}
    </div>

    <!-- Per-tool-call approval gate. Renders nothing when there are no
         pending requests; <Teleport> moves the overlay to <body> so it
         escapes any z-index traps inside AppShell. -->
    <PermissionPrompt />
  </div>
</template>
