<!--
  ChatPane — right column. Thin header (chat label + credit chip) →
  MessageList → Composer.

  Connection state, model picker, permission mode, settings gear, and
  send/stop now ALL live inside the Composer card at the bottom (see
  Composer.vue). The status row that previously lived between the
  header and the message list is gone — it duplicated controls and
  competed with the composer for the user's eye. Credit chip stays in
  the header so plan + usage is visible from the very top of the chat
  surface.

  Per-turn token/cost stats live inside each assistant bubble. We
  deliberately don't render a session-total ticker here — it conflated
  raw model cost with billed usage and read as alarming.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";

import { useBillingStore } from "../stores/billing";
import { useChatStore } from "../stores/chat";
import ChatErrorBanner from "./ChatErrorBanner.vue";
import Composer from "./Composer.vue";
import CreditChip from "./CreditChip.vue";
import MessageList from "./MessageList.vue";
import UpgradeModal from "./UpgradeModal.vue";

const chat = useChatStore();
const billing = useBillingStore();

const { messages, lastError } = storeToRefs(chat);
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
      <span class="text-caption uppercase tracking-wide text-muted-foreground">chat</span>
      <CreditChip />
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
