<!--
  ChatPane — right column. Chat header (model + token totals), MessageList,
  and Composer pinned to the bottom.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useSessionStore } from "../stores/session";
import { formatCost, formatTokens } from "../lib/format";
import Composer from "./Composer.vue";
import MessageList from "./MessageList.vue";

const store = useSessionStore();
const { messages, totals, isStreaming, connState, lastError } = storeToRefs(store);

const PROVIDER = "anthropic-vertex";
const MODEL = "claude-opus-4-7";
</script>

<template>
  <aside
    class="flex h-full w-full min-w-0 flex-col border-l border-border bg-sidebar text-sidebar-foreground"
  >
    <header class="flex items-center justify-between border-b border-sidebar-border px-3 py-2">
      <div class="flex items-center gap-2">
        <span
          class="inline-block h-1.5 w-1.5 rounded-full"
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
      </div>
      <div class="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
        <span :title="`${PROVIDER} · ${MODEL}`">{{ MODEL }}</span>
        <span v-if="isStreaming" class="text-warning">streaming…</span>
      </div>
    </header>

    <MessageList :messages="messages" />

    <footer class="border-t border-sidebar-border bg-sidebar px-3 py-1 text-[10px] font-mono text-muted-foreground flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span title="input tokens">↑ {{ formatTokens(totals.input) }}</span>
        <span title="output tokens">↓ {{ formatTokens(totals.output) }}</span>
        <span title="cache read">R {{ formatTokens(totals.cacheRead) }}</span>
        <span title="cache write">W {{ formatTokens(totals.cacheWrite) }}</span>
      </div>
      <span :title="`${PROVIDER} · ${MODEL}`">{{ formatCost(totals.cost) }}</span>
    </footer>

    <Composer />

    <div
      v-if="lastError"
      class="border-t border-destructive/30 bg-destructive/10 px-3 py-1 text-[11px] text-destructive"
    >
      {{ lastError }}
    </div>
  </aside>
</template>
