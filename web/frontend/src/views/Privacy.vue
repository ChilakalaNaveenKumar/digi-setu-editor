<!--
  Privacy & data handling — unified canonical document.

  Digi Setu ships in two surfaces:

    1. Web editor — digi-setu.com (this site, the file you're reading
       in a browser). Server-hosted; your prompts and files transit
       and rest on our infrastructure.

    2. Desktop app — Digi Setu Desktop (Tauri-shell binary). Runs
       entirely on the user's own machine; their files and chat
       history never leave their disk.

  The two products have meaningfully different data flows, so this
  page is structured around topic → (web behaviour, desktop behaviour)
  pairs. Both web and desktop frontends render this exact same file
  so the document is one source of truth — never drifts.
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";

interface KeyFact {
  icon: string;
  label: string;
  detail: string;
}

const KEY_FACTS: KeyFact[] = [
  {
    icon: "codicon:eye-closed",
    label: "We never train on you",
    detail: "Your prompts and files don't feed any model — web or desktop.",
  },
  {
    icon: "codicon:trash",
    label: "Self-service delete",
    detail: "One click in your account menu wipes everything we hold.",
  },
  {
    icon: "codicon:device-desktop",
    label: "Desktop is local-first",
    detail: "Files and chat history stay on your laptop; we never copy them.",
  },
];

interface Section {
  icon: string;
  title: string;
}

const SECTIONS: Section[] = [
  { icon: "codicon:database",       title: "What we store" },
  { icon: "codicon:remote",         title: "Where prompts actually go" },
  { icon: "codicon:trash",          title: "Deleting your data" },
  { icon: "codicon:archive",        title: "Backups & retention" },
  { icon: "codicon:mail",           title: "Contact" },
];
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="mx-auto w-full max-w-3xl flex-1 px-6 py-12 md:py-16">
      <header class="mb-10">
        <span class="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-caption uppercase tracking-wider text-muted-foreground">
          <Icon icon="codicon:shield" class="h-3 w-3" />
          {{ $t("privacy.badge") }}
        </span>
        <h1 class="mt-3 text-h1 font-semibold tracking-tight">
          {{ $t("privacy.title") }}
        </h1>
        <p class="mt-3 text-lead leading-relaxed text-muted-foreground">
          Digi Setu ships as a hosted <strong>web editor</strong> at
          <a href="https://digi-setu.com" class="text-primary underline-offset-2 hover:underline">digi-setu.com</a>
          and as a <strong>desktop app</strong> you install on your own
          machine. The two have meaningfully different data flows, so
          every section below tells you what applies to each. Anything
          ambiguous is a bug — please
          <a href="mailto:support@digi-setu.com" class="text-primary underline-offset-2 hover:underline">tell&nbsp;us</a>.
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
          <div class="mt-2 text-lead font-semibold">{{ fact.label }}</div>
          <div class="mt-1 text-caption leading-snug text-muted-foreground">
            {{ fact.detail }}
          </div>
        </div>
      </section>

      <!-- DETAILS -->
      <article class="mt-12 space-y-10">
        <!-- ───────────── 1 · What we store ───────────── -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[0].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[0].title }}
          </h2>

          <div class="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            <!-- Web editor -->
            <div class="rounded-lg border border-primary/30 bg-primary/5 p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:globe" class="h-4 w-4 text-primary" />
                If you use the web editor (digi-setu.com)
              </p>
              <ul class="mt-3 space-y-2">
                <li><strong>Account.</strong> Email + auth identity (Clerk).</li>
                <li><strong>Chats.</strong> Every prompt, every model response, and the agent's tool calls — kept on our server's disk so you can resume a session.</li>
                <li><strong>Files.</strong> Whatever you (or the agent) write into your workspace, kept on our server's disk.</li>
                <li><strong>Usage logs.</strong> Connection times + per-request rate-limit counters. No content is logged here.</li>
              </ul>
            </div>

            <!-- Desktop app -->
            <div class="rounded-lg border border-border bg-card p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:device-desktop" class="h-4 w-4 text-primary" />
                If you use the desktop app
              </p>
              <ul class="mt-3 space-y-2">
                <li><strong>Files &amp; chats stay on your machine</strong>, in <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">~/.digi-setu/</code> on your disk. We have no copy.</li>
                <li><strong>Account.</strong> Email + auth identity (Clerk) — the only piece that reaches our servers.</li>
                <li><strong>Billing metadata.</strong> Stripe customer + subscription state.</li>
                <li><strong>Usage counters.</strong> Per-day token totals + model used. <em>No prompt content; no file content.</em></li>
                <li><strong>BYOK API keys</strong> in <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">~/.digi-setu/.env</code> stay on disk; the app calls the provider directly, we never see them.</li>
                <li><strong>Crash reports (opt-in only).</strong> Stack traces + app version. Off by default.</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- ───────────── 2 · Where prompts actually go ───────────── -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[1].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[1].title }}
          </h2>
          <p class="mt-3 text-body leading-relaxed text-muted-foreground">
            Sending a prompt always means a third party (the AI model
            provider) sees it. Which provider — and whether the request
            transits our servers along the way — depends on which surface
            and which mode you're using.
          </p>

          <div class="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            <!-- Web editor -->
            <div class="rounded-lg border border-primary/30 bg-primary/5 p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:globe" class="h-4 w-4 text-primary" />
                Web editor
              </p>
              <p class="mt-2 text-muted-foreground">
                Prompts are sent from your browser to our backend, which
                forwards them to the model provider (currently Anthropic
                via Vertex AI; OpenAI / Google as fallbacks). We
                <strong>do not train</strong> any model on your data and
                we do <strong>not share</strong> it with anyone outside
                the provider that fulfils the request.
              </p>
            </div>

            <!-- Desktop app — two sub-modes -->
            <div class="rounded-lg border border-border bg-card p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:device-desktop" class="h-4 w-4 text-primary" />
                Desktop app
              </p>
              <p class="mt-2 text-muted-foreground">
                <strong>BYOK mode</strong> — you put a provider API key
                in <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">~/.digi-setu/.env</code>.
                The app calls the provider directly from your machine.
                <em>We never see the request, response, or token count.</em>
              </p>
              <p class="mt-2 text-muted-foreground">
                <strong>Cloud-relay mode</strong> — you're on a paid plan
                without your own key. Prompts transit our relay at
                <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">api.digi-setu.com</code>
                which forwards to the model provider. We log
                <em>only</em> timestamp, your user id, model name, and
                token count for billing — never prompt or response
                content.
              </p>
            </div>
          </div>

          <p class="mt-4 text-caption leading-relaxed text-muted-foreground">
            We never train any model on your data, regardless of mode.
            Provider-side retention is governed by each provider's own
            policy — Anthropic, Google, and OpenAI publish their paid-API
            retention windows separately.
          </p>
        </section>

        <!-- ───────────── 3 · Deleting your data ───────────── -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[2].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[2].title }}
          </h2>

          <div class="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            <!-- Web editor -->
            <div class="rounded-lg border border-primary/30 bg-primary/5 p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:globe" class="h-4 w-4 text-primary" />
                Web editor
              </p>
              <p class="mt-2 text-muted-foreground">
                Top-right avatar → <em>Manage account</em> →
                <em>Delete account</em>. Wipes your auth record, every
                workspace you own, every chat log, and every shadow-git
                history. No email, no support ticket, no waiting.
              </p>
              <p class="mt-2 text-muted-foreground">
                Want to delete just one workspace? Trash icon on the
                picker. The folder, its sessions, and the per-workspace
                shadow-git repo are removed in one step.
              </p>
            </div>

            <!-- Desktop app -->
            <div class="rounded-lg border border-border bg-card p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:device-desktop" class="h-4 w-4 text-primary" />
                Desktop app
              </p>
              <p class="mt-2 text-muted-foreground">
                <strong>Local data (your laptop):</strong> quit the app,
                then delete <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">~/.digi-setu/</code>.
                That removes every chat log, every shadow-git checkpoint,
                every cached file, and your local BYOK env file.
                Uninstall the app via your OS's normal flow.
              </p>
              <p class="mt-2 text-muted-foreground">
                <strong>Cloud account:</strong> top-right avatar →
                <em>Manage account</em> → <em>Delete account</em>. Wipes
                your auth record, billing subscription state, and the
                per-user usage counters. No email, no support ticket.
              </p>
            </div>
          </div>
        </section>

        <!-- ───────────── 4 · Backups & retention ───────────── -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[3].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[3].title }}
          </h2>

          <div class="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div class="rounded-lg border border-primary/30 bg-primary/5 p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:globe" class="h-4 w-4 text-primary" />
                Web editor
              </p>
              <p class="mt-2 text-muted-foreground">
                Backups exist for disaster recovery only. When you delete
                an account or a workspace the live data is gone
                immediately; backup tapes age out within 30 days.
              </p>
            </div>

            <div class="rounded-lg border border-border bg-card p-4 text-body leading-relaxed">
              <p class="flex items-center gap-2 text-lead font-semibold text-foreground">
                <Icon icon="codicon:device-desktop" class="h-4 w-4 text-primary" />
                Desktop app
              </p>
              <p class="mt-2 text-muted-foreground">
                We have no backup of your local data — there is nothing
                on our side to back up. Your own machine's
                Time&nbsp;Machine / File&nbsp;History / Backblaze
                backups govern desktop data retention.
              </p>
              <p class="mt-2 text-muted-foreground">
                Stripe and Clerk's own retention windows (typically
                required for tax / fraud-detection reasons) follow
                deletion of the cloud account.
              </p>
            </div>
          </div>
        </section>

        <!-- ───────────── 5 · Contact ───────────── -->
        <section>
          <h2 class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground">
            <Icon :icon="SECTIONS[4].icon" class="h-4 w-4 text-primary" />
            {{ SECTIONS[4].title }}
          </h2>
          <p class="mt-3 text-body leading-relaxed">
            Questions or a takedown request:
            <a class="text-primary underline-offset-2 hover:underline" href="mailto:support@digi-setu.com">
              support@digi-setu.com
            </a>.
          </p>
        </section>
      </article>
    </main>
  </div>
</template>
