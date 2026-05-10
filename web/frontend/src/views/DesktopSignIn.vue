<!--
  Desktop sign-in bounce page.

  Loaded at https://digi-setu.com/desktop/sign-in?state=<csrf>&return=<deeplink>
  by the Tauri shell when the user clicks "Sign in" on the desktop's
  Welcome screen. We don't render this URL inside the desktop webview
  itself — the whole point of the bounce is to use the user's normal
  browser, with their saved passwords / passkeys / autofill / etc.

  Lifecycle:
    1. Mount → validate `state` and `return` URL params. We accept
       two return-URL flavours and refuse all others:
         a. `digi-setu://…`              — production deep-link path.
         b. `http://127.0.0.1:<port>/…`  — desktop sidecar localhost
            callback. The desktop generates a random sidecar port
            bound only to loopback, so this URL is only addressable
            from the user's own machine. Used in dev (where deep
            links don't work in `tauri dev` on macOS) and any prod
            install where deep-link delivery isn't reliable.
       Other schemes / hosts are refused outright so we can't be
       used as an open redirector to phish credentials elsewhere.
    2. Wait for ClerkJS to finish loading (useUser().isLoaded).
    3. If signed in → mint a handoff session and redirect to the
       return URL (step 5).
    4. If signed out → render Clerk's inline <SignIn /> component
       directly on the page. After the user authenticates, ClerkJS
       flips `isSignedIn` in place (no full-page redirect needed),
       which fires the watcher and runs step 5.
    5. Call POST /api/auth/desktop-mint-handoff to mint a fresh
       Clerk session, then top-level navigate to
       `<return>?session_id=<id>&state=<csrf>`. For the deep-link
       form the OS hands the URL to the running Tauri shell. For
       the localhost form the browser issues a GET to the desktop
       sidecar's `/api/auth/desktop-callback` endpoint, which
       refreshes its JWT cache and renders a "you can close this
       tab" page. Either way the desktop frontend's window-focus
       listener picks up the new auth state when the user
       switches back.

  Why inline <SignIn /> instead of clerk.redirectToSignIn():
    The redirect path is racy — when ClerkJS hasn't yet validated
    the cookie, `clerk.session` reads as null and we wrongly try to
    redirect; Clerk's redirectToSignIn then no-ops because the user
    is actually signed in, leaving the page stuck on a spinner with
    no error and no redirect. The inline component sidesteps the
    whole race: it watches Clerk's loaded state itself and never
    leaves this page, so as soon as auth completes we mint.

  CSRF: the `state` param flows through unmodified. For the deep-
  link form the desktop's deep-link handler cross-checks it; for
  the localhost form the desktop sidecar pre-registered the state
  via `/api/auth/desktop-prepare-state` and refuses any callback
  whose state we didn't issue. Without this an attacker could
  fabricate a callback URL to log a victim into their own Clerk
  account.

  Open-redirect protection: we ONLY accept return URLs whose scheme
  is `digi-setu:` OR HTTP URLs pointing at loopback (127.0.0.1 /
  ::1 / localhost). Anything else (https://evil.com, etc.) aborts.
-->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { SignIn, useUser } from "@clerk/vue";

import { apiPost } from "../api/client";
import { useConfigStore } from "../stores/config";

const route = useRoute();
const cfg = useConfigStore();
const { isLoaded, isSignedIn } = useUser();

type Status =
  | "loading"
  | "signing-in"
  | "minting"
  | "handing-off"
  | "error";
const status = ref<Status>("loading");

const stateToken = computed(() => {
  const v = route.query.state;
  return typeof v === "string" ? v : "";
});

const returnUrl = computed(() => {
  const v = route.query.return;
  return typeof v === "string" ? v : "";
});

const returnIsValid = computed(() => {
  if (!returnUrl.value) return false;
  try {
    const parsed = new URL(returnUrl.value);
    if (parsed.protocol === "digi-setu:") return true;
    // Loopback-only HTTP callback (the desktop sidecar). We refuse
    // any non-loopback host even on http:// so this page can't be
    // used as an open redirector. The desktop sidecar binds only
    // to 127.0.0.1 and exposes the random port to its own SPA, so
    // a loopback URL here is only addressable from the same machine.
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      const host = parsed.hostname.toLowerCase();
      return host === "127.0.0.1" || host === "localhost" || host === "[::1]";
    }
    return false;
  } catch {
    return false;
  }
});

async function mintAndRedirect(): Promise<void> {
  status.value = "minting";
  let sessionId = "";
  try {
    const result = await apiPost<{ ok: true; session_id: string; mode: string }>(
      "/api/auth/desktop-mint-handoff",
      {},
    );
    sessionId = result.session_id || "";
  } catch (exc) {
    console.error("[desktop-sign-in] mint failed", exc);
    status.value = "error";
    return;
  }
  if (!sessionId) {
    status.value = "error";
    return;
  }
  status.value = "handing-off";
  const url = new URL(returnUrl.value);
  url.searchParams.set("session_id", sessionId);
  url.searchParams.set("state", stateToken.value);
  // Top-level navigation. For digi-setu:// schemes the OS hands the
  // URL to the running Tauri shell. For http://127.0.0.1:<port>/…
  // URLs the browser issues a GET to the desktop sidecar's
  // /desktop-callback endpoint, which renders its own "you can
  // close this tab" page (so we don't even need our own
  // hand-off message in that case).
  window.location.href = url.toString();
}

// Drive status off Clerk's auth state. Three transitions:
//   not loaded         → "loading" spinner
//   loaded, signed out → "signing-in" (render inline <SignIn />)
//   loaded, signed in  → mintAndRedirect() (one-shot, then "handing-off")
watch(
  [() => isLoaded.value, () => isSignedIn.value],
  ([loaded, signedIn]) => {
    if (!returnIsValid.value || !stateToken.value) {
      status.value = "error";
      return;
    }
    if (!cfg.authRequired) {
      // Dev mode — backend stamps user_id="dev"; mint returns a
      // synthetic id and the bounce still completes end-to-end.
      if (status.value === "loading") void mintAndRedirect();
      return;
    }
    if (!loaded) {
      status.value = "loading";
      return;
    }
    if (signedIn) {
      // Only fire mint once. Once we've kicked it off, status
      // stays in minting/handing-off; the watcher exits without
      // re-firing.
      if (status.value === "loading" || status.value === "signing-in") {
        void mintAndRedirect();
      }
      return;
    }
    status.value = "signing-in";
  },
  { immediate: true },
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <div
        v-if="!returnIsValid"
        class="w-full max-w-md rounded-lg border border-destructive/50 bg-card p-6 text-lead text-foreground"
      >
        <h1 class="mb-2 text-h2 font-semibold tracking-tight">
          Invalid sign-in link
        </h1>
        <p class="text-body text-muted-foreground">
          This sign-in URL didn't come from the Digi Setu desktop app.
          Please open Digi Setu and click <em>Sign in</em> there to
          start a new session.
        </p>
      </div>

      <div
        v-else-if="status === 'error'"
        class="w-full max-w-md rounded-lg border border-destructive/50 bg-card p-6 text-lead text-foreground"
      >
        <h1 class="mb-2 text-h2 font-semibold tracking-tight">
          Couldn't complete sign-in
        </h1>
        <p class="text-body text-muted-foreground">
          Something went wrong. Please return to the Digi Setu app
          and try again.
        </p>
        <button
          type="button"
          class="mt-4 rounded-md border border-border bg-background px-3 py-1.5 text-body font-medium text-foreground hover:border-primary/50"
          @click="status = 'loading'"
        >
          Try again
        </button>
      </div>

      <div
        v-else-if="status === 'signing-in'"
        class="flex w-full max-w-md flex-col items-center gap-4"
      >
        <div class="text-center">
          <h1 class="text-h2 font-semibold tracking-tight text-foreground">
            Sign in to continue
          </h1>
          <p class="mt-1 text-body text-muted-foreground">
            We'll send you back to the Digi Setu desktop app once
            you're signed in.
          </p>
        </div>
        <SignIn :force-redirect-url="$route.fullPath" />
      </div>

      <div
        v-else
        class="flex flex-col items-center gap-3 text-lead text-muted-foreground"
      >
        <span
          class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"
          aria-hidden="true"
        />
        <p>
          <template v-if="status === 'minting'">
            Preparing your desktop session…
          </template>
          <template v-else-if="status === 'handing-off'">
            Returning you to Digi Setu…
          </template>
          <template v-else>Loading…</template>
        </p>
      </div>
    </main>
  </div>
</template>
