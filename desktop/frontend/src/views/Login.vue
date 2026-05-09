<!--
  Login / Welcome.

  Three states this view handles, in priority order:

  1. requiresSetup (desktop only, no Clerk session AND no BYOK keys):
     This is the user's first-launch experience. We render a Welcome
     screen with a single Sign-in card. BYOK is intentionally NOT
     surfaced here as a UI option — power users discover it through
     the docs (drop a key into ~/.digi-setu/.env, the sidecar
     watcher picks it up live and the Welcome screen no longer
     shows). Surfacing BYOK on the Welcome screen confused first-
     run users into thinking the app required them to provide AI
     credentials before they could try it.

  2. authRequired (web prod or desktop with Clerk configured but
     not yet signed in): bounce sign-in out to the system browser.
     The Tauri webview can't host Clerk directly (anti-phishing,
     passkeys, autofill). After Clerk authenticates, the production
     web app's `/desktop/sign-in` page redirects to a digi-setu://
     deep link, which the deep-link bridge installed in main.ts
     picks up and exchanges for a session.

  3. !authRequired (dev mode, no Clerk configured): land on the
     picker — every request resolves to user_id="dev" anyway.

  All user-facing copy lives in `src/locales/en.json#login`. Adding a
  language is a matter of duplicating that file.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";

import AppFooter from "../components/AppFooter.vue";
import { isDesktop } from "../lib/native-bridge";
import { startDesktopSignIn } from "../lib/desktop-auth";
import { useConfigStore } from "../stores/config";

// Desktop frontend is intentionally Clerk-free. Sign-in always
// happens in the system browser (anti-phishing + passkeys); the
// session_id comes back via deep-link, and the sidecar mints the
// JWT server-side. So this view never imports @clerk/vue and never
// renders <SignIn />. See `lib/desktop-auth.ts` and
// `routes/desktop_auth.py` for the full handshake.

const route = useRoute();
const router = useRouter();
const cfg = useConfigStore();

type Status = "idle" | "loading" | "waiting-browser" | "error";
const status = ref<Status>("idle");

const redirectUrl = computed(() => {
  const next = route.query.next;
  return typeof next === "string" && next.startsWith("/") ? next : "/";
});

const showWelcome = computed(
  () => isDesktop() && (cfg.requiresSetup || (!cfg.authRequired && !cfg.byokMode)),
);

async function startSignIn(): Promise<void> {
  status.value = "waiting-browser";
  try {
    await startDesktopSignIn();
  } catch (exc) {
    console.error("[login] startDesktopSignIn failed", exc);
    status.value = "error";
  }
}

async function handoff(): Promise<void> {
  // Welcome / setup screen owns its own state — don't auto-redirect.
  if (showWelcome.value) return;
  // Auth disabled (BYOK or dev). The router's beforeEach already
  // bounced /login to "/" in this case, but we land here defensively.
  if (!cfg.authRequired) {
    void router.replace(redirectUrl.value);
    return;
  }
  // authRequired without a session → bounce to the system browser.
  // Same path on desktop AND web prod (web mode also redirects to
  // the hosted /desktop/sign-in bounce so the auth path is uniform).
  void startSignIn();
}

onMounted(() => {
  void handoff();
});
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <!-- ── Welcome (desktop, no Clerk session AND no BYOK keys) ── -->
      <section
        v-if="showWelcome"
        class="w-full max-w-md"
        aria-labelledby="welcome-title"
      >
        <div class="mb-8 text-center">
          <h1
            id="welcome-title"
            class="text-h1 font-semibold tracking-tight text-foreground"
          >
            {{ $t("login.welcomeTitle") }}
          </h1>
          <p class="mt-2 text-lead text-muted-foreground">
            {{ $t("login.welcomeSubtitle") }}
          </p>
        </div>

        <article
          class="flex flex-col rounded-lg border border-border bg-card p-6 text-foreground"
        >
          <h2 class="text-h2 font-semibold tracking-tight">
            {{ $t("login.signIn.title") }}
          </h2>
          <p class="mt-2 text-body text-muted-foreground">
            {{ $t("login.signIn.blurb") }}
          </p>
          <button
            type="button"
            class="mt-5 inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-body font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60"
            :disabled="status === 'waiting-browser'"
            @click="startSignIn"
          >
            <span
              v-if="status === 'waiting-browser'"
              class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-foreground/40 border-t-primary-foreground"
              aria-hidden="true"
            />
            {{
              status === "waiting-browser"
                ? $t("login.signIn.ctaWaiting")
                : $t("login.signIn.cta")
            }}
          </button>
          <button
            v-if="status === 'waiting-browser'"
            type="button"
            class="mt-2 text-caption text-muted-foreground underline-offset-2 hover:underline"
            @click="startSignIn"
          >
            {{ $t("login.signIn.reopen") }}
          </button>
        </article>

        <!-- Escape hatch: 'Continue without signing in' takes the user
             straight to the picker. They can open folders, browse, etc.;
             the chat surface itself prompts for sign-in at message-send
             time. This is what makes 'Open folder' actually feel
             ungated — the Welcome screen is a friendly default, not a
             blocking wall. -->
        <div class="mt-4 text-center">
          <RouterLink
            to="/"
            class="text-body text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >{{ $t("login.continueAsGuest") }}</RouterLink>
          <p class="mt-1 text-caption text-muted-foreground">
            {{ $t("login.continueAsGuestHint") }}
          </p>
        </div>

        <p
          v-if="status === 'error'"
          class="mt-6 text-center text-body text-destructive"
        >
          {{ $t("login.error") }}
          <span class="text-muted-foreground">— {{ $t("login.errorDetail") }}</span>
        </p>
      </section>

      <!-- ── Web prod or desktop with Clerk: bounce / redirect spinner ── -->
      <div
        v-else-if="cfg.authRequired"
        class="flex flex-col items-center gap-3 text-lead text-muted-foreground"
      >
        <template v-if="status === 'error'">
          <p class="font-medium text-destructive">{{ $t("login.error") }}</p>
          <p class="text-body">{{ $t("login.errorDetail") }}</p>
          <button
            type="button"
            class="mt-2 rounded-md border border-border bg-card px-3 py-1.5 text-body font-medium text-foreground hover:border-primary/50"
            @click="handoff"
          >
            {{ $t("common.tryAgain") }}
          </button>
        </template>
        <template v-else>
          <span
            class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"
            aria-hidden="true"
          />
          <p>
            <template v-if="status === 'waiting-browser'">
              {{ $t("login.signIn.ctaWaiting") }}
            </template>
            <template v-else>{{ $t("login.loading") }}</template>
          </p>
          <button
            v-if="status === 'waiting-browser'"
            type="button"
            class="mt-2 rounded-md border border-border bg-card px-3 py-1.5 text-body font-medium text-foreground hover:border-primary/50"
            @click="handoff"
          >
            {{ $t("login.signIn.reopen") }}
          </button>
        </template>
      </div>

      <!-- ── Dev mode (no Clerk, no BYOK): just continue ── -->
      <div
        v-else
        class="w-full max-w-md rounded-lg border border-border bg-card p-6 text-lead text-foreground"
      >
        <p class="mb-2 font-medium">{{ $t("login.alreadySignedIn") }}</p>
        <RouterLink
          :to="redirectUrl"
          class="block w-full rounded-md bg-primary px-4 py-2 text-center text-lead font-semibold text-primary-foreground hover:opacity-90"
        >
          {{ $t("nav.sessions") }}
        </RouterLink>
      </div>
    </main>

    <AppFooter />
  </div>
</template>
