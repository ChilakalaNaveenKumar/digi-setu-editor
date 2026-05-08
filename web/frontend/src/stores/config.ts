/**
 * Server config store. Fetched once on app boot.
 *
 * The router and the picker view branch on `mode`. `main.ts` waits on
 * `ready` before installing the Clerk plugin so we know the
 * publishable key by the time `<SignIn />` renders.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import { getConfig } from "../api/config";
import type { DeployMode } from "../api/types";

export const useConfigStore = defineStore("config", () => {
  const mode = ref<DeployMode>("web");
  const authRequired = ref(false);
  const clerkPublishableKey = ref("");
  // BYOK = user dropped their own AI keys into ~/.digi-setu/.env.
  // When true the picker skips the login redirect, the header shows
  // a "Using your own key" chip, and Upgrade buttons disappear (they
  // pay the AI provider directly, our subscription is irrelevant).
  const byokMode = ref(false);
  const byokKeys = ref<string[]>([]);
  const ready = ref(false);

  async function refresh(): Promise<void> {
    try {
      const cfg = await getConfig();
      mode.value = cfg.mode === "desktop" ? "desktop" : "web";
      authRequired.value = !!cfg.auth_required;
      clerkPublishableKey.value = cfg.clerk_publishable_key || "";
      byokMode.value = !!cfg.byok_mode;
      byokKeys.value = Array.isArray(cfg.byok_keys) ? cfg.byok_keys : [];
    } catch (exc) {
      console.warn("[config] failed to fetch deploy config", exc);
    } finally {
      ready.value = true;
    }
  }

  return {
    mode,
    authRequired,
    clerkPublishableKey,
    byokMode,
    byokKeys,
    ready,
    refresh,
  };
});
