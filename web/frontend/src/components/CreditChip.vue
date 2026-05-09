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
const { credit, remainingPct, lowCredit, enabled } = storeToRefs(billing);

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
  if (!c) return "loading…";
  return `$${c.remaining_usd.toFixed(2)} / $${c.plan.monthly_credit_usd.toFixed(0)}`;
});

const stateClass = computed(() => {
  if (!credit.value) return "border-border";
  if (credit.value.remaining_usd <= 0) return "border-destructive bg-destructive/10 text-destructive";
  if (lowCredit.value) return "border-warning bg-warning/10 text-warning";
  return "border-border";
});

defineExpose({ openUpgrade: () => (showUpgrade.value = true) });
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-caption font-mono"
    :class="stateClass"
    :title="
      credit
        ? `${credit.plan.label} — ${remainingPct.toFixed(0)}% remaining of $${credit.plan.monthly_credit_usd.toFixed(0)}/mo`
        : 'usage'
    "
    @click="showUpgrade = true"
  >
    <span class="opacity-60">{{ credit?.plan?.label || "Free" }}</span>
    <span>{{ labelLeft }}</span>
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
