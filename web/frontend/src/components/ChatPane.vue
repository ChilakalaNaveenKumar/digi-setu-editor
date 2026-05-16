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
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";

import { useBillingStore } from "../stores/billing";
import { useChatStore } from "../stores/chat";
import { useSubagentPanelStore } from "../stores/subagent-panel";
import CompactionPill from "./CompactionPill.vue";
import Composer from "./Composer.vue";
import MessageList from "./MessageList.vue";
import PermissionPrompt from "./PermissionPrompt.vue";
import SessionDisconnectedCard from "./SessionDisconnectedCard.vue";
import SubagentLivePanel from "./SubagentLivePanel.vue";
import UpgradeModal from "./UpgradeModal.vue";

const chat = useChatStore();
const billing = useBillingStore();
const router = useRouter();
const subagentPanel = useSubagentPanelStore();
const { openCallId: subagentOpenCallId } = storeToRefs(subagentPanel);

const {
  messages,
  lastErrorCode,
  isReconnecting,
  isInitialConnecting,
} = storeToRefs(chat);
// Single source of truth for "do we render the error overlay" — any
// state-level error code (set via chat._setError) gets the full-card
// treatment now. The previous design routed only `session_kicked` and
// `too_many_chats` here and dropped everything else into a bottom
// strip; users complained the strip was easy to miss and looked
// like "another toolbar". One consistent surface = no ambiguity.
//
// We also intentionally suppress the card while the bridge is mid-
// reconnect on a transient code: the chat store quarantines those for
// 3 s before promoting them, so that a network blip that the bridge
// auto-recovers in 1 s never flashes a giant error card. While in
// that grace window we render only the small "Reconnecting…" pill
// below — see `isReconnecting`.
const errorCard = computed<string | null>(() => lastErrorCode.value || null);

// `exhausted` drives the inline Upgrade CTA in messages. `wantsAutoUpgrade`
// is a one-shot the billing store flips when the user first crosses
// into exhausted state — we render the modal here so the user gets
// recovery UX *immediately*. See stores/billing._maybeAutoOpenUpgrade.
const { wantsAutoUpgrade, enabled: billingEnabled } = storeToRefs(billing);

function onSignIn(): void {
  chat.clearError();
  void router.push({ name: "login" });
}

function onUpgrade(): void {
  chat.clearError();
  // Open the upgrade modal via the billing store flag the existing
  // <UpgradeModal v-if="wantsAutoUpgrade"> block already listens to.
  billing.requestUpgrade();
}

function onReload(): void {
  window.location.reload();
}

async function onReconnect(): Promise<void> {
  chat.clearError();
  await chat.reconnect();
}
</script>

<template>
  <aside
    class="relative flex h-full w-full min-w-0 flex-col border-l border-border bg-sidebar text-sidebar-foreground"
  >
    <header
      class="flex items-center justify-between gap-2 border-b border-sidebar-border px-3 py-2"
    >
      <span class="text-caption uppercase tracking-wide text-muted-foreground">chat</span>
      <!--
        Credit chip removed from the chat header. The visible amount
        used to live here AND in the settings popover; keeping both
        meant CreditChip's onMounted fetched /api/usage on every
        ChatPane mount, plus the popover polled it every 30 s. Now
        the only credit surface is inside ChatSettingsMenu, fetched
        on click. Zero polling, zero idle network — see the comment
        on `watch(open, …)` in ChatSettingsMenu.vue.
      -->
    </header>

    <!--
      Initial-connect skeleton. Replaces the empty MessageList with a
      centred spinner so the very first WS handshake (after login or
      session switch) doesn't read as a stuck/blank surface for the
      300-1500 ms it takes to open the socket and replay history.
    -->
    <div
      v-if="isInitialConnecting"
      class="flex flex-1 flex-col items-center justify-center gap-3 text-sm text-muted-foreground"
    >
      <span
        class="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-transparent"
        aria-hidden="true"
      />
      <span>Connecting…</span>
    </div>
    <!--
      MessageList vs SubagentLivePanel are mutually exclusive in this
      flex slot. When the user clicks a SubagentToolCard the panel
      store flips `openCallId`, we hide MessageList, and SubagentLivePanel
      renders the live transcript using the SAME width/height the chat
      uses (instead of the previous 560 px right-side drawer that
      truncated wider tool cards on big screens). PermissionPrompt /
      CompactionPill / Composer keep working below because they're
      sibling flex children, not covered by an overlay anymore.
    -->
    <MessageList
      v-if="!isInitialConnecting && !subagentOpenCallId"
      :messages="messages"
    />
    <SubagentLivePanel v-else-if="!isInitialConnecting && subagentOpenCallId" />

    <!--
      Reconnecting pill — slim, non-modal indicator that we noticed a
      WS hiccup and are actively retrying. Sits above the composer so
      it doesn't push the message column around, and disappears the
      moment the bridge reaches "open" again. No flicker because the
      pill is a soft transition, not a giant red card.
    -->
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isReconnecting && !errorCard"
        class="flex items-center justify-center gap-2 border-t border-sidebar-border/60 bg-sidebar/80 px-3 py-1.5 text-xs text-muted-foreground"
        role="status"
        aria-live="polite"
      >
        <span
          class="h-3 w-3 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-transparent"
          aria-hidden="true"
        />
        <span>Reconnecting…</span>
      </div>
    </Transition>

    <CompactionPill />

    <!-- Pending-permission banner. Renders nothing when the queue is
         empty. Anchored just above the Composer because that's where
         the user's eye lives while a turn is in flight (watching for
         the next thing to type / for the agent to finish). Earlier
         iterations parked this at the top of the chat column; users
         routinely missed the prompt because their gaze had already
         moved to the composer. See PermissionPrompt.vue header comment. -->
    <PermissionPrompt />

    <Composer />

    <SessionDisconnectedCard
      v-if="errorCard"
      :code="errorCard"
      @dismiss="chat.clearError()"
      @reconnect="onReconnect"
      @sign-in="onSignIn"
      @upgrade="onUpgrade"
      @reload="onReload"
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

    <!--
      SubagentLivePanel was previously rendered here as an absolutely-
      positioned right-side drawer. It now slots into the MessageList
      position above (mutually exclusive with MessageList), so the
      transcript inherits the chat column's responsive width instead of
      being clamped to 560 px. See the v-if/v-else-if pair near
      PermissionPrompt above and the comment block in SubagentLivePanel.vue.
    -->
  </aside>
</template>
