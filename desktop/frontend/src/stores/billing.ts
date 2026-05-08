/**
 * Billing + credit state.
 *
 * The credit chip in the chat header polls `/api/usage` so the user
 * sees their tank drain in near real time. The Upgrade flow redirects
 * out to Stripe Checkout (we never collect cards in our own UI).
 *
 * `enabled=false` means the operator hasn't set STRIPE_SECRET_KEY —
 * the SPA hides upgrade buttons in that case rather than showing a
 * broken redirect.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

import {
  getBillingStatus,
  getUsage,
  openPortal as apiOpenPortal,
  startCheckout as apiStartCheckout,
} from "../api/billing";
import { isDesktop, openExternal } from "../lib/native-bridge";
import type { CreditSnapshot, PlanInfo } from "../api/types";

/**
 * In desktop mode Stripe Checkout / Customer Portal must open in the
 * system browser (3DS, Apple Pay, autofill all break inside Tauri's
 * webview). The deep-link bridge in main.ts listens for the matching
 * pi-typst-test://billing/return URL the user hits after success or
 * cancel, refreshes credit state, and surfaces a confirmation toast.
 *
 * The web build keeps the existing `window.location.href` redirect:
 * it's same-origin, the URL is whitelisted by Stripe, and the
 * post-payment cookie reattaches automatically.
 */
const DESKTOP_BILLING_RETURN = "pi-typst-test://billing/return";

export const useBillingStore = defineStore("billing", () => {
  const enabled = ref(false);
  const plans = ref<PlanInfo[]>([]);
  const credit = ref<CreditSnapshot | null>(null);
  const lastRefresh = ref(0);
  const exhausted = ref(false);

  async function refreshStatus(): Promise<void> {
    try {
      const s = await getBillingStatus();
      enabled.value = s.enabled;
      plans.value = s.plans;
    } catch (exc) {
      console.warn("[billing] status refresh failed", exc);
    }
  }

  async function refreshUsage(): Promise<void> {
    try {
      const r = await getUsage();
      credit.value = r.credit;
      lastRefresh.value = Date.now();
      exhausted.value = r.credit.remaining_usd <= 0;
    } catch (exc) {
      // 401 here means we're on the login page — silent skip.
      if (!String(exc).includes("401")) {
        console.warn("[billing] usage refresh failed", exc);
      }
    }
  }

  /**
   * Note a server-pushed credit_exhausted error from chat_ws so the
   * UI can pop the upgrade modal without waiting for the next poll.
   */
  function noteExhausted(snapshot: CreditSnapshot | null = null): void {
    exhausted.value = true;
    if (snapshot) credit.value = snapshot;
  }

  async function startCheckout(planId: string): Promise<void> {
    const desktop = isDesktop();
    const r = await apiStartCheckout(
      planId,
      desktop ? DESKTOP_BILLING_RETURN : undefined,
    );
    if (desktop) {
      await openExternal(r.url);
    } else {
      window.location.href = r.url;
    }
  }

  async function openPortal(): Promise<void> {
    const desktop = isDesktop();
    const r = await apiOpenPortal(
      desktop ? DESKTOP_BILLING_RETURN : undefined,
    );
    if (desktop) {
      await openExternal(r.url);
    } else {
      window.location.href = r.url;
    }
  }

  const planLabel = computed(() => credit.value?.plan?.label ?? "Free");
  const remainingPct = computed(() => credit.value?.remaining_pct ?? 100);
  const lowCredit = computed(
    () => credit.value !== null && credit.value.remaining_pct <= 20,
  );

  return {
    enabled,
    plans,
    credit,
    exhausted,
    planLabel,
    remainingPct,
    lowCredit,
    refreshStatus,
    refreshUsage,
    noteExhausted,
    startCheckout,
    openPortal,
  };
});
