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

  Account menu uses <Teleport to="body"> so the dropdown can't collide
  with the model picker tooltip / credit chip / status pills inside the
  chat pane (z-index trap that the user reported in the screenshot).
-->
<script setup lang="ts">
import { computed, ref, onBeforeUnmount, watch, nextTick } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { useConfigStore } from "../stores/config";
import { useAuthStore } from "../stores/auth";
import { useBillingStore } from "../stores/billing";
import { openExternal } from "../lib/native-bridge";
import { cloudPortalUrl } from "../api/billing";

interface NavLink {
  /** Route path for an internal vue-router target. */
  to?: string;
  /** Symbolic external token (resolved via `_externalUrl`). */
  external?: "ACTIVITY" | "PRICING";
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

// FIXED nav set used on every page. Activity + Pricing route to the
// cloud web app (browser-side billing UI lives there). Privacy / Terms
// move to the footer to keep the top bar focused on actions.
//
// Desktop ships no separate "marketing home" page — the picker IS
// the home — so we just expose Workspaces (/) and the cloud links.
const NAV: NavLink[] = [
  { to: "/", label: "Workspaces" },
  { external: "PRICING", label: "Pricing" },
  { external: "ACTIVITY", label: "Activity" },
];

const cfg = useConfigStore();
const auth = useAuthStore();
const billing = useBillingStore();
const router = useRouter();

function _externalUrl(token: "ACTIVITY" | "PRICING"): string {
  const env = (import.meta as { env?: Record<string, string> }).env;
  const fromEnv = env?.VITE_DIGI_SETU_WEB_BASE || env?.VITE_DESKTOP_AUTH_URL;
  const base = (fromEnv || "https://digi-setu.com").replace(/\/+$/, "");
  switch (token) {
    case "ACTIVITY":
      return `${base}/activity?source=desktop`;
    case "PRICING":
      return `${base}/pricing?source=desktop`;
  }
}

async function onExternalClick(token: "ACTIVITY" | "PRICING"): Promise<void> {
  await openExternal(_externalUrl(token));
}

// Manage Subscription bounces to the Stripe Customer Portal in the
// user's signed-in browser session. We surface it on desktop so paid
// users can update their card without hunting through the cloud SPA;
// "Cancel plan" itself lives there too (one click inside the portal),
// but the desktop binary doesn't expose a separate cancel flow — that
// CTA only ships on the web fork where the billing surface lives.
async function onManageSubscription(): Promise<void> {
  closeMenu();
  await openExternal(cloudPortalUrl());
}

const hasCustomer = computed(() => !!billing.credit?.stripe_customer_id);
const showManageSubscription = computed(() => hasCustomer.value);

const isCompact = computed(() => props.variant === "compact");
const padding = computed(() =>
  isCompact.value ? "px-4 py-2" : "px-6 py-3 md:px-8 md:py-3.5",
);
const logoHeight = computed(() => (isCompact.value ? "h-6" : "h-7"));
const wordmarkClass = computed(() =>
  isCompact.value
    ? "text-h2 font-semibold tracking-tight text-foreground"
    : "text-h2 font-semibold tracking-tight text-foreground",
);

// Account popover. We position it via fixed coordinates anchored to the
// trigger button and Teleport to <body> so it cannot be clipped by any
// containing pane (chat sidebar, splitpanes) or covered by tooltips
// rendered in unrelated components.
const menuOpen = ref(false);
const triggerRef = ref<HTMLButtonElement | null>(null);
const menuStyle = ref<Record<string, string>>({});

function repositionMenu(): void {
  const t = triggerRef.value;
  if (!t) return;
  const r = t.getBoundingClientRect();
  const margin = 8;
  const width = 240;
  let left = r.right - width;
  if (left < margin) left = margin;
  if (left + width > window.innerWidth - margin) {
    left = window.innerWidth - margin - width;
  }
  menuStyle.value = {
    position: "fixed",
    top: `${r.bottom + 6}px`,
    left: `${left}px`,
    width: `${width}px`,
    zIndex: "var(--z-popover)",
  };
}

function toggleMenu(): void {
  menuOpen.value = !menuOpen.value;
}
function closeMenu(): void {
  menuOpen.value = false;
}
async function onSignOut(): Promise<void> {
  closeMenu();
  await auth.signOut();
  await router.push({ name: "login" });
}

const initials = computed(() => {
  const name = auth.name || auth.email || "";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  if (parts.length === 1 && parts[0]) return parts[0][0].toUpperCase();
  return "?";
});

const menuLabel = computed(() => auth.email || auth.name || "Account");

function onDocClick(e: MouseEvent): void {
  const target = e.target as HTMLElement | null;
  if (!target) return closeMenu();
  // The trigger handles its own toggle.
  if (triggerRef.value?.contains(target)) return;
  // Clicks inside the teleported menu stay open.
  if (target.closest('[data-account-menu="popover"]')) return;
  closeMenu();
}
function onKey(e: KeyboardEvent): void {
  if (e.key === "Escape") closeMenu();
}
async function watchMenu(open: boolean): Promise<void> {
  if (open) {
    await nextTick();
    repositionMenu();
    document.addEventListener("click", onDocClick, true);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", repositionMenu);
    window.addEventListener("scroll", repositionMenu, true);
  } else {
    document.removeEventListener("click", onDocClick, true);
    document.removeEventListener("keydown", onKey);
    window.removeEventListener("resize", repositionMenu);
    window.removeEventListener("scroll", repositionMenu, true);
  }
}
watch(menuOpen, watchMenu);
onBeforeUnmount(() => watchMenu(false));
</script>

<template>
  <header
    class="sticky top-0 flex items-center gap-4 border-b border-border bg-background"
    :class="padding"
    :style="{ zIndex: 'var(--z-header)' }"
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

    <!-- Trailing actions: nav links → feedback → account.
         Links use foreground/80 (not muted-foreground) so they're
         readable at a glance — earlier muted variant looked dead. -->
    <nav class="flex items-center gap-1 text-body">
      <template v-for="link in NAV" :key="link.to ?? link.external">
        <RouterLink
          v-if="link.to"
          :to="link.to"
          class="rounded-md px-2.5 py-1.5 text-body-lg font-medium text-foreground/75 transition-colors hover:bg-muted hover:text-foreground"
          active-class="text-foreground bg-muted"
        >{{ link.label }}</RouterLink>
        <button
          v-else-if="link.external"
          type="button"
          class="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-body-lg font-medium text-foreground/75 transition-colors hover:bg-muted hover:text-foreground"
          @click="onExternalClick(link.external)"
        >
          <span>{{ link.label }}</span>
          <svg
            class="h-3 w-3 opacity-60"
            viewBox="0 0 12 12"
            fill="none"
            aria-hidden="true"
          >
            <path d="M4.5 2H10v5.5M10 2L5 7M2.5 4.5v5h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </template>

      <RouterLink
        v-if="showFeedback"
        to="/feedback"
        class="ml-1 rounded-md border border-border bg-card px-3 py-1.5 text-body-lg font-medium text-foreground transition-colors hover:border-primary/50"
      >{{ $t("nav.feedback") }}</RouterLink>

      <template v-if="showAccount && cfg.authRequired">
        <RouterLink
          v-if="!auth.signedIn"
          to="/login"
          class="ml-2 inline-flex items-center rounded-md bg-primary px-3.5 py-1.5 text-body-lg font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
        >{{ $t("nav.signIn") }}</RouterLink>

        <button
          v-else
          ref="triggerRef"
          type="button"
          class="ml-2 flex items-center gap-2.5 rounded-md border border-border bg-card px-2 py-1 text-left transition-colors hover:border-primary/50"
          :title="menuLabel"
          :aria-label="menuLabel"
          aria-haspopup="menu"
          :aria-expanded="menuOpen"
          @click.stop="toggleMenu"
        >
          <span class="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-muted text-caption font-semibold text-foreground">
            <img
              v-if="auth.imageUrl"
              :src="auth.imageUrl"
              :alt="menuLabel"
              class="h-full w-full object-cover"
              referrerpolicy="no-referrer"
            />
            <span v-else>{{ initials }}</span>
          </span>
          <span class="hidden min-w-0 max-w-[12rem] flex-col leading-tight md:flex">
            <span
              v-if="auth.name"
              class="truncate text-body font-medium text-foreground"
            >{{ auth.name }}</span>
            <span
              v-if="auth.email"
              class="truncate text-caption text-muted-foreground"
            >{{ auth.email }}</span>
            <span
              v-else-if="!auth.name"
              class="truncate text-body font-medium text-foreground"
            >{{ $t('nav.account') }}</span>
          </span>
          <svg
            class="hidden h-3 w-3 shrink-0 text-muted-foreground md:block"
            viewBox="0 0 12 12"
            fill="none"
            aria-hidden="true"
          >
            <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </template>
    </nav>

    <!-- Teleported account dropdown — escapes any z-index trap inside
         a containing splitpane / chat sidebar. Background is fully
         opaque so tooltips from underlying components can't bleed
         through. -->
    <Teleport to="body">
      <div
        v-if="menuOpen && showAccount && cfg.authRequired && auth.signedIn"
        data-account-menu="popover"
        role="menu"
        :style="menuStyle"
        class="overflow-hidden rounded-md border border-border bg-popover text-popover-foreground shadow-xl ring-1 ring-black/10"
      >
        <div class="border-b border-border px-3 py-2">
          <div class="truncate text-body font-medium text-foreground">
            {{ auth.name || $t("nav.account") }}
          </div>
          <div
            v-if="auth.email"
            class="truncate text-caption text-muted-foreground"
          >{{ auth.email }}</div>
        </div>
        <button
          v-if="showManageSubscription"
          type="button"
          role="menuitem"
          class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-body text-foreground hover:bg-muted"
          :title="$t('nav.manageSubscriptionHint')"
          @click="onManageSubscription"
        >
          <span>{{ $t("nav.manageSubscription") }}</span>
          <svg
            class="h-3 w-3 opacity-70"
            viewBox="0 0 12 12"
            fill="none"
            aria-hidden="true"
          >
            <path d="M4.5 2H10v5.5M10 2L5 7M2.5 4.5v5h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <RouterLink
          to="/pricing"
          role="menuitem"
          class="flex w-full items-center gap-2 px-3 py-2 text-left text-body text-foreground hover:bg-muted"
          @click="closeMenu"
        >
          See plans
        </RouterLink>
        <button
          type="button"
          role="menuitem"
          class="block w-full border-t border-border px-3 py-2 text-left text-body text-foreground hover:bg-muted"
          @click="onSignOut"
        >{{ $t("nav.signOut") }}</button>
      </div>
    </Teleport>
  </header>
</template>
