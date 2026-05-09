<!--
  Terms & output ownership — unified canonical document.

  Same approach as Privacy.vue: this single file is rendered identically
  by both the web editor (digi-setu.com) and the desktop app, so terms
  are one document and never drift between the two surfaces. Where the
  rules differ between web and desktop, sub-paragraphs call it out
  explicitly.
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
        { to: '/pricing', label: $t('nav.pricing') },
        { to: '/privacy', label: $t('nav.privacy') },
      ]"
    />

    <main class="mx-auto w-full max-w-3xl flex-1 px-6 py-12 md:py-16">
      <header class="mb-10">
        <span class="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-caption uppercase tracking-wider text-muted-foreground">
          <Icon icon="codicon:law" class="h-3 w-3" />
          {{ $t("terms.badge") }}
        </span>
        <h1 class="mt-3 text-h1 font-semibold tracking-tight">
          {{ $t("terms.title") }}
        </h1>
        <p class="mt-3 text-lead leading-relaxed text-muted-foreground">
          The plain-English version. Applies to both the
          <strong>web editor</strong> at
          <a href="https://digi-setu.com" class="text-primary underline-offset-2 hover:underline">digi-setu.com</a>
          and the <strong>desktop app</strong>. Nothing here substitutes
          for legal advice; reach out if anything's unclear.
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
          <div class="mt-2 text-lead font-semibold">{{ fact.label }}</div>
          <div class="mt-1 text-caption leading-snug text-muted-foreground">
            {{ fact.detail }}
          </div>
        </div>
      </section>

      <!-- DETAILS -->
      <article class="mt-12 space-y-10">
        <!-- 1. Output ownership -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:law" class="h-4 w-4 text-primary" />
            Who owns what the agent produces
          </h2>
          <div class="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-4 text-body leading-relaxed">
            <p>
              <strong>You do.</strong> Anything the agent writes into your
              workspace — code, Typst documents, generated PDFs, scripts —
              is yours. We do not claim a license to it, do not retain
              rights to it, and do not re-use it elsewhere.
            </p>
          </div>
          <p class="mt-3 text-body leading-relaxed text-muted-foreground">
            The underlying model providers (Anthropic, Google, OpenAI)
            have their own output policies. For paid API usage they
            generally don't claim ownership of generated output.
          </p>
          <p class="mt-2 text-body leading-relaxed text-muted-foreground">
            <strong>Web editor:</strong> we orchestrate the model call
            on your behalf using our provider contracts; the
            provider-side terms that apply are ours, not yours, and we
            don't transfer claims to the output back to the provider.
          </p>
          <p class="mt-2 text-body leading-relaxed text-muted-foreground">
            <strong>Desktop with BYOK:</strong> if you're using your own
            provider API key, your contract with that provider applies
            to the model output. Digi Setu just orchestrates the call —
            it never sees the request or response.
          </p>
        </section>

        <!-- 2. Acceptable use -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:warning" class="h-4 w-4 text-primary" />
            Acceptable use
          </h2>
          <ul class="mt-3 space-y-2 text-body leading-relaxed">
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>Don't use Digi Setu to generate or distribute content that's illegal where you live.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>Don't try to extract our infrastructure, prompts, or other users' data — applies equally to the hosted web service and to attempts to reverse-engineer the desktop binary's relay credentials.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>Don't run abusive automated workloads against the web editor or the cloud-relay endpoint — we rate-limit, but a determined attacker will get banned.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span>The desktop app is licensed for personal and team use; redistributing the binary as your own product is not permitted.</span>
            </li>
          </ul>
        </section>

        <!-- 3. No warranty -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:circle-slash" class="h-4 w-4 text-primary" />
            No warranty
          </h2>
          <p class="mt-3 text-body leading-relaxed">
            Digi Setu is provided as-is. The agent makes mistakes;
            review what it produces before relying on it. The desktop
            app can run shell commands and edit files on your machine —
            stay aware of what permission mode (Auto / Ask / Cautious)
            you're using and what you're approving. We're not liable
            for losses caused by acting on the agent's output or by
            commands you allowed it to run.
          </p>
        </section>

        <!-- 4. Subscriptions and billing -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:credit-card" class="h-4 w-4 text-primary" />
            Subscriptions &amp; billing
          </h2>
          <p class="mt-3 text-body leading-relaxed">
            Paid plans are billed monthly through Stripe. You can
            cancel any time from <em>Account → Manage subscription</em>;
            cancellation takes effect at the end of the current billing
            cycle. We don't issue partial refunds for unused time.
          </p>
          <p class="mt-2 text-body leading-relaxed text-muted-foreground">
            <strong>Desktop BYOK users</strong> who provide their own AI
            provider key are billed by that provider, not by us. The
            desktop app can be used in BYOK mode without any Digi Setu
            subscription.
          </p>
        </section>

        <!-- 5. Changes -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon icon="codicon:history" class="h-4 w-4 text-primary" />
            Changes
          </h2>
          <p class="mt-3 text-body leading-relaxed">
            We'll update this page when meaningful policy changes
            happen, and we'll show a notice at sign-in if it's a
            material change. Continued use of either product after a
            material change constitutes acceptance.
          </p>
        </section>
      </article>
    </main>

    <footer class="border-t border-border bg-card/40 px-6 py-4 text-center text-caption text-muted-foreground">
      © {{ new Date().getFullYear() }} Digi Setu
    </footer>
  </div>
</template>
