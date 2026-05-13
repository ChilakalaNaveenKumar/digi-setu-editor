<!--
  Open-source acknowledgements page (desktop).

  This is the in-app rendering of THIRD_PARTY_NOTICES.md (kept at the
  repo root). It's the legal-attribution surface that satisfies the
  redistribution clauses in MIT, Apache 2.0, OFL, and LGPL — every
  bundled package is listed with its copyright + licence and a link
  to its full LICENSE file in the source repo.

  The web fork lives at web/frontend/src/views/Acknowledgements.vue
  and renders the same content (single document, two surfaces, never
  drift). Differences vs the web version: padding tightened by one
  step, and AppFooter is mounted inline because the desktop App.vue
  does not auto-render the global footer (matches the pattern used by
  Privacy.vue and Terms.vue in this folder).

  When you add or remove a vendored library from `guides/` or any
  user-facing dependency, update both this file AND THIRD_PARTY_NOTICES.md.
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import AppFooter from "../components/AppFooter.vue";

interface Component {
  name: string;
  version?: string;
  license: string;
  copyright: string;
  role: string;
  href: string;
  highlight?: boolean;
}

const TYPST_STACK: Component[] = [
  {
    name: "Typst",
    version: "0.14.2",
    license: "Apache 2.0",
    copyright: "© The Typst Project Developers",
    role: "Typesetting engine the agent compiles documents with.",
    href: "https://typst.app",
  },
  {
    name: "Touying",
    version: "0.7.3",
    license: "MIT",
    copyright: "© 2026 OrangeX4, © 2026 zral0kh",
    role: "Slide / presentation framework.",
    href: "https://github.com/touying-typ/touying",
  },
  {
    name: "CeTZ",
    version: "0.5.0",
    license: "LGPL-3.0",
    copyright: "© The CeTZ Authors",
    role: "Drawing & charts package.",
    href: "https://github.com/cetz-package/cetz",
    highlight: true,
  },
  {
    name: "Fletcher",
    version: "0.5.8",
    license: "MIT",
    copyright: "© 2023 Joseph Wilson",
    role: "Diagram package.",
    href: "https://github.com/Jollywatt/typst-fletcher",
  },
  {
    name: "Codly",
    version: "1.3.0",
    license: "MIT",
    copyright: "© 2023 Sébastien d'Herbais de Thun, et al.",
    role: "Code-listing package.",
    href: "https://github.com/Dherse/codly",
  },
  {
    name: "Quill",
    version: "0.7.2",
    license: "MIT",
    copyright: "© 2023-2025 Mc-Zen",
    role: "Quantum-circuit diagram package.",
    href: "https://github.com/Mc-Zen/quill",
  },
  {
    name: "Circuiteria",
    version: "0.2.0",
    license: "Apache 2.0",
    copyright: "© The Circuiteria Authors",
    role: "Electronic-circuit diagram package.",
    href: "https://github.com/Quaternijkon/circuiteria",
  },
];

const FONTS: Component[] = [
  {
    name: "Tabler Icons",
    license: "MIT",
    copyright: "© Tabler",
    role: "Icon font used in code listings.",
    href: "https://tabler.io/icons",
  },
  {
    name: "Source Sans 3",
    license: "OFL 1.1",
    copyright: "© Adobe",
    role: "Sample body font.",
    href: "https://github.com/adobe-fonts/source-sans",
  },
  {
    name: "Noto Color Emoji",
    license: "OFL 1.1",
    copyright: "© Google",
    role: "Emoji glyphs.",
    href: "https://fonts.google.com/noto/specimen/Noto+Color+Emoji",
  },
];

const APP_STACK: Component[] = [
  {
    name: "Vue.js",
    license: "MIT",
    copyright: "© Evan You & Vue contributors",
    role: "Frontend framework.",
    href: "https://vuejs.org",
  },
  {
    name: "Tauri",
    license: "MIT / Apache-2.0",
    copyright: "© Tauri Programme within The Commons Conservancy",
    role: "Cross-platform desktop shell.",
    href: "https://tauri.app",
  },
  {
    name: "FastAPI",
    license: "MIT",
    copyright: "© Sebastián Ramírez",
    role: "Backend HTTP layer.",
    href: "https://fastapi.tiangolo.com",
  },
  {
    name: "Iconify (Codicon)",
    license: "MIT",
    copyright: "© Iconify & contributors",
    role: "UI icon set.",
    href: "https://iconify.design",
  },
  {
    name: "Stripe SDK",
    license: "MIT",
    copyright: "© Stripe, Inc.",
    role: "Subscription billing.",
    href: "https://github.com/stripe/stripe-python",
  },
  {
    name: "Clerk SDK",
    license: "MIT",
    copyright: "© Clerk Inc.",
    role: "Authentication.",
    href: "https://clerk.com",
  },
];
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="mx-auto w-full max-w-3xl flex-1 px-6 py-10 md:py-14">
      <header class="mb-10">
        <span
          class="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-caption uppercase tracking-wider text-muted-foreground"
        >
          <Icon icon="codicon:heart" class="h-3 w-3" />
          {{ $t("acknowledgements.badge") }}
        </span>
        <h1 class="mt-3 text-h1 font-semibold tracking-tight">
          {{ $t("acknowledgements.title") }}
        </h1>
        <p class="mt-3 text-lead leading-relaxed text-muted-foreground">
          Digi Setu is built on top of years of work by hundreds of
          open-source maintainers. This page lists every library we
          bundle directly with the product, the licence each is
          distributed under, and the copyright holders we owe credit
          to. The full machine-readable equivalent lives at
          <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">THIRD_PARTY_NOTICES.md</code>
          in our source repository.
        </p>
      </header>

      <!-- Typst stack -->
      <section class="mt-2">
        <h2
          class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground"
        >
          <Icon icon="codicon:book" class="h-4 w-4 text-primary" />
          Typst typesetting stack
        </h2>
        <p class="mt-3 text-body leading-relaxed text-muted-foreground">
          Typst itself plus the package ecosystem the agent uses to
          render slides, diagrams, charts, code listings, and circuits.
        </p>
        <ul class="mt-4 space-y-3">
          <li
            v-for="c in TYPST_STACK"
            :key="c.name"
            class="rounded-lg border p-4"
            :class="
              c.highlight
                ? 'border-primary/40 bg-primary/5'
                : 'border-border bg-card'
            "
          >
            <div class="flex flex-wrap items-baseline gap-2">
              <a
                :href="c.href"
                target="_blank"
                rel="noopener"
                class="text-lead font-semibold text-foreground hover:text-primary hover:underline"
              >{{ c.name }}</a>
              <span
                v-if="c.version"
                class="font-mono text-caption text-muted-foreground"
              >v{{ c.version }}</span>
              <span
                class="ml-auto rounded-full bg-muted px-2 py-0.5 text-caption font-medium text-muted-foreground"
              >{{ c.license }}</span>
            </div>
            <p class="mt-1 text-body text-muted-foreground">{{ c.role }}</p>
            <p class="mt-1 text-caption text-muted-foreground">{{ c.copyright }}</p>
          </li>
        </ul>
      </section>

      <!-- LGPL clarification -->
      <section class="mt-10">
        <h2
          class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground"
        >
          <Icon icon="codicon:law" class="h-4 w-4 text-primary" />
          A note on CeTZ (LGPL-3.0)
        </h2>
        <div
          class="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-4 text-body leading-relaxed"
        >
          <p>
            CeTZ is the only Digi Setu component released under a
            <strong>copyleft</strong> licence (LGPL-3.0). LGPL permits
            commercial use of the library inside a proprietary product
            so long as users can swap the bundled copy out for a
            modified one of their own.
          </p>
          <p class="mt-2 text-muted-foreground">
            The desktop binary loads CeTZ via the standard Typst
            packages directory under
            <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">~/.digi-setu/</code> —
            drop a different version (or your own modified version) of
            <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">cetz</code>
            in there and the agent will pick it up. We don't modify
            CeTZ ourselves; if we ever ship local modifications, those
            modifications will be released under LGPL alongside the
            next release.
          </p>
        </div>
      </section>

      <!-- Fonts -->
      <section class="mt-10">
        <h2
          class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground"
        >
          <Icon icon="codicon:symbol-string" class="h-4 w-4 text-primary" />
          Bundled fonts
        </h2>
        <p class="mt-3 text-body leading-relaxed text-muted-foreground">
          Used by the agent for sample documents and code-listing
          rendering. The OFL permits embedding and redistribution
          inside Digi Setu but forbids selling the font files alone —
          we do neither.
        </p>
        <ul class="mt-4 space-y-3">
          <li
            v-for="c in FONTS"
            :key="c.name"
            class="rounded-lg border border-border bg-card p-4"
          >
            <div class="flex flex-wrap items-baseline gap-2">
              <a
                :href="c.href"
                target="_blank"
                rel="noopener"
                class="text-lead font-semibold text-foreground hover:text-primary hover:underline"
              >{{ c.name }}</a>
              <span
                class="ml-auto rounded-full bg-muted px-2 py-0.5 text-caption font-medium text-muted-foreground"
              >{{ c.license }}</span>
            </div>
            <p class="mt-1 text-body text-muted-foreground">{{ c.role }}</p>
            <p class="mt-1 text-caption text-muted-foreground">{{ c.copyright }}</p>
          </li>
        </ul>
      </section>

      <!-- Application stack -->
      <section class="mt-10">
        <h2
          class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground"
        >
          <Icon icon="codicon:package" class="h-4 w-4 text-primary" />
          Application stack
        </h2>
        <p class="mt-3 text-body leading-relaxed text-muted-foreground">
          The frameworks and SDKs that power the editor itself. The
          full transitive list ships with every release inside the
          dependency manifests
          (<code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">package.json</code>,
          <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">requirements.txt</code>,
          <code class="rounded bg-muted px-1 py-0.5 font-mono text-caption">Cargo.lock</code>)
          along with each package's own LICENSE file.
        </p>
        <ul class="mt-4 space-y-3">
          <li
            v-for="c in APP_STACK"
            :key="c.name"
            class="rounded-lg border border-border bg-card p-4"
          >
            <div class="flex flex-wrap items-baseline gap-2">
              <a
                :href="c.href"
                target="_blank"
                rel="noopener"
                class="text-lead font-semibold text-foreground hover:text-primary hover:underline"
              >{{ c.name }}</a>
              <span
                class="ml-auto rounded-full bg-muted px-2 py-0.5 text-caption font-medium text-muted-foreground"
              >{{ c.license }}</span>
            </div>
            <p class="mt-1 text-body text-muted-foreground">{{ c.role }}</p>
            <p class="mt-1 text-caption text-muted-foreground">{{ c.copyright }}</p>
          </li>
        </ul>
      </section>

      <!-- AI output -->
      <section class="mt-10">
        <h2
          class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground"
        >
          <Icon icon="codicon:robot" class="h-4 w-4 text-primary" />
          On AI-generated output
        </h2>
        <p class="mt-3 text-body leading-relaxed">
          The agent uses third-party large language models (currently
          Anthropic Claude via Vertex AI; Google Gemini and OpenAI as
          fallbacks). Purely AI-generated content may not be eligible
          for copyright protection in some jurisdictions — most
          notably the United States, per the U.S. Copyright Office's
          2023 guidance. Please review and edit generated material
          before relying on it where authorship attribution or
          downstream IP claims matter. See the
          <RouterLink to="/terms" class="text-primary underline-offset-2 hover:underline">
            Terms
          </RouterLink>
          for the full output-ownership clause.
        </p>
      </section>

      <!-- Reach out -->
      <section class="mt-10">
        <h2
          class="flex items-center gap-2 text-lead font-semibold uppercase tracking-wide text-foreground"
        >
          <Icon icon="codicon:mail" class="h-4 w-4 text-primary" />
          Something missing or wrong?
        </h2>
        <p class="mt-3 text-body leading-relaxed">
          If a notice here is incomplete, inaccurate, or you believe
          we're using your work in a way the licence above doesn't
          permit, email
          <a
            class="text-primary underline-offset-2 hover:underline"
            href="mailto:support@digi-setu.com"
          >support@digi-setu.com</a>
          and we'll fix it promptly.
        </p>
      </section>
    </main>

    <AppFooter />
  </div>
</template>
