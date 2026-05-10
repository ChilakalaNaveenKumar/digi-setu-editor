<!--
  BrandHeader — single global top bar mounted in App.vue.

  One header, one place to maintain it. The visible link set is FIXED;
  individual views no longer inject their own `:links`. That kept every
  page silently rebuilding its own header and meant the user saw a
  different nav on every screen.

  Variants (driven by route.meta.header in App.vue):
    full     → tall hero header (default for marketing + picker pages).
    compact  → short bar suitable for the workspace IDE: same controls,
               smaller padding, and a centre slot for the chat title.

  Account dropdown: the desktop fork uses a teleported popover + custom
  z-index scale to avoid a collision with the model picker tooltip in
  its IDE shell. The web fork has no such overlap (the chat surface is
  a single column with the composer pinned to the bottom), so we lean
  on Clerk's stock <UserButton> for the avatar / open-account-portal /
  sign-out cluster and add a dedicated "Cancel plan" button alongside
  it for users on a paid plan. That button only shows when the user
  actually has a Stripe customer record AND a non-free plan — anything
  else would link them to a portal that 404s.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { Icon } from "@iconify/vue";
// `@clerk/vue` v2.2.0 doesn't ship the React-style <SignedIn>/<SignedOut>
// wrapper components — it ships a single <Show :when="'signed-in'">
// (or "signed-out") with the same semantics. We use it below to gate
// the Sign-in CTA vs. the UserButton avatar.
import { Show as ClerkShow, UserButton } from "@clerk/vue";

import { useConfigStore } from "../stores/config";
import { useBillingStore } from "../stores/billing";

interface NavLink {
  to: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    /** Visual density. */
    variant?: "full" | "compact";
    /** When true, render the Feedback button. Hidden on Login. */
    showFeedback?: boolean;
    /** When true, render the account avatar / sign-in CTA. */
    showAccount?: boolean;
  }>(),
  {
    variant: "full",
    showFeedback: true,
    showAccount: true,
  },
);

// FIXED nav set used on every page. Activity + Pricing route to local
// SPA pages (the web fork ships them; the desktop fork bounces them
// to {CLOUD}/pricing instead). Privacy / Terms move to the footer to
// keep the top bar focused on actions.
//
// Download stays in the top-bar (not just the footer) because it's
// the highest-intent action for first-time visitors landing on
// digi-setu.com — the whole product is the desktop app, and we'd
// rather one extra header item than a hidden conversion path.
const NAV: NavLink[] = [
  { to: "/", label: "Home" },
  { to: "/sessions", label: "Workspaces" },
  { to: "/pricing", label: "Pricing" },
  { to: "/activity", label: "Activity" },
  { to: "/download", label: "Download" },
];

const cfg = useConfigStore();
const billing = useBillingStore();

const hasCustomer = computed(() => !!billing.credit?.stripe_customer_id);
const isPaidPlan = computed(() => {
  const id = billing.credit?.plan?.id ?? "free";
  return id !== "free";
});
// Cancel plan CTA — only useful when there's actually something to
// cancel (paid plan AND a Stripe customer record exists). Otherwise
// the portal call would 404.
const showCancelPlan = computed(() => hasCustomer.value && isPaidPlan.value);

async function onCancelPlan(): Promise<void> {
  // openPortal navigates the current tab to the Stripe Customer
  // Portal — from there the user can hit "Cancel plan" and keep
  // access until the period ends. We don't have a "cancel directly"
  // API endpoint because Stripe owns that flow.
  await billing.openPortal();
}

const isCompact = computed(() => props.variant === "compact");

// ── Mobile drawer ────────────────────────────────────────────────────
//
// The default top bar lays out NAV + Feedback + Account inline. On
// screens narrower than the Tailwind `md` breakpoint (~768px) the
// inline strip overflows or wraps under the wordmark. On a real phone
// (320–428px) it's visually broken.
//
// We solve that by rendering all the NAV items inside a slide-down
// drawer that opens from a hamburger button when `<md`. The drawer
// auto-closes on route change (so picking "Home" doesn't leave the
// drawer hanging open) and on Escape.
//
// On `>=md` the drawer is hidden entirely and the inline nav strip
// stays exactly as before — this is purely additive markup.
const mobileOpen = ref(false);
const route = useRoute();
function toggleMobile(): void {
  mobileOpen.value = !mobileOpen.value;
}
function closeMobile(): void {
  mobileOpen.value = false;
}
watch(() => route.fullPath, closeMobile);

function onKeydown(ev: KeyboardEvent): void {
  if (ev.key === "Escape" && mobileOpen.value) closeMobile();
}
if (typeof window !== "undefined") {
  window.addEventListener("keydown", onKeydown);
  onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
}
const padding = computed(() =>
  isCompact.value ? "px-4 py-2" : "px-6 py-3 md:px-8 md:py-3.5",
);
const logoHeight = computed(() => (isCompact.value ? "h-6" : "h-7"));
const wordmarkClass = computed(() =>
  isCompact.value
    ? "text-h2 font-semibold tracking-tight text-foreground"
    : "text-h2 font-semibold tracking-tight text-foreground",
);
</script>

<template>
  <header
    class="sticky top-0 z-30 flex items-center gap-4 border-b border-border bg-background"
    :class="padding"
  >
    <!-- Optional leading slot (workspace uses for back button). -->
    <slot name="leading" />

    <!-- Brand: icon + "Digi Setu" wordmark. Always links to /. -->
    <RouterLink
      to="/"
      class="flex shrink-0 items-center gap-2 transition-opacity hover:opacity-80"
      :aria-label="$t('brand.homeAria')"
    >
      <img
        src="/digi-setu-logo.svg"
        alt=""
        aria-hidden="true"
        class="w-auto select-none"
        :class="logoHeight"
        draggable="false"
      />
      <span :class="wordmarkClass">{{ $t("brand.name") }}</span>
    </RouterLink>

    <!-- Centre slot — workspace uses it for the chat title. Hidden on
         small screens so the header never wraps. -->
    <div class="hidden min-w-0 flex-1 md:block">
      <slot />
    </div>
    <div v-if="!$slots.default" class="hidden flex-1 md:block" />

    <!-- Inline trailing nav — only visible on >=md screens. On smaller
         screens the same items live inside the mobile drawer below. -->
    <nav class="hidden items-center gap-1 text-body md:flex">
      <RouterLink
        v-for="link in NAV"
        :key="link.to"
        :to="link.to"
        class="rounded-md px-2.5 py-1.5 text-body-lg font-medium text-foreground/75 transition-colors hover:bg-muted hover:text-foreground"
        active-class="text-foreground bg-muted"
      >{{ link.label }}</RouterLink>

      <RouterLink
        v-if="showFeedback"
        to="/feedback"
        class="ml-1 rounded-md border border-border bg-card px-3 py-1.5 text-body-lg font-medium text-foreground transition-colors hover:border-primary/50"
      >{{ $t("nav.feedback") }}</RouterLink>

      <!-- Account surface. Same gating logic as before. -->
      <template v-if="showAccount && cfg.authRequired">
        <ClerkShow :when="'signed-out'">
          <RouterLink
            to="/login"
            class="ml-2 inline-flex items-center rounded-md bg-primary px-3.5 py-1.5 text-body-lg font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          >{{ $t("nav.signIn") }}</RouterLink>
        </ClerkShow>
        <ClerkShow :when="'signed-in'">
          <button
            v-if="showCancelPlan"
            type="button"
            class="ml-2 rounded-md border border-border bg-card px-2.5 py-1 text-body font-medium text-muted-foreground transition-colors hover:border-destructive/50 hover:text-destructive"
            title="Opens the Stripe customer portal. You can cancel and keep access until the current period ends."
            @click="onCancelPlan"
          >Cancel plan</button>
          <UserButton :after-sign-out-url="'/login'" class="ml-2" />
        </ClerkShow>
      </template>
    </nav>

    <!-- Mobile cluster — hamburger + (when signed in) avatar so the
         user can still open their account without first opening the
         drawer. Hidden on >=md. -->
    <div class="ml-auto flex items-center gap-2 md:hidden">
      <template v-if="showAccount && cfg.authRequired">
        <ClerkShow :when="'signed-in'">
          <UserButton :after-sign-out-url="'/login'" />
        </ClerkShow>
      </template>
      <button
        type="button"
        class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-foreground transition-colors hover:bg-muted"
        :aria-expanded="mobileOpen"
        aria-label="Open menu"
        @click="toggleMobile"
      >
        <Icon :icon="mobileOpen ? 'mdi:close' : 'mdi:menu'" class="h-5 w-5" />
      </button>
    </div>
  </header>

  <!-- Mobile drawer — slides down beneath the sticky header. Pure CSS
       transition (no third-party modal lib) so it's cheap and matches
       the marketing theme. Tap a link → drawer auto-closes via the
       route watcher. Tap the backdrop → also closes. -->
  <Transition
    enter-active-class="transition-all duration-150 ease-out"
    leave-active-class="transition-all duration-100 ease-in"
    enter-from-class="opacity-0 -translate-y-2"
    leave-to-class="opacity-0 -translate-y-2"
  >
    <div
      v-if="mobileOpen"
      class="fixed inset-x-0 top-0 z-20 md:hidden"
      role="dialog"
      aria-modal="true"
    >
      <!-- Spacer matches the sticky header so the drawer slides BENEATH it. -->
      <div class="h-14"></div>
      <nav class="border-b border-border bg-background shadow-lg">
        <div class="flex flex-col py-2">
          <RouterLink
            v-for="link in NAV"
            :key="link.to"
            :to="link.to"
            class="px-5 py-3 text-body-lg font-medium text-foreground/85 transition-colors hover:bg-muted active:bg-muted"
            active-class="bg-muted text-foreground"
          >{{ link.label }}</RouterLink>
          <RouterLink
            v-if="showFeedback"
            to="/feedback"
            class="mx-4 mt-2 rounded-md border border-border bg-card px-4 py-2 text-center text-body-lg font-medium text-foreground transition-colors hover:border-primary/50"
          >{{ $t("nav.feedback") }}</RouterLink>
          <template v-if="showAccount && cfg.authRequired">
            <ClerkShow :when="'signed-out'">
              <RouterLink
                to="/login"
                class="mx-4 mt-2 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-body-lg font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
              >{{ $t("nav.signIn") }}</RouterLink>
            </ClerkShow>
            <ClerkShow :when="'signed-in'">
              <button
                v-if="showCancelPlan"
                type="button"
                class="mx-4 mt-2 rounded-md border border-border bg-card px-4 py-2 text-body font-medium text-muted-foreground transition-colors hover:border-destructive/50 hover:text-destructive"
                @click="onCancelPlan"
              >Cancel plan</button>
            </ClerkShow>
          </template>
        </div>
      </nav>
      <!-- Click-outside backdrop. Sized to fill the rest of the viewport. -->
      <div
        class="absolute inset-x-0 bottom-0 top-full -z-10 h-screen bg-background/40 backdrop-blur-[1px]"
        @click="closeMobile"
      ></div>
    </div>
  </Transition>
</template>
