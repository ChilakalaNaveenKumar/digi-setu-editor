<!--
  ChatPane — right column. Chat header (model picker + settings menu),
  MessageList, then Composer pinned to the bottom.

  Per-turn token/cost stats live inside each assistant bubble; the user's
  plan-level usage lives in ChatSettingsMenu (gear icon). We deliberately
  no longer render a session-total ticker here — it conflated raw model
  cost with billed usage and read as alarming.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useBillingStore } from "../stores/billing";
import { useChatStore } from "../stores/chat";
import ChatErrorBanner from "./ChatErrorBanner.vue";
import Composer from "./Composer.vue";
import ChatSettingsMenu from "./ChatSettingsMenu.vue";
import MessageList from "./MessageList.vue";
import ModelPicker from "./ModelPicker.vue";

const chat = useChatStore();
const billing = useBillingStore();

const { messages, isStreaming, connState, lastError } = storeToRefs(chat);
const { exhausted } = storeToRefs(billing);
</script>

<template>
  <aside
    class="flex h-full w-full min-w-0 flex-col border-l border-border bg-sidebar text-sidebar-foreground"
  >
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
