/**
 * Server config store. Fetched once on app boot.
 *
 * `main.ts` waits on `ready` before installing the Clerk plugin so we
 * know the publishable key by the time `<SignIn />` renders.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import { getConfig } from "../api/config";

export const useConfigStore = defineStore("config", () => {
  const authRequired = ref(false);
  const clerkPublishableKey = ref("");
  // BYOK = the operator wired their own AI provider keys into the
  // backend env. When true the picker skips the login redirect and
  // Upgrade buttons disappear (they pay the AI provider directly,
  // our subscription is irrelevant).
  const byokMode = ref(false);
  const byokKeys = ref<string[]>([]);
  const ready = ref(false);

  async function refresh(): Promise<void> {
    try {
      const cfg = await getConfig();
      authRequired.value = !!cfg.auth_required;
      clerkPublishableKey.value = cfg.clerk_publishable_key || "";
      byokMode.value = !!cfg.byok_mode;
      byokKeys.value = Array.isArray(cfg.byok_keys) ? cfg.byok_keys : [];
    } catch (exc) {
      // Local-dev fallback: when the web backend isn't running on
      // localhost:8000 the Vite proxy fails on /api/config with
      // ECONNREFUSED, which used to leave Clerk uninitialised and
      // produce a header with no Sign-in button.
      //
      // To keep the SPA usable from `vite dev` without a backend,
      // honour `VITE_CLERK_PUBLISHABLE_KEY` from the environment so
      // Clerk can still boot, render <SignIn />, and let us test the
      // sign-in flow end-to-end. In production /api/config always
      // succeeds (Caddy → fastapi) so this branch never runs.
      const envKey = (import.meta as { env?: Record<string, string> }).env
        ?.VITE_CLERK_PUBLISHABLE_KEY;
      if (envKey) {
        console.warn("[config] /api/config failed; using VITE_CLERK_PUBLISHABLE_KEY fallback");
        authRequired.value = true;
        clerkPublishableKey.value = envKey;
        byokMode.value = false;
        byokKeys.value = [];
      } else {
        console.warn("[config] failed to fetch deploy config", exc);
      }
    } finally {
      ready.value = true;
    }
  }

  return {
    authRequired,
    clerkPublishableKey,
    byokMode,
    byokKeys,
    ready,
    refresh,
  };
});
