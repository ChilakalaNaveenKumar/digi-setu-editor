<!--
  Pricing — public plans page.

  Shares the underlying billing data with the in-chat UpgradeModal but
  is a stand-alone, bookmarkable route. Linked from the brand header
  on every page and from the credit chip's "see all plans" footer.

  Auth posture: signed-out users CAN view the pricing tiers (so the
  URL is shareable in marketing copy). Upgrade buttons require sign-
  in — we surface a "Sign in to upgrade" CTA in that case rather than
  a broken POST /api/billing/checkout.

  Layout:
    1. Hero (title + tagline)
    2. Plan cards row (Free / Pro / Enterprise / Custom)
    3. "What's included" feature matrix
    4. Trust strip (Stripe + cancel anytime + cards never seen)
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import BrandHeader from "../components/BrandHeader.vue";
import { useBillingStore } from "../stores/billing";
import { useConfigStore } from "../stores/config";

const router = useRouter();
const cfg = useConfigStore();
const billing = useBillingStore();
const { plans, credit, enabled } = storeToRefs(billing);

const busy = ref<string | null>(null);
const signedIn = ref<boolean | null>(null);

onMounted(async () => {
  if (!plans.value.length) await billing.refreshStatus();
  if (cfg.authRequired) {
    try {
      const { getToken } = await import("@clerk/vue");
      const t = await getToken();
      signedIn.value = !!t;
      if (signedIn.value) await billing.refreshUsage();
    } catch {
      signedIn.value = false;
    }
  } else {
    signedIn.value = true;
    await billing.refreshUsage();
  }
});

const currentPlanId = computed(() => credit.value?.plan?.id ?? "free");
const hasCustomer = computed(() => !!credit.value?.stripe_customer_id);

async function onUpgrade(planId: string): Promise<void> {
  if (planId === "free" || planId === currentPlanId.value) return;
  if (!signedIn.value) {
    router.push({ name: "login", query: { next: "/pricing" } });
    return;
  }
  busy.value = planId;
  try {
    await billing.startCheckout(planId);
  } catch (exc) {
    console.warn("[pricing] checkout failed", exc);
    busy.value = null;
  }
}

async function onManage(): Promise<void> {
  busy.value = "portal";
  try {
    await billing.openPortal();
  } catch (exc) {
    console.warn("[pricing] portal failed", exc);
    busy.value = null;
  }
}

function fmtUsd(v: number): string {
  return v % 1 === 0 ? `$${v}` : `$${v.toFixed(2)}`;
}

function ctaLabel(planId: string): string {
  if (planId === currentPlanId.value) return "Current plan";
  if (planId === "free") return "Default";
  if (signedIn.value === false) return "Sign in to upgrade";
  if (busy.value === planId) return "Loading…";
  return "Upgrade";
}

// Highlight a "popular" plan visually. Pulled by id rather than
// hard-coded so the same template handles plan changes server-side.
const POPULAR_PLAN_ID = "pro";

// What each plan includes — a single source of truth for the feature
// bullets shown under each card. Keeps the template lean.
function bullets(planId: string): string[] {
  switch (planId) {
    case "free":
      return [
        "1 sandboxed workspace",
        "Latest open-source models",
        "Community feedback page",
      ];
    case "pro":
      return [
        "Unlimited workspaces",
        "Claude + Gemini at real cost",
        "Faster sandbox spin-up",
        "Priority email support",
      ];
    case "enterprise":
      return [
        "Everything in Pro",
        "SSO / domain claim",
        "Custom egress firewall rules",
        "Dedicated success channel",
      ];
    default:
      return ["Tailored — talk to us"];
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <BrandHeader
      :links="[
        { to: '/privacy', label: 'Privacy' },
        { to: '/terms', label: 'Terms' },
      ]"
    />

    <main class="mx-auto w-full max-w-6xl flex-1 px-6 py-12 md:py-16">
      <!-- HERO -->
      <header class="mx-auto max-w-2xl text-center">
        <h1 class="text-h1 font-semibold tracking-tight md:text-h1">
          Plans &amp; pricing
        </h1>
        <p class="mt-3 text-lead leading-relaxed text-muted-foreground md:text-lead">
          Pay once a month for credit. We pass the actual model + infra cost
          through — no per-token surprises, no hidden margin. Cancel any
          time, no contracts.
        </p>
        <p
          v-if="enabled === false"
          class="mx-auto mt-4 inline-block rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-body text-warning-foreground"
        >
          <Icon icon="codicon:warning" class="mr-1 inline h-3.5 w-3.5 align-text-bottom" />
          Paid plans aren't enabled in this build —
          <code class="font-mono">STRIPE_SECRET_KEY</code> isn't configured yet.
        </p>
      </header>

      <!-- PLAN CARDS -->
      <section class="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        <article
          v-for="p in plans"
          :key="p.id"
          class="relative flex flex-col rounded-2xl border p-6 transition-shadow"
          :class="[
            p.id === POPULAR_PLAN_ID
              ? 'border-primary/60 bg-card shadow-lg shadow-primary/10'
              : 'border-border bg-card',
            p.id === currentPlanId && p.id !== POPULAR_PLAN_ID
              ? 'ring-2 ring-primary/40'
              : '',
          ]"
        >
          <!-- Popular badge -->
          <div
            v-if="p.id === POPULAR_PLAN_ID"
            class="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-caption font-semibold uppercase tracking-wider text-primary-foreground shadow"
          >
            Most popular
          </div>
          <div
            v-else-if="p.id === currentPlanId"
            class="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full border border-primary/40 bg-card px-3 py-0.5 text-caption font-semibold uppercase tracking-wider text-primary"
          >
            Your plan
          </div>

          <header>
            <h3 class="text-h2 font-semibold">{{ p.label }}</h3>
            <div class="mt-2 flex items-baseline gap-1">
              <span class="text-h1 font-bold tracking-tight">
                {{ fmtUsd(p.monthly_price_usd) }}
              </span>
              <span class="text-lead text-muted-foreground">/ month</span>
            </div>
            <p class="mt-2 text-body leading-snug text-muted-foreground">
              {{ p.description }}
            </p>
          </header>

          <div class="my-5 h-px bg-border" />

          <ul class="space-y-2 text-lead text-foreground/90">
            <li class="flex items-start gap-2">
              <Icon icon="codicon:check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
              <span class="leading-snug">
                <strong class="font-mono">{{ fmtUsd(p.monthly_credit_usd) }}</strong>
                of model + infra credit / month
              </span>
            </li>
            <li
              v-for="b in bullets(p.id)"
              :key="b"
              class="flex items-start gap-2"
            >
              <Icon icon="codicon:check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
              <span class="leading-snug">{{ b }}</span>
            </li>
          </ul>

          <div class="mt-6">
            <button
              type="button"
              class="w-full rounded-md px-3 py-2 text-lead font-semibold transition-colors"
              :class="
                p.id === currentPlanId || p.id === 'free'
                  ? 'border border-border text-muted-foreground cursor-not-allowed'
                  : p.id === POPULAR_PLAN_ID
                    ? 'bg-primary text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60'
                    : 'border border-primary/60 bg-primary/10 text-primary hover:bg-primary/20 disabled:cursor-not-allowed disabled:opacity-60'
              "
              :disabled="
                p.id === currentPlanId || p.id === 'free' || busy !== null || enabled === false
              "
              @click="onUpgrade(p.id)"
            >
              {{ ctaLabel(p.id) }}
            </button>
          </div>
        </article>
      </section>

      <!-- TRUST STRIP -->
      <footer class="mt-12 flex flex-col items-center justify-between gap-3 rounded-lg border border-border bg-card/60 px-5 py-4 text-body text-muted-foreground sm:flex-row">
        <div class="flex flex-wrap items-center justify-center gap-4 sm:justify-start">
          <span class="flex items-center gap-1.5">
            <Icon icon="codicon:shield" class="h-3.5 w-3.5" />
            Stripe-secured checkout
          </span>
          <span class="flex items-center gap-1.5">
            <Icon icon="codicon:eye-closed" class="h-3.5 w-3.5" />
            We never see your card
          </span>
          <span class="flex items-center gap-1.5">
            <Icon icon="codicon:close-all" class="h-3.5 w-3.5" />
            Cancel any time
          </span>
        </div>
        <button
          v-if="enabled && hasCustomer"
          type="button"
          class="rounded border border-border bg-background px-2.5 py-1 text-body hover:bg-muted disabled:opacity-50"
          :disabled="busy !== null"
          @click="onManage"
        >
          Manage subscription
        </button>
      </footer>
    </main>

    <footer class="border-t border-border bg-card/40 px-6 py-4 text-center text-caption text-muted-foreground">
      © {{ new Date().getFullYear() }} Digi Setu
    </footer>
  </div>
</template>
