<!--
  Login — flash redirector to Clerk's hosted sign-in page.

  Per product decision we don't render Clerk's <SignIn /> widget
  inline. The hosted page (e.g. https://certain-sunfish-59.accounts.dev
  /sign-in for dev, https://accounts.<your-domain>.com/sign-in for prod)
  carries Clerk's full styling, security headers, and branding — and we
  want the user to experience that exact page rather than an embedded
  copy.

  Flow:
    1. Router guard bounces unauthenticated users to /login?next=…
    2. This view mounts, waits for Clerk to load.
    3. If a session is already present (e.g. user opened /login
       directly while signed in), we just push to `next`.
    4. Otherwise we call clerk.redirectToSignIn({ redirectUrl }) which
       full-page-navigates to Clerk's hosted sign-in. After successful
       auth Clerk's `signInForceRedirectUrl` (configured in main.ts)
       brings them back to "/", and the picker resolves their session.

  Dev-mode fallback (auth_required=false): the backend has no Clerk
  configured, so `redirectToSignIn` doesn't exist. We render a notice
  and a "continue to picker" button instead.
-->
<script setup lang="ts">
import { computed, onMounted, watch, ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { useClerk, useAuth } from "@clerk/vue";

import { useConfigStore } from "../stores/config";

const route = useRoute();
const router = useRouter();
const cfg = useConfigStore();
const clerk = useClerk();
// `useAuth().isLoaded` flips to `true` only AFTER clerk-js has
// hydrated the session from cookies / fragment. Without this we'd
// (a) decide "no session" while Clerk is still loading and
// (b) immediately bounce back to Clerk's hosted page → which then
// returns to /, which the router guard ALSO sees as signed-out, and
// we end up in an infinite redirect loop. Symptom: user signs up,
// Clerk hosted page completes, but the SPA gets stuck on
// "Redirecting to Clerk…" until they hit F5.
const { isLoaded, isSignedIn } = useAuth();

const status = ref<"loading" | "redirecting" | "error">("loading");
const errMsg = ref("");

const redirectUrl = computed(() => {
  const next = route.query.next;
  if (typeof next === "string" && next.startsWith("/")) return next;
  // Default landing after sign-in: /start auto-resolves the user's
  // most recent chat (or mints one for first-time accounts) and
  // replaces itself with /chat/<sid>?wsid=<wsid>. That cuts the
  // post-sign-in click depth from "land on / → click 'Continue' →
  // land on /sessions → click a chat" down to zero.
  return "/start";
});

async function handoff(): Promise<void> {
  if (!cfg.authRequired) return;

  const c = clerk.value;
  if (!c) return;
  // Wait for clerk-js to finish hydrating before deciding whether to
  // redirect. `isLoaded` is the canonical "hydration done" signal.
  if (!isLoaded.value) return;

  // Hydrated AND signed in (e.g. user opened /login directly while
  // already authenticated, OR the page just came back from Clerk's
  // hosted sign-in) → land on the requested URL.
  if (isSignedIn.value || c.session) {
    await router.replace(redirectUrl.value);
    return;
  }

  status.value = "redirecting";
  try {
    // Full-page navigate to Clerk's hosted sign-in page. After auth
    // Clerk redirects back to `redirectUrl` (origin-absolute so it
    // crosses the accounts.dev → app boundary cleanly).
    await c.redirectToSignIn({
      signInForceRedirectUrl: window.location.origin + redirectUrl.value,
    });
  } catch (exc) {
    console.error("[login] redirectToSignIn failed", exc);
    errMsg.value = exc instanceof Error ? exc.message : String(exc);
    status.value = "error";
  }
}

onMounted(() => {
  void handoff();
});

// Re-evaluate every time clerk-js' state changes (instance becomes
// available OR isLoaded flips OR isSignedIn flips). The previous
// implementation only watched `clerk.value` and fired before the
// session cookie was hydrated, racing into a redirect loop.
watch(
  [() => clerk.value, () => isLoaded.value, () => isSignedIn.value],
  () => {
    void handoff();
  },
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <div
        v-if="cfg.authRequired"
        class="flex flex-col items-center gap-3 text-lead text-muted-foreground"
      >
        <template v-if="status === 'error'">
          <p class="font-medium text-destructive">
            Couldn't redirect to Clerk.
          </p>
          <p class="font-mono text-caption">{{ errMsg }}</p>
          <button
            type="button"
            class="mt-2 rounded-md border border-border bg-card px-3 py-1.5 text-body font-medium text-foreground hover:border-primary/50"
            @click="handoff"
          >Try again</button>
        </template>
        <template v-else>
          <span
            class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"
            aria-hidden="true"
          />
          <p>
            <template v-if="status === 'redirecting'">
              Redirecting to Clerk…
            </template>
            <template v-else>Loading…</template>
          </p>
        </template>
      </div>

      <div
        v-else
        class="w-full max-w-md rounded-lg border border-border bg-card p-6 text-lead text-foreground"
      >
        <p class="mb-2 font-medium">Auth is disabled on this server.</p>
        <p class="mb-4 text-muted-foreground">
          The backend is running without
          <code class="font-mono text-caption">CLERK_SECRET_KEY</code>, so
          every request resolves to the synthetic
          <code class="font-mono text-caption">dev</code> user. Set the
          <code class="font-mono text-caption">CLERK_*</code> env vars in
          <code class="font-mono text-caption">web/backend/.env</code> and
          restart uvicorn to enable real sign-in.
        </p>
        <RouterLink
          :to="redirectUrl"
          class="block w-full rounded-md bg-primary px-4 py-2 text-center text-lead font-semibold text-primary-foreground hover:opacity-90"
        >
          Continue to picker
        </RouterLink>
      </div>
    </main>
  </div>
</template>
