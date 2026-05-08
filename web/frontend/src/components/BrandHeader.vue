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
import { UserButton } from "@clerk/vue";

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
const logoHeight = computed(() => (isCompact.value ? "h-7" : "h-9 md:h-10"));
</script>

<template>
  <header
    class="flex items-center gap-4 border-b border-border bg-background/80 backdrop-blur"
    :class="padding"
  >
    <!-- Optional leading slot (used by Workspace for the back button) -->
    <slot name="leading" />

    <!-- Wordmark. The white-logo SVG already contains the "Digi Setu"
         text, so we don't duplicate it next to the image. We use two
         render paths instead of `<component :is>` so vue-router's
         RouterLink stays type-safe and we don't pay for v-bind dispatch. -->
    <RouterLink
      v-if="homeLink"
      to="/"
      class="flex shrink-0 items-center transition-opacity hover:opacity-80"
      aria-label="Digi Setu — home"
    >
      <img
        src="/digi-setu-logo.svg"
        alt="Digi Setu"
        class="w-auto select-none"
        :class="logoHeight"
        draggable="false"
      />
    </RouterLink>
    <div v-else class="flex shrink-0 items-center" aria-label="Digi Setu">
      <img
        src="/digi-setu-logo.svg"
        alt="Digi Setu"
        class="w-auto select-none"
        :class="logoHeight"
        draggable="false"
      />
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
    <nav class="flex items-center gap-3 text-[12px]">
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
        class="rounded-md border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
        title="Send feedback to the team"
      >Feedback</RouterLink>

      <UserButton
        v-if="showAccount && cfg.authRequired"
        :after-sign-out-url="'/login'"
      />
    </nav>
  </header>
</template>
