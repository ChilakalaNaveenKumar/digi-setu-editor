<!--
  UpgradeModal — pricing table + Upgrade buttons.

  Pulls plans from the billing store (which mirrors backend /api/billing/status).
  Clicking Upgrade redirects out to Stripe Checkout. The current plan is
  shown with a "Manage" button that opens the Stripe Customer Portal.

  When the operator hasn't configured Stripe (`enabled=false`) we render
  the catalogue read-only with a banner explaining that paid plans aren't
  available in this build — better than a broken Upgrade button.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useBillingStore } from "../stores/billing";

const props = defineProps<{ enabled: boolean }>();
const emit = defineEmits<{ close: [] }>();

const billing = useBillingStore();
const { plans, credit } = storeToRefs(billing);

const busy = ref<string | null>(null);

const currentPlanId = computed(() => credit.value?.plan?.id ?? "free");
const hasCustomer = computed(() => !!credit.value?.stripe_customer_id);

async function onUpgrade(planId: string): Promise<void> {
  if (!props.enabled || planId === "free" || planId === currentPlanId.value) return;
  busy.value = planId;
  try {
    await billing.startCheckout(planId);
  } catch (exc) {
    console.warn("[upgrade] checkout failed", exc);
    busy.value = null;
  }
}

async function onManage(): Promise<void> {
  busy.value = "portal";
  try {
    await billing.openPortal();
  } catch (exc) {
    console.warn("[upgrade] portal failed", exc);
    busy.value = null;
  }
}

function fmtUsd(v: number): string {
  return v % 1 === 0 ? `$${v}` : `$${v.toFixed(2)}`;
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-3xl rounded-lg border border-border bg-background shadow-xl">
      <header class="flex items-center justify-between border-b border-border px-5 py-3">
        <h2 class="text-lead font-semibold">Plans</h2>
        <button
          type="button"
          class="rounded px-2 py-1 text-lead text-muted-foreground hover:bg-muted"
          aria-label="close"
          @click="emit('close')"
        >
          ✕
        </button>
      </header>

      <div v-if="!enabled" class="border-b border-warning bg-warning/10 px-5 py-3 text-lead">
        Paid plans aren't enabled in this build — the operator hasn't configured
        <code>STRIPE_SECRET_KEY</code> yet. Free tier is fully functional; bookmark this page
        and come back when the upgrade button lights up.
      </div>

      <div class="grid gap-3 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="p in plans"
          :key="p.id"
          class="flex flex-col rounded border p-3 text-lead"
          :class="
            p.id === currentPlanId
              ? 'border-primary bg-primary/5'
              : 'border-border bg-card'
          "
        >
          <div class="flex items-baseline justify-between">
            <h3 class="font-semibold">{{ p.label }}</h3>
            <span class="font-mono text-body text-muted-foreground"
              >{{ fmtUsd(p.monthly_price_usd) }}/mo</span
            >
          </div>
          <p class="mt-1 text-caption leading-snug text-muted-foreground">
            {{ p.description }}
          </p>
          <p class="mt-2 font-mono text-caption">
            {{ fmtUsd(p.monthly_credit_usd) }} of credit / month
          </p>

          <div class="mt-auto pt-3">
            <button
              v-if="p.id === currentPlanId"
              type="button"
              class="w-full rounded border border-border px-2 py-1 text-body"
              disabled
            >
              Current plan
            </button>
            <button
              v-else-if="p.id === 'free'"
              type="button"
              class="w-full rounded border border-border px-2 py-1 text-body text-muted-foreground"
              disabled
            >
              Default
            </button>
            <button
              v-else
              type="button"
              class="w-full rounded bg-primary px-2 py-1 text-body font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="!enabled || busy !== null"
              @click="onUpgrade(p.id)"
            >
              {{ busy === p.id ? "Loading…" : "Upgrade" }}
            </button>
          </div>
        </div>
      </div>

      <footer
        class="flex items-center justify-between border-t border-border px-5 py-3 text-body text-muted-foreground"
      >
        <div>
          <span v-if="enabled">Card details handled by Stripe — we never see them.</span>
          <span v-else>Plans visible for reference; checkout disabled.</span>
        </div>
        <button
          v-if="enabled && hasCustomer"
          type="button"
          class="rounded border border-border px-2 py-1 text-body hover:bg-muted disabled:opacity-50"
          :disabled="busy !== null"
          @click="onManage"
        >
          Manage subscription
        </button>
      </footer>
    </div>
  </div>
</template>
