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
import { i18n } from "../i18n";
import type { CreditSnapshot, PlanInfo } from "../api/types";

import { useUiStore } from "./ui";

// Threshold (in remaining_pct) where we fire the one-shot low-credit
// toast. Below this and the user starts seeing the warning colour on
// the gear icon AND a single nudge toast — Cursor pops a similar toast
// when you cross 20% of your monthly cap. We DON'T want to fire it on
// every poll once they're below the line, so the store guards on the
// crossing event.
const _LOW_CREDIT_PCT_THRESHOLD = 20;
// Once the user climbs back above this (e.g. they upgraded, the month
// rolled over, or their plan was bumped), we re-arm the one-shot so a
// subsequent dip will toast again.
const _LOW_CREDIT_REARM_PCT = 50;

export const useBillingStore = defineStore("billing", () => {
  const enabled = ref(false);
  const plans = ref<PlanInfo[]>([]);
  const credit = ref<CreditSnapshot | null>(null);
  const lastRefresh = ref(0);
  const exhausted = ref(false);

  // ── one-shot UX flags (NOT exposed on the public surface) ──────
  // Whether we've already shown the "you're under 20%" toast for the
  // current low-credit cycle. Resets when remaining climbs back over
  // _LOW_CREDIT_REARM_PCT. Persists across `refreshUsage` calls but
  // not across page reloads — that's intentional: a refresh is a
  // legitimate moment to remind the user.
  const _shownLowCreditToast = ref(false);
  // Whether we've already auto-popped the upgrade modal for the
  // current "exhausted" cycle. Cleared when the user dismisses or
  // when the credit gauge climbs back above 0.
  const _shownAutoUpgrade = ref(false);
  // The reactive flag the chat surface watches to render the modal.
  // Distinct from `exhausted` so the user can dismiss the modal
  // without having to also hide the bottom error banner — the banner
  // stays until the user clicks ✕.
  const wantsAutoUpgrade = ref(false);

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
      _applyCredit(r.credit);
      lastRefresh.value = Date.now();
    } catch (exc) {
      // 401 here means we're on the login page — silent skip.
      if (!String(exc).includes("401")) {
        console.warn("[billing] usage refresh failed", exc);
      }
    }
  }

  /**
   * Apply a new CreditSnapshot — used by both poll-based refresh and
   * server-push paths. Centralised so the one-shot crossing logic
   * (low-credit toast, auto-open upgrade modal) lives in exactly one
   * place and can't drift between callers.
   */
  function _applyCredit(snap: CreditSnapshot): void {
    const prev = credit.value;
    credit.value = snap;

    // Re-arm the one-shot low-credit toast once the user is comfortably
    // above the threshold again (upgrade, month rollover, refund, …).
    if (snap.remaining_pct >= _LOW_CREDIT_REARM_PCT) {
      _shownLowCreditToast.value = false;
    }

    const wasExhausted = !!prev && prev.remaining_usd <= 0;
    const nowExhausted = snap.remaining_usd <= 0;
    exhausted.value = nowExhausted;

    // Re-arm auto-upgrade once the user has any credit again.
    if (!nowExhausted) {
      _shownAutoUpgrade.value = false;
    }

    // Edge transitions ──────────────────────────────────────────────
    // Crossed *down* into low-credit territory. Show one toast, never
    // again until they climb back above _LOW_CREDIT_REARM_PCT.
    if (
      !nowExhausted &&
      snap.remaining_pct <= _LOW_CREDIT_PCT_THRESHOLD &&
      !_shownLowCreditToast.value
    ) {
      _shownLowCreditToast.value = true;
      _emitLowCreditToast(snap);
    }

    // Crossed *into* exhausted. Pop the upgrade modal once.
    if (nowExhausted && !wasExhausted) {
      _maybeAutoOpenUpgrade();
    }
  }

  function _emitLowCreditToast(snap: CreditSnapshot): void {
    try {
      const ui = useUiStore();
      const remaining = `$${snap.remaining_usd.toFixed(2)}`;
      const budget = `$${snap.plan.monthly_credit_usd.toFixed(0)}`;
      const msg = i18n.global.te("billing.lowCreditToast")
        ? (i18n.global.t("billing.lowCreditToast", { remaining, budget }) as string)
        : `Heads up — only ${remaining} of ${budget} left this month.`;
      ui.toast({ message: msg, kind: "info", ttl: 8000 });
    } catch (exc) {
      // Toast firing must never throw past the billing refresh path —
      // an i18n hiccup or pinia init order quirk should NOT break
      // the credit poll. Worst case: no toast, gear icon dot still
      // signals the state.
      console.warn("[billing] low-credit toast failed", exc);
    }
  }

  function _maybeAutoOpenUpgrade(): void {
    if (_shownAutoUpgrade.value) return;
    _shownAutoUpgrade.value = true;
    wantsAutoUpgrade.value = true;
  }

  /**
   * Called by the chat error handler when the backend pushes a
   * `quota_exceeded` _bridge_error. Lets us pop the upgrade modal
   * the moment the user hits the cap, instead of waiting up to 30s
   * for the next /api/usage poll.
   */
  function noteExhausted(snapshot: CreditSnapshot | null = null): void {
    exhausted.value = true;
    if (snapshot) credit.value = snapshot;
    _maybeAutoOpenUpgrade();
  }

  /** Called by the modal's @close — clears the one-shot so we don't
   * immediately re-pop. The user can still click the bottom-banner
   * Upgrade button or the gear icon to reopen on demand. */
  function dismissAutoUpgrade(): void {
    wantsAutoUpgrade.value = false;
  }

  /**
   * Pop the upgrade modal on demand (e.g. user clicked "Upgrade" on
   * the chat error card after hitting a quota / billing error). This
   * resets the one-shot guard so the modal can re-open even if it
   * was previously dismissed in this session.
   */
  function requestUpgrade(): void {
    _shownAutoUpgrade.value = false;
    _maybeAutoOpenUpgrade();
  }

  async function startCheckout(planId: string): Promise<void> {
    const r = await apiStartCheckout(planId);
    window.location.href = r.url;
  }

  async function openPortal(): Promise<void> {
    const r = await apiOpenPortal();
    window.location.href = r.url;
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
    wantsAutoUpgrade,
    planLabel,
    remainingPct,
    lowCredit,
    refreshStatus,
    refreshUsage,
    noteExhausted,
    dismissAutoUpgrade,
    requestUpgrade,
    startCheckout,
    openPortal,
  };
});
