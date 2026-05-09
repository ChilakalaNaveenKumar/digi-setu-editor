<!--
  ChatPane — right column. Simple header (status dot + model picker +
  settings gear) → MessageList → Composer.

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
import CreditChip from "./CreditChip.vue";
import MessageList from "./MessageList.vue";
import ModelPicker from "./ModelPicker.vue";
import UpgradeModal from "./UpgradeModal.vue";

const chat = useChatStore();
const billing = useBillingStore();

const { messages, isStreaming, connState, lastError } = storeToRefs(chat);
// `exhausted` drives the red bottom-banner Upgrade CTA.
// `wantsAutoUpgrade` is a one-shot the billing store flips when the
// user first crosses into exhausted state — we render the modal here
// so the user gets recovery UX *immediately* instead of having to
// click the button on the banner. See stores/billing._maybeAutoOpenUpgrade.
const { exhausted, wantsAutoUpgrade, enabled: billingEnabled } = storeToRefs(billing);
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
        <span class="text-caption uppercase tracking-wide text-muted-foreground">chat</span>
        <span v-if="isStreaming" class="text-caption text-warning">streaming…</span>
      </div>
      <div class="flex items-center gap-2">
        <CreditChip />
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
