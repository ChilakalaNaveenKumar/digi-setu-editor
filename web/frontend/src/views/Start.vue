<!--
  Start — auto-router after sign-in.

  Why this exists:
    Previously Clerk's hosted sign-in returned the user to "/" (Home),
    which signed-in users mostly used as a stepping stone — one click
    to "/sessions", another to pick a chat. Three full page transitions
    just to arrive at the chat surface where they actually wanted to
    type. This view collapses all of that into a single auto-resolved
    redirect so the user lands directly inside a chat the moment Clerk
    hands them back.

  Resolution rules:
    1. Refresh workspaces + their sessions.
    2. If any session exists → router.replace to the most-recently-used
       one (`/chat/<sid>?wsid=<wsid>`). This matches what the user
       almost always wants — pick up where they left off.
    3. If they have ZERO sessions (brand-new account) → mint a
       workspace + session via createWebPair() and route there. They
       land in an empty chat ready to type.
    4. On any failure → fall back to /sessions so they at least see the
       picker (manual recovery surface) instead of getting stuck on a
       spinner.

  We use router.replace (not push) throughout so the redirect doesn't
  create a back-button trap that would bounce the user right back here.

  Auth-off / dev mode: same flow works — the synthetic `dev` user has
  workspaces too. We don't gate on Clerk here; the global router guard
  already enforces auth before this view mounts.
-->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import { useChatSessionStore } from "../stores/chat-session";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

const router = useRouter();
const ws = useWorkspaceStore();
const sess = useChatSessionStore();
const ui = useUiStore();

const status = ref<"resolving" | "creating" | "error">("resolving");
const errMsg = ref<string>("");

async function _findMostRecentSession(): Promise<
  { sid: string; wsid: string } | null
> {
  await ws.refresh();
  let best: { sid: string; wsid: string; ts: string } | null = null;
  for (const w of ws.workspaces) {
    await sess.refresh(w.id);
    for (const s of sess.sessions) {
      const ts = s.last_used || "";
      if (!best || ts.localeCompare(best.ts) > 0) {
        best = { sid: s.id, wsid: w.id, ts };
      }
    }
  }
  return best ? { sid: best.sid, wsid: best.wsid } : null;
}

async function resolve(): Promise<void> {
  try {
    const recent = await _findMostRecentSession();
    if (recent) {
      await router.replace({
        name: "chat",
        params: { sid: recent.sid },
        query: { wsid: recent.wsid },
      });
      return;
    }
    // Brand-new account / wiped storage — mint a chat for them so
    // they don't have to make a "click New chat" decision before
    // typing anything.
    status.value = "creating";
    const { workspace, session } = await sess.createWebPair();
    await router.replace({
      name: "chat",
      params: { sid: session.id },
      query: { wsid: workspace.id },
    });
  } catch (exc) {
    console.error("[start] auto-resolve failed", exc);
    errMsg.value = exc instanceof Error ? exc.message : String(exc);
    status.value = "error";
    ui.toastError("Couldn't open your last chat", exc);
    // Fall back to the picker after a short pause so the user has
    // something interactive to look at instead of a frozen spinner.
    setTimeout(() => {
      void router.replace({ name: "sessions" });
    }, 1200);
  }
}

onMounted(resolve);
</script>

<template>
  <div class="flex min-h-0 w-full flex-1 items-center justify-center bg-background px-6 py-12 text-foreground">
    <div class="flex max-w-md flex-col items-center gap-3 text-center">
      <span
        v-if="status !== 'error'"
        class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"
        aria-hidden="true"
      />
      <Icon
        v-else
        icon="codicon:warning"
        class="h-6 w-6 text-destructive"
        aria-hidden="true"
      />

      <p class="text-lead text-foreground">
        <template v-if="status === 'resolving'">
          Opening your last chat…
        </template>
        <template v-else-if="status === 'creating'">
          Setting up your first sandbox…
        </template>
        <template v-else>
          Couldn't open your chats automatically.
        </template>
      </p>

      <p
        v-if="status === 'error'"
        class="font-mono text-caption text-muted-foreground"
      >
        {{ errMsg }}
      </p>
      <p
        v-if="status === 'error'"
        class="text-body text-muted-foreground"
      >
        Taking you to your workspace list…
      </p>
    </div>
  </div>
</template>
