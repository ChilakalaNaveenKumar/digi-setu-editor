<!--
  Home — public landing page (mounted at /).

  Replaces the old behaviour where `/` rendered the session/folder
  picker, which gave the app no real "home" surface and left first-
  time visitors with a list of empty workspaces and zero context for
  what Digi Setu is.

  Layout (top → bottom):
    1. Hero       — value prop + primary CTA
    2. Pillars    — three cards explaining what we do
    3. Plans      — compact teaser of the public pricing tiers, links
                    to the full /pricing page for details + checkout
    4. Closing    — "built on top of pi" credit + secondary CTAs
    5. Footer     — fixed © 2025 (shared component)

  Signed-in users see the same hero with the CTA flipped to "Continue
  to your workspaces" → /sessions. The marketing copy stays visible
  so the landing is a stable shareable URL, not a stealth redirect.

  The global header is mounted in App.vue, NOT here.
-->
<script setup lang="ts">
import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useRouter, RouterLink } from "vue-router";
import { Icon } from "@iconify/vue";
import { Show as ClerkShow } from "@clerk/vue";

import { useBillingStore } from "../stores/billing";
import { useConfigStore } from "../stores/config";

const router = useRouter();
const cfg = useConfigStore();
const billing = useBillingStore();
const { plans } = storeToRefs(billing);

onMounted(async () => {
  if (!plans.value.length) await billing.refreshStatus();
});

// In dev mode (auth_required=false) the user is treated as signed-in
// because the backend resolves every request to the synthetic `dev`
// user. We use this to decide which CTA to render before Clerk has
// loaded — auth_required toggles the Clerk gate, the ClerkShow
// blocks below pick the actual variant when auth IS required.
const authOff = computed(() => !cfg.authRequired);

function goToSessions(): void {
  router.push({ name: "sessions" });
}

function goToLogin(): void {
  router.push({ name: "login" });
}

const PILLARS: Array<{ icon: string; title: string; body: string }> = [
  {
    icon: "codicon:file-pdf",
    title: "Production-grade Typst",
    body: "Reports, papers, slides, brochures — Digi Setu writes Typst and renders to PDF in the same chat turn, with a real preview alongside the editor.",
  },
  {
    icon: "codicon:terminal",
    title: "A real sandbox per chat",
    body: "Every conversation gets its own isolated workspace with files, a terminal, and a snapshot history. Revert any turn in one click.",
  },
  {
    icon: "codicon:shield",
    title: "Bring your own keys",
    body: "Drop an Anthropic, OpenAI or Google key into your account and the app routes straight to your provider — billed by them, not us.",
  },
];
</script>

<template>
  <div class="flex min-h-0 w-full flex-1 flex-col bg-background text-foreground">
    <main class="flex-1">
      <!-- HERO -->
      <section class="mx-auto w-full max-w-5xl px-6 pt-16 pb-20 md:pt-24 md:pb-28">
        <div class="text-center">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-caption text-muted-foreground"
          >
            <span class="inline-block h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
            Desktop &amp; web · open beta
          </span>
          <h1
            class="mx-auto mt-5 max-w-3xl text-h1 font-semibold leading-tight tracking-tight text-foreground"
            style="font-size: clamp(28px, 5vw, 44px); line-height: 1.1;"
          >
            An AI typesetter that writes documents
            <span class="text-primary">the way you think</span>.
          </h1>
          <p
            class="mx-auto mt-5 max-w-2xl text-lead leading-relaxed text-muted-foreground"
            style="font-size: 16px; line-height: 1.6;"
          >
            Digi Setu turns plain English into polished Typst documents,
            slides and PDFs — inside a sandboxed workspace with a real
            editor, terminal, and live preview. Pay once a month for the
            actual model + infra cost, or bring your own AI keys.
          </p>
          <div class="mt-8 flex flex-wrap items-center justify-center gap-3">
            <!-- Auth-off: single CTA goes straight to the picker. -->
            <button
              v-if="authOff"
              type="button"
              class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-lead font-semibold text-primary-foreground shadow-md transition-opacity hover:opacity-90"
              @click="goToSessions"
            >
              <Icon icon="codicon:arrow-right" class="h-4 w-4" />
              Open your workspaces
            </button>

            <!-- Auth-required: pick the CTA based on the signed-in
                 state from Clerk so the hero adapts in real time. -->
            <template v-else>
              <ClerkShow :when="'signed-in'">
                <button
                  type="button"
                  class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-lead font-semibold text-primary-foreground shadow-md transition-opacity hover:opacity-90"
                  @click="goToSessions"
                >
                  <Icon icon="codicon:arrow-right" class="h-4 w-4" />
                  Continue to your workspaces
                </button>
              </ClerkShow>
              <ClerkShow :when="'signed-out'">
                <button
                  type="button"
                  class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-lead font-semibold text-primary-foreground shadow-md transition-opacity hover:opacity-90"
                  @click="goToLogin"
                >
                  <Icon icon="codicon:rocket" class="h-4 w-4" />
                  Get started — free
                </button>
              </ClerkShow>
            </template>

            <RouterLink
              to="/pricing"
              class="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-4 py-2.5 text-lead font-medium text-foreground transition-colors hover:border-primary/50"
            >
              See pricing
              <Icon icon="codicon:chevron-right" class="h-3.5 w-3.5 opacity-70" />
            </RouterLink>
          </div>
          <p class="mt-3 text-caption text-muted-foreground">
            No credit card required. Cancel any time from your account.
          </p>
        </div>
      </section>

      <!-- PILLARS -->
      <section class="mx-auto w-full max-w-5xl px-6 pb-16">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <article
            v-for="p in PILLARS"
            :key="p.title"
            class="rounded-xl border border-border bg-card p-5"
          >
            <div
              class="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary"
            >
              <Icon :icon="p.icon" class="h-4 w-4" />
            </div>
            <h3 class="text-h2 font-semibold tracking-tight text-foreground">
              {{ p.title }}
            </h3>
            <p class="mt-2 text-lead leading-relaxed text-muted-foreground">
              {{ p.body }}
            </p>
          </article>
        </div>
      </section>

      <!-- PLANS TEASER -->
      <section class="mx-auto w-full max-w-5xl px-6 pb-20">
        <header class="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 class="text-h1 font-semibold tracking-tight text-foreground">
              Pricing that follows the meter
            </h2>
            <p class="mt-2 max-w-xl text-lead leading-relaxed text-muted-foreground">
              We pass the actual model + infra cost through. No per-token
              surprises, no hidden margin. Cancel any time.
            </p>
          </div>
          <RouterLink
            to="/pricing"
            class="inline-flex items-center gap-1 text-lead font-medium text-primary hover:underline"
          >
            Compare full plans
            <Icon icon="codicon:arrow-right" class="h-3.5 w-3.5" />
          </RouterLink>
        </header>

        <div
          v-if="plans.length"
          class="grid grid-cols-1 gap-4 md:grid-cols-3"
        >
          <RouterLink
            v-for="p in plans.slice(0, 3)"
            :key="p.id"
            to="/pricing"
            class="group rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/50"
          >
            <div class="flex items-baseline justify-between">
              <h3 class="text-h2 font-semibold tracking-tight">{{ p.label }}</h3>
              <span class="text-lead font-mono text-muted-foreground">
                ${{ p.monthly_price_usd }}<span class="text-caption">/mo</span>
              </span>
            </div>
            <p class="mt-2 text-lead leading-snug text-muted-foreground">
              {{ p.description }}
            </p>
            <span
              class="mt-4 inline-flex items-center gap-1 text-body font-medium text-primary opacity-80 transition-opacity group-hover:opacity-100"
            >
              View details
              <Icon icon="codicon:arrow-right" class="h-3 w-3" />
            </span>
          </RouterLink>
        </div>
        <div
          v-else
          class="rounded-xl border border-border bg-card p-5 text-center text-lead text-muted-foreground"
        >
          Loading plan catalogue…
        </div>
      </section>

      <!-- CLOSING -->
      <section class="mx-auto w-full max-w-3xl px-6 pb-20 text-center">
        <p class="text-lead leading-relaxed text-muted-foreground">
          <Icon icon="codicon:circuit-board" class="mr-1 inline h-3.5 w-3.5 align-text-bottom" />
          Built on top of
          <a
            href="https://github.com/coding-agent/pi"
            target="_blank"
            rel="noopener noreferrer"
            class="font-mono font-semibold text-foreground/80 hover:text-primary hover:underline"
          >pi</a>
          — an open-source coding agent. Digi Setu adds the sandbox, the UI,
          and the production-grade Typst pipeline.
        </p>
        <div class="mt-5 flex flex-wrap items-center justify-center gap-3">
          <button
            v-if="authOff"
            type="button"
            class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-lead font-semibold text-primary-foreground shadow-sm hover:opacity-90"
            @click="goToSessions"
          >
            Open your workspaces
            <Icon icon="codicon:arrow-right" class="h-4 w-4" />
          </button>
          <template v-else>
            <ClerkShow :when="'signed-in'">
              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-lead font-semibold text-primary-foreground shadow-sm hover:opacity-90"
                @click="goToSessions"
              >
                Open your workspaces
                <Icon icon="codicon:arrow-right" class="h-4 w-4" />
              </button>
            </ClerkShow>
            <ClerkShow :when="'signed-out'">
              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-lead font-semibold text-primary-foreground shadow-sm hover:opacity-90"
                @click="goToLogin"
              >
                Start a chat
                <Icon icon="codicon:arrow-right" class="h-4 w-4" />
              </button>
            </ClerkShow>
          </template>
          <RouterLink
            to="/feedback"
            class="inline-flex items-center gap-1 rounded-md border border-border bg-card px-4 py-2 text-lead font-medium text-foreground hover:border-primary/50"
          >
            Send feedback
          </RouterLink>
        </div>
      </section>
    </main>
  </div>
</template>
