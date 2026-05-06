<!--
  App — top-level. Two states:
    1. picker  → centered card; pick or create a session
    2. session → AppShell (3-column IDE layout)
  No global header bar. Connection state lives in ChatPane's header.
-->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import AppShell from "./components/AppShell.vue";
import { useSessionStore } from "./stores/session";

const store = useSessionStore();
const { savedSessions, session, connState } = storeToRefs(store);

const showPicker = ref(true);

onMounted(async () => {
  await store.refreshSavedSessions();
});

async function startNew(): Promise<void> {
  try {
    const id = await store.newSessionId();
    store.connect(id);
    showPicker.value = false;
  } catch (exc) {
    console.error(exc);
  }
}

function resume(id: string): void {
  store.connect(id);
  showPicker.value = false;
}
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background text-foreground">
    <!-- Picker -->
    <div
      v-if="showPicker"
      class="flex flex-1 items-center justify-center p-6"
    >
      <div class="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg">
        <div class="mb-5 text-center">
          <h1 class="text-lg font-semibold text-foreground">pi · web</h1>
          <p class="mt-1 text-sm text-muted-foreground">
            Pick or start a session.
          </p>
        </div>

        <button
          type="button"
          class="w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
          @click="startNew"
        >
          + New session
        </button>

        <div v-if="savedSessions.length" class="mt-5 space-y-1">
          <div class="text-[11px] uppercase tracking-wide text-muted-foreground">
            Saved sessions
          </div>
          <button
            v-for="s in savedSessions"
            :key="s.id"
            type="button"
            class="w-full rounded-md border border-border bg-background px-3 py-2 text-left text-xs text-foreground hover:border-ring transition-colors"
            @click="resume(s.id)"
          >
            <div class="font-mono">{{ s.id }}</div>
            <div class="text-[10px] text-muted-foreground">{{ s.modified }}</div>
          </button>
        </div>
        <div v-else class="mt-3 text-center text-xs text-muted-foreground">
          No saved sessions yet.
        </div>
      </div>
    </div>

    <!-- Active session -->
    <AppShell v-else />

    <!-- Tiny error banner (only when WS unhealthy) -->
    <div
      v-if="!showPicker && (connState === 'closed' || connState === 'error')"
      class="border-t border-destructive/40 bg-destructive/10 px-3 py-1 text-center text-[11px] text-destructive"
    >
      Connection {{ connState }} — bridge is down or pi crashed.
    </div>
  </div>
</template>
