<!--
  ChatErrorBanner — bottom strip used for inline rate-limit / credit /
  generic chat errors. Renders a one-line dismissible notice; when the
  error is `credit_exhausted` it adds an Upgrade CTA that opens the
  pricing modal so the user can recover in one click.
-->
<script setup lang="ts">
import { ref } from "vue";

import UpgradeModal from "./UpgradeModal.vue";
import { useBillingStore } from "../stores/billing";

defineProps<{ message: string; creditExhausted: boolean }>();
const emit = defineEmits<{ dismiss: [] }>();

const billing = useBillingStore();
const showUpgrade = ref(false);
</script>

<template>
  <div
    class="flex items-start justify-between gap-2 border-t border-destructive/30 bg-destructive/10 px-3 py-1.5 text-caption text-destructive"
  >
    <span class="flex-1 leading-snug">{{ message }}</span>
    <div class="flex shrink-0 items-center gap-2">
      <button
        v-if="creditExhausted"
        type="button"
        class="rounded bg-destructive px-2 py-0.5 text-caption font-semibold uppercase tracking-wide text-destructive-foreground hover:bg-destructive/90"
        @click="showUpgrade = true"
      >
        Upgrade
      </button>
      <button
        type="button"
        class="rounded px-1 text-body hover:bg-destructive/20"
        aria-label="dismiss"
        @click="emit('dismiss')"
      >
        ✕
      </button>
    </div>
    <UpgradeModal v-if="showUpgrade" :enabled="billing.enabled" @close="showUpgrade = false" />
  </div>
</template>
