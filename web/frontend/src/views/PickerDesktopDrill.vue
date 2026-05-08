<!--
  Desktop drill-in view: one workspace's chat sessions.
  URL: /workspaces/:wsid
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";

import { useChatSessionStore } from "../stores/chat-session";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import type { SessionRecord } from "../api/types";

const props = defineProps<{ wsid: string }>();
const router = useRouter();
const ui = useUiStore();
const ws = useWorkspaceStore();
const sess = useChatSessionStore();

const { sessions } = storeToRefs(sess);

const busy = ref(false);
const workspace = computed(() => ws.workspaces.find((w) => w.id === props.wsid) ?? null);

async function load(): Promise<void> {
  if (!ws.workspaces.length) await ws.refresh();
  if (!workspace.value) {
    router.replace({ name: "picker" });
    return;
  }
  await sess.refresh(props.wsid);
}

onMounted(load);
watch(() => props.wsid, load);

async function startNewSession(): Promise<void> {
  busy.value = true;
  try {
    const s = await sess.create(props.wsid);
    router.push({ name: "chat", params: { sid: s.id }, query: { wsid: props.wsid } });
  } catch (exc) {
    ui.toastError("Could not create chat", exc);
  } finally {
    busy.value = false;
  }
}

function open(s: SessionRecord): void {
  router.push({ name: "chat", params: { sid: s.id }, query: { wsid: props.wsid } });
}

async function rename(s: SessionRecord): Promise<void> {
  const next = window.prompt("Rename chat:", s.title || "Untitled chat");
  if (!next) return;
  try {
    await sess.rename(s.id, next);
  } catch (exc) {
    ui.toastError("Could not rename", exc);
  }
}

async function remove(s: SessionRecord): Promise<void> {
  const ok = await ui.confirm({
    title: "Delete this chat?",
    description: "Files in the workspace are kept.",
    confirmLabel: "Delete",
    cancelLabel: "Cancel",
    variant: "destructive",
  });
  if (!ok) return;
  try {
    await sess.remove(s.id);
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
</script>

<template>
  <div class="flex h-full w-full items-center justify-center bg-background p-6 text-foreground">
    <div class="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-lg">
      <button
        type="button"
        class="mb-3 text-xs text-muted-foreground hover:text-foreground"
        @click="router.push({ name: 'picker' })"
      >
        ← All workspaces
      </button>

      <div v-if="workspace" class="mb-5">
        <div class="text-[11px] uppercase tracking-wide text-muted-foreground">Workspace</div>
        <div class="mt-0.5 truncate text-base font-semibold">{{ workspace.name }}</div>
        <div class="truncate font-mono text-[11px] text-muted-foreground">{{ workspace.path }}</div>
      </div>

      <button
        type="button"
        class="w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60"
        :disabled="busy"
        @click="startNewSession"
      >
        + New chat in this workspace
      </button>

      <div v-if="sessions.length" class="mt-5 space-y-1">
        <div class="text-[11px] uppercase tracking-wide text-muted-foreground">Chats</div>
        <div
          v-for="s in sessions"
          :key="s.id"
          class="group flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 hover:border-ring"
        >
          <button type="button" class="flex-1 text-left text-xs text-foreground" @click="open(s)">
            <div class="truncate">{{ s.title || "Untitled chat" }}</div>
            <div class="text-[10px] text-muted-foreground">{{ timeShort(s.last_used) }}</div>
          </button>
          <button
            type="button"
            class="rounded p-1 text-muted-foreground opacity-0 hover:text-foreground group-hover:opacity-100"
            title="Rename"
            @click="rename(s)"
          >
            ✎
          </button>
          <button
            type="button"
            class="rounded p-1 text-destructive opacity-0 hover:bg-destructive/10 group-hover:opacity-100"
            title="Delete chat"
            @click="remove(s)"
          >
            ×
          </button>
        </div>
      </div>
      <div v-else class="mt-3 text-center text-xs text-muted-foreground">
        No chats in this workspace yet.
      </div>
    </div>
  </div>
</template>
