import { createPinia } from "pinia";
import { createApp } from "vue";
import { addCollection } from "@iconify/vue";
import materialIconTheme from "@iconify-json/material-icon-theme/icons.json";
import codicon from "@iconify-json/codicon/icons.json";

import App from "./App.vue";
import { router } from "./router";
import { setApiBase } from "./api/client";
import {
  installDeepLinkBridge,
  restoreDesktopSession,
} from "./lib/desktop-auth";
import { installMenuBridge } from "./lib/menu-bridge";
import {
  isDesktop,
  onBackendLifecycle,
  waitForBackend,
} from "./lib/native-bridge";
import { useConfigStore } from "./stores/config";
import { useAuthStore } from "./stores/auth";
import { i18n, bootLocale } from "./i18n";
import "./app.css";

// Pre-register Iconify collections so file/folder/action icons resolve
// instantly without an API round-trip. Material Icon Theme is the
// standard "VS Code Material Icon Theme" pack (per-language colours);
// codicon is Microsoft's official VS Code action-icon set (new file,
// refresh, collapse-all, etc.).
addCollection(materialIconTheme as never);
addCollection(codicon as never);

// Apply dark mode + chosen palette globally. To swap palette: change the
// class name below to "theme-linear" / "theme-cursor" / "theme-vercel" /
// "theme-stripe" — each is defined in app.css.
document.documentElement.classList.add("dark", "theme-notion");

/**
 * Boot order:
 *  1. Apply persisted locale.
 *  2. Build the Vue app + Pinia + router + i18n.
 *  3. Wait for the local sidecar's randomized port and pin every
 *     fetch() to it (desktop only — web mode uses same-origin paths).
 *  4. Restore SSO from the OS keychain (silent /desktop-refresh).
 *  5. Fetch /api/config so the router's beforeEach guard sees the
 *     correct `requires_setup` / `auth_required` flags before the
 *     first navigation.
 *  6. Fetch /api/auth/whoami so BrandHeader can paint the avatar /
 *     sign-in CTA on first frame without a flash.
 *  7. Mount.
 *
 * The desktop frontend is intentionally Clerk-free. Sign-in always
 * happens in the system browser via the web fork's
 * /desktop/sign-in bounce page. The sidecar (Python) is the only
 * place that talks to Clerk's SDK. Loopback between the SPA and the
 * sidecar doesn't need a bearer token (`AUTH_REQUIRED=false` in the
 * desktop sidecar by default).
 */
async function boot(): Promise<void> {
  // Apply persisted locale BEFORE creating the app so the very first
  // paint never flashes English while we resolve the user's choice.
  bootLocale();

  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  app.use(router);
  app.use(i18n);

  // Desktop bridge: discover the sidecar's randomized port and pin
  // every API request to `http://127.0.0.1:<port>`. In web mode this
  // resolves to null and the api client uses relative paths, exactly
  // as before. The wait is bounded by the sidecar health-check
  // timeout in src-tauri/src/sidecar.rs; if it returns null we let
  // the SPA boot anyway and surface the connection error in the UI.
  if (isDesktop()) {
    const port = await waitForBackend();
    if (port) {
      setApiBase(`http://127.0.0.1:${port}`);
    } else {
      console.error(
        "[boot] Desktop sidecar did not announce a port; API calls will fail until it does.",
      );
    }

    // Suppress page-reload shortcuts inside the Tauri webview. A
    // native desktop app should NOT behave like a browser tab — Cmd+R
    // / Ctrl+R / F5 would tear down all in-flight chats, drop the
    // websocket, and replay the boot sequence from scratch (which
    // confused the user during dev). Devtools / hard-refresh during
    // engineering can still be done by restarting `tauri dev`.
    window.addEventListener(
      "keydown",
      (e) => {
        const isReloadCombo =
          e.key === "F5" ||
          ((e.metaKey || e.ctrlKey) && (e.key === "r" || e.key === "R"));
        if (isReloadCombo) {
          e.preventDefault();
          e.stopPropagation();
        }
      },
      { capture: true },
    );

    // Suppress the macOS WebKit / Windows WebView2 native right-click
    // context menu ("Reload", "Inspect Element", "Back/Forward",
    // "Search With Google…"). These items don't make sense for a
    // packaged native app — they leak the underlying browser engine
    // to the user, allow them to reload the SPA mid-stream (same
    // problem as the reload-combo above), and make the product look
    // like a wrapped webpage instead of a desktop app. Real text
    // selection (Cmd+C, double-click, drag-select) and form-field
    // context menus inside <input>/<textarea> still work — those go
    // through the OS's text-services menu, not the webview's
    // navigation menu.
    window.addEventListener(
      "contextmenu",
      (e) => {
        // Allow the native menu inside text inputs / textareas /
        // contenteditable so users can still cut/copy/paste with the
        // mouse on form fields.
        const target = e.target as HTMLElement | null;
        if (target) {
          const tag = target.tagName;
          if (
            tag === "INPUT" ||
            tag === "TEXTAREA" ||
            target.isContentEditable
          ) {
            return;
          }
        }
        e.preventDefault();
      },
      { capture: true },
    );

    // Native menu bar (File / Edit / View / Window / Help) is built in
    // src-tauri/src/menu.rs. The bridge listens for Tauri `menu:*`
    // events and translates them into router pushes / store calls so
    // the same menu works no matter which view the user is in.
    void installMenuBridge(router);

    // Sidecar self-heal: subscribe to the watchdog's lifecycle events
    // BEFORE the SPA opens any WebSockets so the very first crash
    // is observable. The handler:
    //   * On `restarted`, rebinds the API base to the new port and
    //     forces the chat bridge (if any) to reconnect against it.
    //   * On `restarting` / `restartFailed`, only logs — the SPA's
    //     existing connection-error banner already covers the user-
    //     visible state, no need for a duplicate toast.
    // See desktop/src-tauri/src/sidecar.rs#watchdog_loop for the
    // backoff schedule.
    void onBackendLifecycle((event) => {
      if (event.kind === "restarted") {
        console.info(
          `[boot] sidecar respawned on port ${event.port} — rebinding API base`,
        );
        setApiBase(`http://127.0.0.1:${event.port}`);
        // Re-anchor any open chat WebSocket against the new port.
        // We import on demand so the listener costs nothing on web.
        void import("./stores/chat").then(({ useChatStore }) => {
          try {
            useChatStore().reanchorBridge();
          } catch (exc) {
            console.warn("[boot] reanchorBridge failed", exc);
          }
        });
      } else if (event.kind === "restarting") {
        console.warn(
          `[boot] sidecar exited (code ${event.previousExitCode}); watchdog respawning`,
        );
      } else {
        console.warn(`[boot] sidecar respawn attempt failed: ${event.error}`);
      }
    });

    // Wire the digi-setu:// deep-link handler. Auth + billing
    // callbacks from the system browser come through here.
    void installDeepLinkBridge({
      onAuthSuccess: async () => {
        // Re-fetch config + whoami so the router gate flips
        // requires_setup → false and BrandHeader paints the user's
        // avatar without a full page reload.
        try {
          await cfg.refresh();
          await auth.refresh();
        } catch {}
        window.location.replace("/");
      },
      onAuthFailure: (reason) => {
        console.error("[desktop-auth] failed:", reason);
      },
      onBillingSuccess: async () => {
        try {
          await cfg.refresh();
        } catch {}
      },
      onBillingCancel: () => {
        console.info("[desktop-auth] checkout cancelled");
      },
    });
  }

  const cfg = useConfigStore();
  const auth = useAuthStore();

  // Persistent SSO: try the OS-keychain → /api/auth/desktop-refresh
  // path BEFORE the first /api/config call so the response already
  // reflects the restored session (i.e. requires_setup goes false
  // again without a flash of the Welcome screen). This is the
  // "Cursor stays signed in" UX — sign in once, the keychain holds
  // the long-lived session id, fresh JWTs are minted on every
  // launch silently. Web mode no-ops this.
  await restoreDesktopSession();

  await cfg.refresh();
  // /whoami is a single GET against the local sidecar. Awaiting it
  // here (in parallel with the cfg.refresh above would be even
  // better but the latency is sub-ms on loopback) means the very
  // first paint of BrandHeader already knows the user's email /
  // avatar — no spinner, no flicker.
  await auth.refresh();

  app.mount("#app");
}

void boot();
