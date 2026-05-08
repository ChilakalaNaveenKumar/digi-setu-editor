<!--
  Desktop /workspaces/:wsid landing — kept around so bookmarks and
  legacy in-app links keep working, but no longer renders a "pick a
  chat" UI. The desktop UX is: opening a folder = a ready chat.

  Flow:
    1. Load workspace registry (wsid must exist; if not, bounce home).
    2. List chats in this workspace.
    3. If any exist, redirect to the most-recent one.
       Else, auto-create a fresh chat and redirect to it.
    4. While the network calls are inflight, render a tiny spinner so
       the brief flash isn't a black screen.
-->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import { useChatSessionStore } from "../stores/chat-session";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

const props = defineProps<{ wsid: string }>();
const router = useRouter();
const ui = useUiStore();
const ws = useWorkspaceStore();
const sess = useChatSessionStore();

const error = ref<string | null>(null);

async function resolve(): Promise<void> {
  try {
    if (!ws.workspaces.length) await ws.refresh();
    const found = ws.workspaces.find((w) => w.id === props.wsid);
    if (!found) {
      router.replace({ name: "picker" });
      return;
    }

    await sess.refresh(props.wsid);
    const recent = sess.sessions[0];
    const target = recent ?? (await sess.create(props.wsid));
    router.replace({
      name: "chat",
      params: { sid: target.id },
      query: { wsid: props.wsid },
    });
  } catch (exc) {
    const msg = exc instanceof Error ? exc.message : String(exc);
    error.value = msg;
    ui.toastError("Could not open workspace", exc);
  }
}

onMounted(resolve);
</script>

<template>
  <div class="flex h-full w-full items-center justify-center bg-background text-foreground">
    <div v-if="!error" class="flex items-center gap-2 text-sm text-muted-foreground">
      <Icon icon="codicon:loading" class="h-4 w-4 animate-spin" />
      Opening workspace…
    </div>
    <div v-else class="max-w-sm rounded-md border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
      <div class="font-medium">Could not open workspace</div>
      <div class="mt-1 text-xs opacity-80">{{ error }}</div>
      <button
        type="button"
        class="mt-3 rounded-md border border-border bg-card px-3 py-1 text-xs text-foreground hover:border-primary/40"
        @click="router.replace({ name: 'picker' })"
      >
        Back to home
      </button>
    </div>
  </div>
</template>
