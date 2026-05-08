<!--
  Privacy — public, static. Addresses the explicit user feedback:
  "Generally, how is data handled? E-mail deletion request is not
  allowed in certain countries." We answer plainly and self-host
  every deletion control so no inbox round-trip is ever required.

  Layout — sectioned with leading icons so the page scans at a
  glance. A "key facts" strip up top summarises the three things most
  visitors actually want to know (we don't train on your data; you
  can self-delete; backups age out).
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
    icon: "codicon:eye-closed",
    label: "We don't train on you",
    detail: "Your prompts and files never feed any model.",
  },
  {
    icon: "codicon:trash",
    label: "Self-service delete",
    detail: "One click in your account menu wipes everything.",
  },
  {
    icon: "codicon:archive",
    label: "Backups age out",
    detail: "Disaster-recovery snapshots roll off in 30 days.",
  },
];

interface Section {
  icon: string;
  title: string;
}

const SECTIONS: Section[] = [
  { icon: "codicon:database", title: "What we store" },
  { icon: "codicon:remote", title: "Who else sees your prompts" },
  { icon: "codicon:trash", title: "Deleting your data" },
  { icon: "codicon:archive", title: "Backups & retention" },
  { icon: "codicon:mail", title: "Contact" },
];
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <BrandHeader
      :links="[
        { to: '/pricing', label: 'Pricing' },
        { to: '/terms', label: 'Terms' },
      ]"
    />

    <main class="mx-auto w-full max-w-3xl flex-1 px-6 py-12 md:py-16">
      <header class="mb-10">
        <span class="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <Icon icon="codicon:shield" class="h-3 w-3" />
          v1 · last updated 2026-05
        </span>
        <h1 class="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
          Privacy &amp; data handling
        </h1>
        <p class="mt-3 text-sm leading-relaxed text-muted-foreground">
          We try to keep this page short, plain, and accurate. Anything
          ambiguous below is a bug — please
          <a href="mailto:nchilaka@digi-setu.com" class="text-primary underline-offset-2 hover:underline">
            tell us</a>.
        </p>
      </header>

      <!-- KEY FACTS strip -->
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
            <Icon :icon="SECTIONS[0].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[0].title }}
          </h2>
          <ul class="mt-3 space-y-2 text-sm leading-relaxed">
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span><strong>Account.</strong> Your email + auth identity, managed by Clerk.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span><strong>Chats.</strong> Every prompt, every model response, and the agent's tool calls — kept so you can resume a session.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span><strong>Files.</strong> Whatever you (or the agent) write into your workspace, kept on our server's disk.</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon icon="codicon:circle-small" class="mt-1 h-3 w-3 text-primary" />
              <span><strong>Usage logs.</strong> Connection times + per-request rate-limit counters. No content is logged here.</span>
            </li>
          </ul>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[1].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[1].title }}
          </h2>
          <p class="mt-3 text-sm leading-relaxed">
            Prompts and the file context you attach are sent to whichever LLM
            provider routes your request (currently Anthropic and, optionally,
            providers you've configured via your own API keys). We do
            <strong>not</strong> train any model on your data and we do
            <strong>not</strong> share it with anyone else.
          </p>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[2].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[2].title }}
          </h2>
          <div class="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm leading-relaxed">
            <p class="font-semibold text-foreground">One-click account delete</p>
            <p class="mt-1 text-muted-foreground">
              Top-right avatar → <em>Manage account</em> → <em>Delete account</em>.
              Wipes your auth record, every workspace you own, every chat
              log, and every shadow-git history. No email, no support
              ticket, no waiting.
            </p>
          </div>
          <p class="mt-3 text-sm leading-relaxed text-muted-foreground">
            Want to delete just one workspace? Use the trash icon on the
            picker. The folder, its sessions, and the per-workspace shadow-
            git repo are removed in one step.
          </p>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[3].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[3].title }}
          </h2>
          <p class="mt-3 text-sm leading-relaxed">
            Backups exist for disaster recovery only. When you delete an
            account or a workspace the live data is gone immediately;
            backup tapes age out within 30 days.
          </p>
        </section>

        <section>
          <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[4].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[4].title }}
          </h2>
          <p class="mt-3 text-sm leading-relaxed">
            Questions or a takedown request:
            <a class="text-primary underline-offset-2 hover:underline" href="mailto:nchilaka@digi-setu.com">
              nchilaka@digi-setu.com
            </a>.
          </p>
        </section>
      </article>
    </main>

    <footer class="border-t border-border bg-card/40 px-6 py-4 text-center text-[11px] text-muted-foreground">
      © {{ new Date().getFullYear() }} Digi Setu
    </footer>
  </div>
</template>
