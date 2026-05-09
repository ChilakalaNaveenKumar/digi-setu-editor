<!--
  CloudRedirect — placeholder page that hands the user off to the
  equivalent surface on digi-setu.com.

  Used for /pricing and /activity so:

    1. Billing UX (Stripe Checkout, Customer Portal, Cancel) stays in
       the user's normal Clerk-authenticated browser session — the
       desktop never touches Stripe.
    2. Activity / usage data is read directly from the cloud's
       authoritative ledger by the cloud SPA. The desktop binary
       never queries the cloud DB and never caches a copy that the
       user could tamper with.

  UX:
    • Opens the system browser to the target URL on mount.
    • Renders a minimal "Opened in your browser" card with a
      manual "Open again" button in case the OS swallowed the
      first openExternal() (browser was closing / focus stolen / …).
    • A back link returns the user to the picker.
-->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import AppFooter from "../components/AppFooter.vue";
import { openExternal } from "../lib/native-bridge";

const props = withDefaults(
  defineProps<{
    /** Symbolic target — "ACTIVITY" or "PRICING". Resolved against
     *  the same VITE_DESKTOP_AUTH_URL / digi-setu.com base used by
     *  the billing redirects. */
    target: "ACTIVITY" | "PRICING";
    /** Human title for the card. */
    title?: string;
  }>(),
  { title: "Continuing in your browser" },
);

const router = useRouter();
const opened = ref(false);
const lastError = ref<string | null>(null);

function _resolveUrl(): string {
  const env = (import.meta as { env?: Record<string, string> }).env;
  const fromEnv = env?.VITE_DIGI_SETU_WEB_BASE || env?.VITE_DESKTOP_AUTH_URL;
  const base = (fromEnv || "https://digi-setu.com").replace(/\/+$/, "");
  switch (props.target) {
    case "ACTIVITY":
      return `${base}/activity?source=desktop`;
    case "PRICING":
      return `${base}/pricing?source=desktop`;
    default:
      return base;
  }
}

async function openIt(): Promise<void> {
  lastError.value = null;
  try {
    await openExternal(_resolveUrl());
    opened.value = true;
  } catch (exc) {
    lastError.value = exc instanceof Error ? exc.message : String(exc);
  }
}

onMounted(() => {
  void openIt();
});
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="flex flex-1 items-center justify-center px-6 py-12">
      <div class="w-full max-w-md rounded-lg border border-border bg-card p-6 text-center">
        <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Icon icon="codicon:link-external" class="h-6 w-6 text-primary" />
        </div>
        <h1 class="text-h2 font-semibold tracking-tight">{{ title }}</h1>
        <p class="mt-2 text-body text-muted-foreground">
          {{ title }} lives on
          <code class="font-mono text-caption">digi-setu.com</code>
          so payments and usage data stay in your signed-in browser
          session. We've opened the page for you.
        </p>

        <div
          v-if="lastError"
          class="mt-4 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-left text-caption text-destructive"
        >
          Couldn't open the browser: {{ lastError }}
        </div>

        <div class="mt-5 flex flex-col gap-2">
          <button
            type="button"
            class="inline-flex items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-body font-semibold text-primary-foreground hover:opacity-90"
            @click="openIt"
          >
            <Icon icon="codicon:link-external" class="h-4 w-4" />
            <span>{{ opened ? "Open again" : "Open in browser" }}</span>
          </button>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-md border border-border bg-card px-3 py-2 text-body text-muted-foreground hover:border-primary/40 hover:text-foreground"
            @click="router.push('/')"
          >
            Back to workspaces
          </button>
        </div>
      </div>
    </main>

    <AppFooter />
  </div>
</template>
