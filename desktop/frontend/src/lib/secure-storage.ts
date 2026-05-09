/**
 * Tauri secure-storage IPC wrappers.
 *
 * Cursor-style "stay signed in" UX. The Clerk session id is stashed
 * in the OS keychain (macOS Keychain Services / Windows Credential
 * Vault / Linux libsecret) by the Rust shell so it survives app
 * restarts. The SPA reads it back at boot, calls
 * /api/auth/desktop-refresh to mint a fresh JWT, and the user is
 * signed in without any browser bounce.
 *
 * Web mode no-ops every call here — none of the keychain plumbing
 * exists outside the Tauri shell. The same SPA bundle still loads;
 * `isDesktop()` gates these calls on the consumer side.
 */

import { isDesktop } from "./native-bridge";

/** Persist a Clerk session id. Resolves silently on web mode. */
export async function storeSessionId(sessionId: string): Promise<void> {
  if (!isDesktop() || !sessionId) return;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("secure_store_session", { sessionId });
  } catch (err) {
    // Keyring failures (locked vault, headless Linux without
    // secret-service) are NOT user-facing. Log for our debugging
    // and let the app continue — the worst-case is the user has
    // to sign in again next launch.
    console.warn("[secure-storage] store failed", err);
  }
}

/** Read the cached Clerk session id, or null if none / unavailable. */
export async function loadSessionId(): Promise<string | null> {
  if (!isDesktop()) return null;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const sid = await invoke<string | null>("secure_load_session");
    return sid && sid.trim() ? sid : null;
  } catch (err) {
    console.warn("[secure-storage] load failed", err);
    return null;
  }
}

/** Clear the cached session id (sign-out + refresh-failure cleanup). */
export async function deleteSessionId(): Promise<void> {
  if (!isDesktop()) return;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("secure_delete_session");
  } catch (err) {
    console.warn("[secure-storage] delete failed", err);
  }
}
