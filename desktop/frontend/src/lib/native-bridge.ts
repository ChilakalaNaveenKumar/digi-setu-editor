/**
 * Tiny runtime-detected bridge to native (Tauri) capabilities.
 *
 * The same SPA bundle ships to both the web (Vite + Caddy) and desktop
 * (Tauri shell) deployments. We feature-detect Tauri at runtime via
 * `window.__TAURI_INTERNALS__` (injected by the Tauri WebView when
 * `withGlobalTauri: true` is set) and fall through to web-flavour
 * implementations otherwise.
 *
 * Why dynamic imports of `@tauri-apps/api`? Static imports would force
 * Vite to bundle the package into every web build too, even though the
 * web build never executes any of its code. Dynamic imports tree-shake
 * properly: if `isDesktop()` is false, the chunk is fetched but never
 * evaluated; if you want it gone entirely, conditional `await import`
 * (used here) keeps it out of the initial bundle.
 *
 * Lifecycle of a desktop session:
 *   1. App boots, calls `getBackendPort()` to discover the sidecar's
 *      port (which is randomised per launch — see desktop/src-tauri/
 *      src/sidecar.rs).
 *   2. Picker view calls `pickFolder()` for the workspace selector.
 *   3. Auth + billing flows call `openExternal()` to bounce out to the
 *      user's default browser, then come back via `onDeepLink()`.
 */

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
    __TAURI__?: unknown;
  }
}

/** True when running inside the Tauri desktop shell. */
export function isDesktop(): boolean {
  if (typeof window === "undefined") return false;
  return "__TAURI_INTERNALS__" in window || "__TAURI__" in window;
}

/**
 * Local TCP port the desktop sidecar is bound to. Tauri spawns the
 * sidecar with a random free port to avoid clashing with a locally-
 * running web backend; we surface it so the SPA can build absolute
 * URLs (`http://127.0.0.1:<port>/api/...`).
 *
 * In web mode this returns `null` and callers should fall through to
 * relative paths (Caddy reverse-proxies them server-side).
 */
export async function getBackendPort(): Promise<number | null> {
  if (!isDesktop()) return null;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<number | null>("get_backend_port");
  } catch {
    return null;
  }
}

/** OS app-data dir for "show me where my data lives" UI affordances. */
export async function getAppDataDir(): Promise<string | null> {
  if (!isDesktop()) return null;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<string>("app_data_dir");
  } catch {
    return null;
  }
}

/**
 * Native folder picker. Returns null when the user cancels.
 *
 * Falls back to `window.prompt()` in web mode so the same Picker.vue
 * code path keeps working without a wrapper conditional everywhere.
 * The web fallback is intentionally awful — the web build of this
 * SPA is for the cloud product where users never touch a folder
 * picker at all (they get a sandboxed workspace), so the prompt is
 * only there for power users or one-off testing.
 */
export async function pickFolder(): Promise<string | null> {
  if (!isDesktop()) {
    const path = window.prompt("Absolute path to workspace folder:");
    return path && path.trim() ? path.trim() : null;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<string | null>("pick_folder");
  } catch (err) {
    console.error("pickFolder failed:", err);
    return null;
  }
}

/**
 * Open a URL in the user's default browser. The Tauri webview is
 * non-default-browser by definition (no autofill, no Clerk's
 * fingerprint, can't satisfy 3DS) so OAuth + Stripe Checkout MUST
 * leave the embedded webview.
 *
 * In web mode this just opens a new tab via `window.open`.
 */
export async function openExternal(url: string): Promise<void> {
  if (!isDesktop()) {
    window.open(url, "_blank", "noopener,noreferrer");
    return;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("open_external_url", { url });
  } catch (err) {
    console.error("openExternal failed:", err);
    // Last-resort fallback so a broken IPC doesn't strand the user
    // mid-checkout. The Tauri webview will show its "external link"
    // confirmation dialog on this path.
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

/** Listener signature for deep-link events. */
export type DeepLinkPayload = { url: string };
export type DeepLinkHandler = (payload: DeepLinkPayload) => void;

/**
 * Subscribe to `pi-typst-test://` and `digi-setu://` deep-link URLs
 * the OS hands us when the user finishes an OAuth/Stripe flow in
 * their browser. Returns an unsubscribe function.
 *
 * In web mode this is a no-op — the equivalent flow uses an iframe
 * postMessage relay, which lives in `web/frontend/src/lib/auth.ts`
 * (not this file).
 */
export async function onDeepLink(
  handler: DeepLinkHandler,
): Promise<() => void> {
  if (!isDesktop()) return () => {};
  try {
    const { listen } = await import("@tauri-apps/api/event");
    const unlisten = await listen<DeepLinkPayload>("deep-link", (event) => {
      handler(event.payload);
    });
    return unlisten;
  } catch (err) {
    console.error("onDeepLink subscribe failed:", err);
    return () => {};
  }
}

/**
 * Wait for the sidecar to publish `backend-ready`. Tauri emits this
 * after the FastAPI process passes its /healthz probe. Resolves
 * immediately if we're already past that point (e.g. on a hot reload).
 *
 * In web mode this resolves on the next microtask.
 */
export async function waitForBackend(): Promise<number | null> {
  if (!isDesktop()) return Promise.resolve(null);
  const port = await getBackendPort();
  if (port) return port;
  try {
    const { listen } = await import("@tauri-apps/api/event");
    return await new Promise<number>((resolve) => {
      let unlisten: (() => void) | undefined;
      listen<number>("backend-ready", (event) => {
        if (unlisten) unlisten();
        resolve(event.payload);
      }).then((u) => {
        unlisten = u;
      });
    });
  } catch (err) {
    console.error("waitForBackend failed:", err);
    return null;
  }
}
