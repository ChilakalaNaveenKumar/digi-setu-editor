import { createPinia } from "pinia";
import { createApp } from "vue";
import { addCollection } from "@iconify/vue";
import materialIconTheme from "@iconify-json/material-icon-theme/icons.json";
import codicon from "@iconify-json/codicon/icons.json";
import { clerkPlugin, getToken } from "@clerk/vue";

import App from "./App.vue";
import { router } from "./router";
import { setTokenResolver } from "./api/client";
import { useConfigStore } from "./stores/config";
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
  // Apply persisted locale BEFORE creating the app so the very first
  // paint never flashes English while we resolve the user's choice.
  bootLocale();

  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  app.use(router);
  app.use(i18n);

  const cfg = useConfigStore();
  await cfg.refresh();

  if (cfg.authRequired && cfg.clerkPublishableKey) {
    app.use(clerkPlugin, {
      publishableKey: cfg.clerkPublishableKey,
      // After sign-in we want users to land on the picker (root) by
      // default — but only when no per-call URL was provided. We use
      // the *fallback* form (not *force*) so flows that pass an
      // explicit `forceRedirectUrl` (e.g. the desktop bounce page at
      // /desktop/sign-in) keep control of where to land. Using
      // `signInForceRedirectUrl: "/"` here would unconditionally
      // override every sign-in's redirect target and silently break
      // the desktop handoff loop.
      //
      // No `appearance` override on purpose: per user instruction we
      // ship Clerk's default styling unmodified for SignIn and
      // UserButton.
      signInFallbackRedirectUrl: "/",
      signUpFallbackRedirectUrl: "/",
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
