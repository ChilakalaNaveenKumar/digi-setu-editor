<!--
  Terms — public, static. Addresses "Who owns the output? I saw that
  Gemini is used, but their output ownership depends on the
  subscription." We answer the only thing that actually matters to a
  user: *who can stop you from using what comes out*.
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import BrandHeader from "../components/BrandHeader.vue";

interface KeyFact {
  icon: string;
  label: string;
  detail: string;
}

const KEY_FACTS: KeyFact[] = [
  {
    icon: "codicon:law",
    label: "You own the output",
    detail: "Whatever the agent writes is yours. We don't claim a license.",
  },
  {
    icon: "codicon:warning",
    label: "Use it responsibly",
    detail: "No illegal content, no infra exfiltration, no abuse loops.",
  },
  {
    icon: "codicon:circle-slash",
    label: "No warranty",
    detail: "Review what the agent produces before relying on it.",
  },
];
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <BrandHeader
      :links="[
        { to: '/pricing', label: 'Pricing' },
        { to: '/privacy', label: 'Privacy' },
      ]"
    />

    <main class="mx-auto w-full max-w-3xl flex-1 px-6 py-12 md:py-16">
      <header class="mb-10">
        <span class="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <Icon icon="codicon:law" class="h-3 w-3" />
          v1 · last updated 2026-05
        </span>
        <h1 class="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
          Terms &amp; output ownership
        </h1>
        <p class="mt-3 text-sm leading-relaxed text-muted-foreground">
          The plain-English version. Nothing here substitutes for legal
          advice; reach out if anything's unclear.
        </p>
      </header>

      <!-- KEY FACTS -->
      <section class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div
          v-for="fact in KEY_FACTS"
          :key="fact.label"
          class="rounded-lg border border-border bg-card p-4"
        >
          <Icon :icon="fact.icon" class="h-5 w-5 text-primary" />
          <div class="mt-2 text-sm font-semibold">{{ fact.label }}</div>
          <div class="mt-1 text-xs leading-snug text-muted-foreground">
            {{ fact.detail }}
          </div>
        </div>
      </section>

      <!-- DETAILS -->
      <article class="mt-12 space-y-10">
        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:law" class="h-4 w-4 text-primary" />
            Who owns what the agent produces
          </h2>
          <div class="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm leading-relaxed">
            <p>
              <strong>You do.</strong> Anything the agent writes into your
              workspace — Typst documents, code, generated PDFs — is yours.
              We do not claim a license to it, do not retain rights to it,
              and do not re-use it elsewhere.
            </p>
          </div>
          <p class="mt-3 text-xs leading-relaxed text-muted-foreground">
            The underlying model providers (Anthropic, Google, etc.) have
            their own output policies. For paid API usage they generally
            don't claim ownership of generated output. If you're using a
            provider API key you supplied, your contract with that provider
            applies to the model output; Digi Setu just orchestrates the
            call.
          </p>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:warning" class="h-4 w-4 text-primary" />
            Acceptable use
          </h2>
          <ul class="mt-3 space-y-2 text-sm leading-relaxed">
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>Don't use Digi Setu to generate or distribute content that's illegal where you live.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>Don't try to extract our infrastructure, prompts, or other users' data.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>Don't run abusive automated workloads — we rate-limit, but a determined attacker will get banned.</span>
            </li>
          </ul>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:circle-slash" class="h-4 w-4 text-primary" />
            No warranty
          </h2>
          <p class="mt-3 text-sm leading-relaxed">
            Digi Setu is provided as-is. The agent makes mistakes; review
            what it produces before relying on it. We're not liable for
            losses caused by acting on its output.
          </p>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:history" class="h-4 w-4 text-primary" />
            Changes
          </h2>
          <p class="mt-3 text-sm leading-relaxed">
            We'll update this page when meaningful policy changes happen,
            and we'll show a notice at sign-in if it's a material change.
          </p>
        </section>
      </article>
    </main>

    <footer class="border-t border-border bg-card/40 px-6 py-4 text-center text-[11px] text-muted-foreground">
      © {{ new Date().getFullYear() }} Digi Setu
    </footer>
  </div>
</template>
