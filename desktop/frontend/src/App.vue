<!--
  App — global shell. Mounts the router-view and the singleton overlays
  (toasts, confirm modal). Per-route content lives in `views/`.

  Boot gate: render a small "Starting…" splash while the config /
  auth stores are still warming up. main.ts already awaits both
  before mount, so this branch is normally bypassed in <1ms — it
  only shows up if a later code path resets `ready` (e.g. a manual
  refresh during a flaky sidecar reconnect).
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

import BrandHeader from "./components/BrandHeader.vue";
import ConfirmModal from "./components/ConfirmModal.vue";
import Toast from "./components/Toast.vue";
import { useConfigStore } from "./stores/config";
import { useAuthStore } from "./stores/auth";
import { useUiStore } from "./stores/ui";

const cfg = useConfigStore();
const auth = useAuthStore();
const ui = useUiStore();
const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const booted = computed<boolean>(() => cfg.ready && auth.ready);

// Read the per-route header variant — see router.ts route meta.
// "none" hides the global header (no current routes use this); "compact"
// shrinks the bar for the IDE shell; default is "full".
const headerVariant = computed<"full" | "compact" | "none">(() => {
  const v = (route.meta as { header?: "full" | "compact" | "none" } | undefined)?.header;
  return v ?? "full";
});

// Hide the BrandHeader on the IDE chat shell — that view has its own
// purpose-built top bar (back button + chat title + tabs) and adding
// the global brand header on top would push the editor off-screen.
const showHeader = computed(() => headerVariant.value !== "none" && route.name !== "chat");

// Refresh config + auth on window focus. The natural moment for a
// user to "expect changes to land" is when they alt-tab back from
// Finder (after editing ~/.digi-setu/.env to drop a BYOK key) or
// from the browser (after completing the desktop sign-in bounce).
// Both cases are cheap loopback fetches (<1ms) so we don't bother
// debouncing.
//
// The sidecar's dotenv watcher also re-evaluates BYOK keys server-
// side every 2s, so even without focus the next /api/config call
// returns the right answer. This handler just makes the refresh
// instant on the visible refocus, instead of "after the next
// router navigation".
//
// Auth-side: if the user is sitting on /login waiting for the
// browser sign-in bounce to come back, the sidecar's localhost
// callback at /api/auth/desktop-callback will have minted a JWT
// before they alt-tab here. We notice that on this refresh and
// kick them to / so they don't have to click anything to land
// on the workspace picker. Without this hop they'd see a stale
// Welcome screen with a primed-but-invisible signed_in state.
async function refreshOnFocus(): Promise<void> {
  const wasSignedIn = auth.signedIn;
  try {
    await Promise.all([cfg.refresh(), auth.refresh()]);
  } catch {
    return;
  }
  // Visible confirmation that the browser sign-in landed: a one-time
  // toast on the false→true transition. Without this, the user has no
  // signal anything happened (sign-in completed in the *browser*; the
  // desktop window only finds out on focus refresh).
  if (!wasSignedIn && auth.signedIn) {
    const label = auth.name || auth.email;
    const msg = label
      ? t("auth.welcomeBackToast", { name: label })
      : t("auth.signedInToast");
    ui.toast({ message: msg, kind: "success" });
  }
  if (auth.signedIn && router.currentRoute.value.name === "login") {
    router.replace({ path: "/" }).catch(() => {});
  }
}
onMounted(() => {
  window.addEventListener("focus", refreshOnFocus);
});
onBeforeUnmount(() => {
  window.removeEventListener("focus", refreshOnFocus);
});
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background text-foreground">
    <template v-if="booted">
      <BrandHeader v-if="showHeader" :variant="headerVariant === 'compact' ? 'compact' : 'full'" />
      <div class="flex min-h-0 flex-1 flex-col">
        <RouterView />
      </div>
      <Toast />
      <ConfirmModal />
    </template>
    <template v-else>
      <div class="flex h-full w-full flex-col items-center justify-center gap-3 text-muted-foreground">
        <span
          class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"
          aria-hidden="true"
        />
        <p class="text-body">{{ $t("app.starting") }}</p>
      </div>
    </template>
  </div>
</template>
