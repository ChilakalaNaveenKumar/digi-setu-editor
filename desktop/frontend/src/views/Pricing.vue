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

import AppFooter from "../components/AppFooter.vue";
import { useBillingStore } from "../stores/billing";
import { useConfigStore } from "../stores/config";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const cfg = useConfigStore();
const auth = useAuthStore();
const billing = useBillingStore();
const { plans, credit } = storeToRefs(billing);

const busy = ref<string | null>(null);
// Sign-in state comes from the desktop auth store (which polls
// /api/auth/whoami at boot). No @clerk/vue dependency here.
const signedIn = computed<boolean>(() =>
  cfg.authRequired ? auth.signedIn : true,
);

onMounted(async () => {
  if (!plans.value.length) await billing.refreshStatus();
  if (signedIn.value) await billing.refreshUsage();
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
    // Opens https://digi-setu.com/pricing?plan=… in the system
    // browser. Stripe Checkout runs there inside the user's
    // Clerk-authenticated browser session — the desktop app never
    // touches a card.
    await billing.startCheckout(planId);
    busy.value = null;
  } catch (exc) {
    console.warn("[pricing] checkout failed", exc);
    busy.value = null;
  }
}

async function onManage(): Promise<void> {
  busy.value = "portal";
  try {
    // Opens https://digi-setu.com/account/billing in the system
    // browser. Stripe Customer Portal runs there.
    await billing.openPortal();
    busy.value = null;
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
  if (busy.value === planId) return "Opening browser…";
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
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="mx-auto w-full max-w-6xl flex-1 px-6 py-10 md:py-14">
      <!-- HERO -->
      <header class="mx-auto max-w-2xl text-center">
        <h1
          class="font-semibold tracking-tight text-foreground"
          style="font-size: clamp(28px, 4vw, 36px); line-height: 1.15;"
        >
          Pricing that follows the meter
        </h1>
        <p class="mt-4 text-lead leading-relaxed text-muted-foreground">
          Pay once a month for credit. We pass the actual model + infra cost
          through — no per-token surprises, no hidden margin.
          <span class="text-foreground/85">Cancel any time</span>, no contracts.
        </p>
        <p
          class="mx-auto mt-5 inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-caption text-muted-foreground"
        >
          <Icon icon="codicon:link-external" class="h-3 w-3" />
          Upgrade &amp; cancel open
          <code class="font-mono text-foreground/85">digi-setu.com</code>
          in your browser.
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
                p.id === currentPlanId || p.id === 'free' || busy !== null
              "
              @click="onUpgrade(p.id)"
            >
              {{ ctaLabel(p.id) }}
            </button>
            <p
              v-if="p.id !== 'free'"
              class="mt-2 text-center text-caption text-muted-foreground"
            >
              Cancel any time — you keep access until the period ends.
            </p>
          </div>
        </article>
      </section>

      <!-- TRUST STRIP + ACCOUNT ACTIONS
           Cancel + Manage are surfaced as separate buttons here so a
           user looking specifically for "cancel" doesn't have to guess
           that the cancel flow is buried inside Stripe's "manage"
           portal. Both bounce to the same Stripe Customer Portal in
           the system browser. -->
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
            Cancel any time — keep access until period end
          </span>
        </div>
        <div v-if="hasCustomer" class="flex items-center gap-2">
          <button
            type="button"
            class="rounded-md border border-border bg-background px-3 py-1.5 text-body text-foreground hover:bg-muted disabled:opacity-50"
            :disabled="busy !== null"
            @click="onManage"
          >
            {{ busy === "portal" ? "Opening browser…" : "Manage subscription" }}
          </button>
          <button
            type="button"
            class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-1.5 text-body font-medium text-destructive hover:bg-destructive/20 disabled:opacity-50"
            :disabled="busy !== null"
            title="Opens the Stripe customer portal in your browser. You can cancel and keep access until the current period ends."
            @click="onManage"
          >
            Cancel plan
          </button>
        </div>
      </footer>
    </main>

    <AppFooter />
  </div>
</template>
