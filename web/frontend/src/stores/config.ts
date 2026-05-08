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
  const ready = ref(false);

  async function refresh(): Promise<void> {
    try {
      const cfg = await getConfig();
      mode.value = cfg.mode === "desktop" ? "desktop" : "web";
      authRequired.value = !!cfg.auth_required;
      clerkPublishableKey.value = cfg.clerk_publishable_key || "";
    } catch (exc) {
      console.warn("[config] failed to fetch deploy config", exc);
    } finally {
      ready.value = true;
    }
  }

  return { mode, authRequired, clerkPublishableKey, ready, refresh };
});
