import { createPinia } from "pinia";
import { createApp } from "vue";
import { addCollection } from "@iconify/vue";
import materialIconTheme from "@iconify-json/material-icon-theme/icons.json";
import codicon from "@iconify-json/codicon/icons.json";
import { clerkPlugin, getToken } from "@clerk/vue";

import App from "./App.vue";
import { router } from "./router";
import { setApiBase, setTokenResolver } from "./api/client";
import { installDeepLinkBridge } from "./lib/desktop-auth";
import { installMenuBridge } from "./lib/menu-bridge";
import { isDesktop, waitForBackend } from "./lib/native-bridge";
import { useConfigStore } from "./stores/config";
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
 *  1. Build the Vue app + Pinia + router.
 *  2. Fetch /api/config so we know whether Clerk should be installed
 *     and which publishable key to pass it.
 *  3. Conditionally install Clerk + register the token resolver so
 *     api/client.ts can sign every request.
 *  4. Mount.
 *
 * Why we delay mount until after step 3: if we mount first, the
 * router beforeEach guard in router.ts may run before Clerk is ready
 * and bounce the user to /login on the very first paint. Doing the
 * config fetch up front (it's a single tiny GET) keeps the boot path
 * deterministic.
 *
 * Why `getToken()` from `@clerk/shared` and not the `useAuth` composable:
 * composables rely on Vue's `inject()` and only work inside a setup
 * function. The bare `getToken()` walks the global Clerk singleton and
 * is the documented way to grab a token from non-component code
 * (interceptors, websocket bridges, …).
 */
async function boot(): Promise<void> {
  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  app.use(router);

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

    // Native menu bar (File / Edit / View / Window / Help) is built in
    // src-tauri/src/menu.rs. The bridge listens for Tauri `menu:*`
    // events and translates them into router pushes / store calls so
    // the same menu works no matter which view the user is in.
    void installMenuBridge(router);

    // Wire the pi-typst-test:// deep-link handler. Auth + billing
    // callbacks from the system browser come through here.
    void installDeepLinkBridge({
      onAuthSuccess: async () => {
        // Refresh config + reload so the Clerk plugin picks up the
        // newly-stamped session and the router's beforeEach guard
        // lets the user past /login.
        try {
          await cfg.refresh();
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
  await cfg.refresh();

  if (cfg.authRequired && cfg.clerkPublishableKey) {
    app.use(clerkPlugin, {
      publishableKey: cfg.clerkPublishableKey,
      // Default Clerk routing — works fine with vue-router history mode.
      // We override the after-sign-in URL so users land back on the
      // picker (which then resolves their workspaces). No `appearance`
      // override on purpose: per-user instruction we ship Clerk's own
      // styling unmodified, both inside SignIn and inside UserButton.
      signInForceRedirectUrl: "/",
      signUpForceRedirectUrl: "/",
    });

    setTokenResolver(async () => {
      try {
        return await getToken();
      } catch (exc) {
        console.warn("[auth] getToken failed", exc);
        return null;
      }
    });
  }

  app.mount("#app");
}

void boot();
