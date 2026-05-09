<!--
  CreditChip — compact "$X.XX of $Y.YY left" indicator for the chat header.

  Polls /api/usage every 30s while the chat tab is visible, and re-polls
  immediately on `_session_info` (a fresh chat probably means a fresh
  page load, so the user expects accurate numbers right away).

  Click → opens the UpgradeModal. When billing is disabled by the
  operator, the chip still shows the current usage but the click is a
  no-op (the modal renders a "billing not configured in this build"
  notice instead).
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { useBillingStore } from "../stores/billing";

const billing = useBillingStore();
const { credit, remainingPct, lowCredit, enabled, exhausted, isAuthoritative, isByok } =
  storeToRefs(billing);

const showUpgrade = ref(false);

// We deliberately do NOT spin up a polling interval here even though the
// chip is one of the most "live"-feeling surfaces in the chat header.
// `ChatSettingsMenu` (the gear icon, always mounted next to us in the
// chat header) already polls `/api/usage` every 30s and writes through
// the shared billing store — adding a second timer here would just
// duplicate the request. We still kick a one-shot fetch on mount so the
// chip has a number on cold load, before the gear's interval ticks.
onMounted(() => {
  void billing.refreshStatus();
  void billing.refreshUsage();
});

const labelLeft = computed(() => {
  const c = credit.value;
  if (!c) return "…";
  if (isByok.value) return "Your key";
  // Don't render the noisy "$0.00 / $0" pair when the cloud reading
  // hasn't arrived yet (offline / signed-out). Show the plan label
  // alone — calmer and accurate.
  const cap = c.plan.monthly_credit_usd ?? 0;
  if (!isAuthoritative.value && cap === 0) return "—";
  if (cap === 0) return `$${c.remaining_usd.toFixed(2)}`;
  return `$${c.remaining_usd.toFixed(2)} of $${cap.toFixed(0)}`;
});

// Three calm states. Red is reserved for actual exhausted-credit on
// an authoritative cloud reading; amber for low-credit (<20%); the
// default uses muted-foreground tones that sit politely in the
// chrome instead of yelling at the user.
const stateClass = computed(() => {
  if (exhausted.value) {
    return "border-rose-500/40 bg-rose-500/5 text-rose-300";
  }
  if (lowCredit.value) {
    return "border-amber-500/40 bg-amber-500/5 text-amber-200";
  }
  return "border-border bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/50";
});

const tooltip = computed(() => {
  const c = credit.value;
  if (!c) return "Usage";
  if (isByok.value) return "Bring-your-own-key — billed by your AI provider";
  if (!isAuthoritative.value) {
    return `${c.plan.label} plan · live usage shown once you sign in`;
  }
  const cap = c.plan.monthly_credit_usd ?? 0;
  if (cap === 0) return `${c.plan.label} plan`;
  return `${c.plan.label} · ${remainingPct.value.toFixed(0)}% of $${cap.toFixed(0)}/mo remaining`;
});

defineExpose({ openUpgrade: () => (showUpgrade.value = true) });
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-caption font-mono transition-colors"
    :class="stateClass"
    :title="tooltip"
    @click="showUpgrade = true"
  >
    <span class="font-semibold tracking-wide opacity-80">{{ credit?.plan?.label || "Free" }}</span>
    <span class="opacity-60">·</span>
    <span class="tabular-nums">{{ labelLeft }}</span>
  </button>

  <!-- modal: lazy-rendered to avoid pulling in the catalogue list when -->
  <!-- the chip is just sitting there idle. -->
  <UpgradeModal v-if="showUpgrade" :enabled="enabled" @close="showUpgrade = false" />
</template>

<script lang="ts">
// Hoist the lazy modal import out of the template — keeps SSR-safe and
// gives Vite a single chunk for it.
import UpgradeModal from "./UpgradeModal.vue";
export default { components: { UpgradeModal } };
</script>
