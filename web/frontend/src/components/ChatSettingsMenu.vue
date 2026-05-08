<!--
  ChatSettingsMenu — single gear-icon button in the chat header that
  consolidates per-chat settings + status into one popover. Replaces
  the previous always-on `[ permission ] [ model ] [ credit ]` row
  which crammed three chips + an emoji into the header and overflowed
  on narrow widths.

  What lives here:
    - Permission mode picker (auto / approve_risky / approve_all)
    - Plan + credit usage with progress bar + Upgrade button
    - Quick links to /pricing and "Open billing portal"

  What does NOT live here: the model picker. Model is changed often
  (per prompt) so it stays as a first-class control next to the gear.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { Icon } from "@iconify/vue";

import { useBillingStore } from "../stores/billing";

import PermissionModePicker from "./PermissionModePicker.vue";
import UpgradeModal from "./UpgradeModal.vue";

const billing = useBillingStore();
const { credit, remainingPct, lowCredit, enabled } = storeToRefs(billing);

const open = ref(false);
const showUpgrade = ref(false);
const root = ref<HTMLDivElement | null>(null);

let pollHandle: number | null = null;

onMounted(() => {
  void billing.refreshStatus();
  void billing.refreshUsage();
  // 30 s is enough — usage rarely changes outside an active turn,
  // and message_end already nudges the ledger live.
  pollHandle = window.setInterval(() => void billing.refreshUsage(), 30_000);
  document.addEventListener("click", onDocClick);
});

onUnmounted(() => {
  if (pollHandle !== null) window.clearInterval(pollHandle);
  document.removeEventListener("click", onDocClick);
});

function onDocClick(e: MouseEvent): void {
  if (!root.value) return;
  if (!root.value.contains(e.target as Node)) open.value = false;
}

const usageLabel = computed(() => {
  const c = credit.value;
  if (!c) return "loading…";
  return `$${c.remaining_usd.toFixed(2)} of $${c.plan.monthly_credit_usd.toFixed(0)}`;
});

const usageBarWidth = computed(() => {
  const pct = Math.max(0, Math.min(100, 100 - remainingPct.value));
  return `${pct}%`;
});

const usageBarColor = computed(() => {
  if (!credit.value) return "bg-muted";
  if (credit.value.remaining_usd <= 0) return "bg-destructive";
  if (lowCredit.value) return "bg-warning";
  return "bg-primary";
});

const planLabel = computed(() => credit.value?.plan?.label || "Free");

// Subtle red dot on the gear when credit is below the warning threshold,
// so users notice without us having to keep the chip in the header.
const showAlert = computed(
  () => !!credit.value && (credit.value.remaining_usd <= 0 || lowCredit.value),
);

function close(): void {
  open.value = false;
}

function openUpgrade(): void {
  close();
  showUpgrade.value = true;
}
</script>

<template>
  <div ref="root" class="relative inline-flex items-center">
    <button
      type="button"
      class="relative flex h-6 w-6 items-center justify-center rounded border border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
      :class="open ? 'text-foreground' : ''"
      :title="`Chat settings · ${planLabel} ${usageLabel}`"
      @click="open = !open"
    >
      <Icon icon="codicon:settings-gear" class="h-[14px] w-[14px]" />
      <span
        v-if="showAlert"
        class="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full"
        :class="credit && credit.remaining_usd <= 0 ? 'bg-destructive' : 'bg-warning'"
        aria-hidden="true"
      />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-full z-30 mt-1 w-80 rounded border border-border bg-popover shadow-lg"
    >
      <!-- Permission mode -->
      <div class="border-b border-border px-3 py-2.5">
        <div class="mb-1.5 flex items-baseline justify-between">
          <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            permissions
          </span>
        </div>
        <PermissionModePicker />
        <p class="mt-1.5 text-[10px] leading-tight text-muted-foreground">
          Controls when pi asks before running tools. Audit trail is
          always recorded.
        </p>
      </div>

      <!-- Credit / plan -->
      <div class="border-b border-border px-3 py-2.5">
        <div class="mb-1.5 flex items-baseline justify-between">
          <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            credit · {{ planLabel.toLowerCase() }}
          </span>
          <span
            class="font-mono text-[10px]"
            :class="
              credit && credit.remaining_usd <= 0
                ? 'text-destructive'
                : lowCredit
                ? 'text-warning'
                : 'text-muted-foreground'
            "
          >
            {{ usageLabel }}
          </span>
        </div>
        <!-- thin progress bar so the gauge doesn't shout when it's 90%
             empty but still draws the eye when it's almost full. -->
        <div class="h-1 overflow-hidden rounded-full bg-muted">
          <div
            class="h-full transition-[width] duration-300"
            :class="usageBarColor"
            :style="{ width: usageBarWidth }"
          />
        </div>
        <div class="mt-2 flex items-center gap-2">
          <button
            type="button"
            class="flex-1 rounded border border-border bg-background px-2 py-1 font-mono text-[11px] hover:bg-muted"
            @click="openUpgrade"
          >
            Upgrade
          </button>
          <RouterLink
            to="/pricing"
            class="flex-1 rounded border border-border bg-background px-2 py-1 text-center font-mono text-[11px] text-foreground hover:bg-muted"
            @click="close"
          >
            See plans
          </RouterLink>
        </div>
      </div>

      <!-- Footer hint -->
      <div class="px-3 py-2 text-[10px] leading-tight text-muted-foreground">
        Settings live next to the model picker so you don't lose visual
        space in the chat. Open this menu any time to change permission
        or check usage.
      </div>
    </div>
  </div>

  <UpgradeModal v-if="showUpgrade" :enabled="enabled" @close="showUpgrade = false" />
</template>
