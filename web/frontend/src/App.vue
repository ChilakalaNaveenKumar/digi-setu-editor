<!--
  App — global shell. Mounts the router-view, the singleton overlays
  (toasts, confirm modal), the global BrandHeader, and the shared
  AppFooter (per route.meta).

  Per-route content lives in `views/`. The header and footer used to
  live inside each view, which meant every page silently rebuilt its
  own chrome — the user saw a slightly different nav on every screen
  and copyright years drifted between views. They now mount here once.
-->
<script setup lang="ts">
import { computed, onMounted } from "vue";
import { RouterView, useRoute } from "vue-router";

import BrandHeader from "./components/BrandHeader.vue";
import AppFooter from "./components/AppFooter.vue";
import ConfirmModal from "./components/ConfirmModal.vue";
import Toast from "./components/Toast.vue";
import { useConfigStore } from "./stores/config";

const cfg = useConfigStore();
const route = useRoute();

// Fetch deploy mode once on boot — Picker.vue waits on `cfg.ready`.
onMounted(() => {
  void cfg.refresh();
});

// Read the per-route header variant — see router.ts route meta.
// "none" hides the global header (no current routes use this);
// "compact" shrinks the bar for the IDE shell; default is "full".
const headerVariant = computed<"full" | "compact" | "none">(() => {
  const v = (route.meta as { header?: "full" | "compact" | "none" } | undefined)?.header;
  return v ?? "full";
});

// Hide the BrandHeader on the IDE chat shell — that view has its own
// purpose-built top bar (status pills, model picker, etc) and adding
// the global brand header on top would push the editor off-screen.
const showHeader = computed(
  () => headerVariant.value !== "none" && route.name !== "chat",
);

const showFooter = computed<boolean>(() => {
  const f = (route.meta as { footer?: boolean } | undefined)?.footer;
  // Default true — public-page surfaces want the footer; only the
  // chat IDE opts out via meta.footer = false.
  return f !== false && route.name !== "chat";
});

// Two distinct layout shapes share this shell — pick per route:
//
//   1. Chat IDE (/chat/:sid):
//      A fixed-height app-shell. The file-tree, editor and chat
//      panes scroll INDEPENDENTLY inside the viewport; the page
//      itself never scrolls. Needs an exact height so the inner
//      `h-full` chains resolve (otherwise panes collapse and you
//      get the giant black void underneath the IDE we saw before).
//      → `h-screen overflow-hidden`.
//
//   2. Marketing / settings (Home, Pricing, Picker, Privacy, Terms,
//      Activity, Login, Feedback, Download, Desktop sign-in):
//      Long-scroll documents. The shell must GROW with content so
//      the AppFooter docks at the bottom of the document, not at
//      the bottom of the viewport. → `min-h-screen` (≥100vh, no
//      upper cap, body scrolls naturally).
//
//   We keyed off `route.name === "chat"` (the only IDE route) so the
//   class swap is unambiguous. Earlier we tried a single `min-h-screen`
//   for both and the IDE's `h-full` panes lost their height anchor.
const rootClass = computed<string>(() =>
  route.name === "chat"
    ? "flex h-screen w-full flex-col overflow-hidden bg-background text-foreground"
    : "flex min-h-screen w-full flex-col bg-background text-foreground",
);
</script>

<template>
  <div :class="rootClass">
    <BrandHeader
      v-if="showHeader"
      :variant="headerVariant === 'compact' ? 'compact' : 'full'"
    />
    <div class="flex min-h-0 flex-1 flex-col">
      <RouterView />
    </div>
    <AppFooter v-if="showFooter" />
    <Toast />
    <ConfirmModal />
  </div>
</template>
