<!--
  BrandHeader — shared top bar used on every "shell" view.

  One header, one place to maintain it. Slots into:

      Picker      (the landing / session picker)
      Pricing     (public plans page)
      Privacy     (legal)
      Terms       (legal)
      Login       (Clerk wrapper)
      Workspace   (above the IDE shell — variant=compact + a leading
                  "back to sessions" button)

  Variants:
    full     → tall hero header (default). Logo on the left, full
               nav + account actions on the right.
    compact  → short bar suitable for the workspace IDE: logo + a
               leading slot (we use it for the back button) and the
               same account/nav actions, but smaller.

  The right-side nav links are configurable via `links` prop so each
  page can choose which neighbours to show. Nothing here is page-
  specific — a redesign should only touch this component.
-->
<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
// `@clerk/vue` v2.2.0 doesn't ship the React-style <SignedIn>/<SignedOut>
// wrapper components — it ships a single <Show :when="'signed-in'">
// (or "signed-out") with the same semantics. We use it below to gate
// the Sign-in CTA vs. the UserButton avatar.
import { Show as ClerkShow, UserButton } from "@clerk/vue";

import { useConfigStore } from "../stores/config";

interface NavLink {
  to: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    /** Visual density. */
    variant?: "full" | "compact";
    /** Right-side nav entries. Defaults vary by route — every page
     *  passes its own. */
    links?: NavLink[];
    /** When true, render the Feedback button. Hidden on Login since
     *  there's nothing to give feedback about yet. */
    showFeedback?: boolean;
    /** When true, render the Clerk account avatar. */
    showAccount?: boolean;
    /** Make the wordmark a router-link to "/". Disable on the picker
     *  itself (the user is already on home). */
    homeLink?: boolean;
  }>(),
  {
    variant: "full",
    // Default nav. Pages that need a different mix (Login hides
    // everything, Workspace hides Activity for visual breathing
    // room) override `links` directly.
    links: () => [
      { to: "/activity", label: "Activity" },
      { to: "/pricing", label: "Pricing" },
      { to: "/download", label: "Download" },
      { to: "/privacy", label: "Privacy" },
      { to: "/terms", label: "Terms" },
    ],
    showFeedback: true,
    showAccount: true,
    homeLink: true,
  },
);

const cfg = useConfigStore();

const isCompact = computed(() => props.variant === "compact");
const padding = computed(() =>
  isCompact.value ? "px-4 py-2" : "px-6 py-4 md:px-8",
);
// Logo icon (square) — sized to read at the chosen variant. The wordmark
// "Digi Setu" text rendered next to it scales to match.
const logoHeight = computed(() => (isCompact.value ? "h-6" : "h-8"));
const wordmarkClass = computed(() =>
  isCompact.value
    ? "text-h2 font-semibold tracking-tight"
    : "text-h2 font-semibold tracking-tight md:text-h1",
);
</script>

<template>
  <header
    class="flex items-center gap-4 border-b border-border bg-background/80 backdrop-blur"
    :class="padding"
  >
    <!-- Optional leading slot (used by Workspace for the back button) -->
    <slot name="leading" />

    <!-- Brand: icon + "Digi Setu" wordmark in Inter. The SVG asset is
         icon-only; the text is rendered alongside so the brand is
         legible at every variant size. We use two render paths
         instead of `<component :is>` so vue-router's RouterLink stays
         type-safe and we don't pay for v-bind dispatch. -->
    <RouterLink
      v-if="homeLink"
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
    <div v-else class="flex shrink-0 items-center gap-2" :aria-label="$t('brand.name')">
      <img
        src="/digi-setu-logo.svg"
        alt=""
        aria-hidden="true"
        class="w-auto select-none"
        :class="logoHeight"
        draggable="false"
      />
      <span :class="wordmarkClass">{{ $t("brand.name") }}</span>
    </div>

    <!-- Center slot — pages can drop in a workspace name, breadcrumb,
         status pill, etc. Hidden on small screens so the header never
         wraps. -->
    <div class="hidden min-w-0 flex-1 md:block">
      <slot />
    </div>
    <div v-if="!$slots.default" class="hidden flex-1 md:block" />

    <!-- Trailing actions: nav links → feedback → account.
         All compact text-buttons; hover reveals a subtle underline. -->
    <nav class="flex items-center gap-3 text-body">
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="text-muted-foreground hover:text-foreground hover:underline"
        active-class="text-foreground"
      >{{ link.label }}</RouterLink>

      <!-- Feedback is a real route now (/feedback) — RouterLink keeps
           browser-back working and survives full page reloads. -->
      <RouterLink
        v-if="showFeedback"
        to="/feedback"
        class="rounded-md border border-border bg-card px-2.5 py-1 text-body text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
        :title="$t('nav.feedback')"
      >{{ $t("nav.feedback") }}</RouterLink>

      <!-- Account surface. Clerk's <UserButton> renders the avatar + menu
           ONLY when the user is signed in. To make sure signed-out users
           have a visible CTA (the avatar slot is empty otherwise), we
           pair it with a <Show :when="'signed-out'"> "Sign in" button.
           The bounded v-if="showAccount && cfg.authRequired" stays so
           the legacy AUTH_REQUIRED=false dev mode still hides everything.
      -->
      <template v-if="showAccount && cfg.authRequired">
        <ClerkShow :when="'signed-out'">
          <RouterLink
            to="/login"
            class="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-body font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          >{{ $t("nav.signIn") }}</RouterLink>
        </ClerkShow>
        <ClerkShow :when="'signed-in'">
          <UserButton :after-sign-out-url="'/login'" />
        </ClerkShow>
      </template>
    </nav>
  </header>
</template>
