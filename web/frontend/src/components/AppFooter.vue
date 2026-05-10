<!--
  AppFooter — single source of truth for the public-page footer.

  Locks the copyright string at "© 2025 Digi Setu" — we deliberately
  do NOT use `new Date().getFullYear()` here. The dynamic year was a
  long-running annoyance: every Jan 1 the copyright would silently
  flip to a year before the codebase had any commits in it, and on
  long-running browser sessions the displayed year disagreed with
  the page's "last updated" badges. Fixed string, bumped manually
  during the annual review.

  Used by Home, Picker, Pricing, Feedback, Login, Privacy, Terms.
-->
<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <footer
    class="border-t border-border bg-card/50 px-6 py-5 text-caption text-muted-foreground"
  >
    <div
      class="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 sm:flex-row"
    >
      <span>© 2025 Digi Setu — built for writers, coders &amp; everyone in between.</span>
      <nav class="flex items-center gap-4">
        <RouterLink
          to="/download"
          class="hover:text-foreground hover:underline"
        >Download</RouterLink>
        <RouterLink
          to="/pricing"
          class="hover:text-foreground hover:underline"
        >Pricing</RouterLink>
        <RouterLink
          to="/privacy"
          class="hover:text-foreground hover:underline"
        >Privacy</RouterLink>
        <RouterLink
          to="/terms"
          class="hover:text-foreground hover:underline"
        >Terms</RouterLink>
        <RouterLink
          to="/feedback"
          class="hover:text-foreground hover:underline"
        >Contact</RouterLink>
      </nav>
    </div>
  </footer>
</template>
