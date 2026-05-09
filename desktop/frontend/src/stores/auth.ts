/**
 * Auth store — desktop user session state.
 *
 * The desktop frontend is intentionally Clerk-free (no @clerk/vue).
 * Every Clerk SDK call lives in the Python sidecar; this store is a
 * thin Pinia wrapper around the sidecar's `/api/auth/whoami` and
 * `/api/auth/desktop-sign-out` endpoints, plus the OS-keychain ops
 * exposed by Tauri's `secure_storage` IPC commands.
 *
 * Lifecycle:
 *   - `refresh()` is called once at boot (after `restoreDesktopSession()`)
 *     and again after every successful deep-link auth callback.
 *   - `signOut()` clears the sidecar cache + the OS keychain so the
 *     next launch lands back on the Welcome screen.
 *
 * This store NEVER imports @clerk/vue. All Clerk interaction is
 * server-side in the sidecar.
 */
import { defineStore } from "pinia";
import { ref } from "vue";

import { apiJson, apiPost } from "../api/client";
import { deleteSessionId } from "../lib/secure-storage";

interface WhoamiResponse {
  signed_in: boolean;
  user_id: string | null;
  email: string | null;
  name: string | null;
  image_url: string | null;
  mode?: string;
}

export const useAuthStore = defineStore("auth", () => {
  const signedIn = ref(false);
  const userId = ref<string | null>(null);
  const email = ref<string | null>(null);
  const name = ref<string | null>(null);
  const imageUrl = ref<string | null>(null);
  const ready = ref(false);

  async function refresh(): Promise<void> {
    try {
      const res = await apiJson<WhoamiResponse>("/api/auth/whoami");
      signedIn.value = !!res.signed_in;
      userId.value = res.user_id || null;
      email.value = res.email || null;
      name.value = res.name || null;
      imageUrl.value = res.image_url || null;
    } catch (exc) {
      // Endpoint missing or sidecar offline — leave state as-is so the
      // header doesn't flicker. Logged for the dev console only.
      console.warn("[auth] whoami failed", exc);
    } finally {
      ready.value = true;
    }
  }

  async function signOut(): Promise<void> {
    try {
      await apiPost("/api/auth/desktop-sign-out", {});
    } catch (exc) {
      console.warn("[auth] sign-out POST failed", exc);
    }
    try {
      await deleteSessionId();
    } catch (exc) {
      console.warn("[auth] keychain delete failed", exc);
    }
    signedIn.value = false;
    userId.value = null;
    email.value = null;
    name.value = null;
    imageUrl.value = null;
  }

  return {
    signedIn,
    userId,
    email,
    name,
    imageUrl,
    ready,
    refresh,
    signOut,
  };
});
