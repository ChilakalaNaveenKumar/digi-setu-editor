<!--
  WebSandboxNotice — first-run / empty-chat info card.

  Shown above the "type below to start" copy when a chat has zero
  messages. The first-time experience on the hosted web product was
  silently failing users: they'd sign in, land in a blank chat, and
  upload an R / Quarto / heavy-toolchain workflow with no awareness
  that the cloud sandbox is ephemeral and 100 MB-quota'd. By the time
  the rendering started failing, they'd already lost trust in the
  product. This notice fronts those constraints proactively.

  Surface model:
    - Compact-by-default: one tight line with a clear "not your
      machine" framing, an expand toggle, and a "Get desktop" CTA.
    - Expandable: two columns of can-do / can't-do, the numeric
      limits chip, and a primary CTA to /download.
    - Dismissible: a tiny × button writes a flag to localStorage so
      returning users with hundreds of past chats don't have to see
      it on every new empty session. The flag is keyed per browser
      (not per user-account) so a shared laptop's other tenants still
      see the notice on their first visit.

  Where this renders:
    Embedded inside MessageList's empty-state branch. Becomes invisible
    the moment the user's first message lands (messages.length > 0)
    AND for the next chat after they've dismissed it once. We don't
    show it on every empty chat forever — that would be nagware.

  Why localStorage and not user_prefs.json:
    user_prefs.json is shared between web and desktop. Dismissing this
    notice in the web product shouldn't silently make the same notice
    disappear in some future desktop feature, and vice versa. localStorage
    is also a single write/read and survives across sessions in the same
    browser — exactly the persistence we want for a UX hint.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { Icon } from "@iconify/vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const STORAGE_KEY = "digi-setu.sandbox-notice.dismissed";

// Persist dismissal so returning users with many past chats don't get
// hit by this on every new empty session. Reading once on mount is
// enough; we only flip the value in one place (the × handler).
function loadDismissed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    // Private mode / quota / sandbox iframe — fail open (show the
    // notice). Better to surface the message twice than to hide it
    // forever from someone who'd benefit from seeing it once.
    return false;
  }
}

const dismissed = ref(loadDismissed());
const expanded = ref(false);
const shown = computed(() => !dismissed.value);

function dismiss(): void {
  dismissed.value = true;
  try {
    localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* localStorage unavailable — at least hide for this session */
  }
}

function toggle(): void {
  expanded.value = !expanded.value;
}
</script>

<template>
  <div
    v-if="shown"
    class="mx-auto mb-6 mt-2 max-w-2xl rounded-lg border border-amber-500/30 bg-amber-500/[0.05] text-left"
  >
    <!-- Compact row: icon + headline + expand toggle + dismiss × -->
    <div class="flex items-start gap-3 px-4 py-3">
      <Icon
        icon="mdi:cloud-outline"
        class="mt-0.5 h-5 w-5 shrink-0 text-amber-400"
        aria-hidden="true"
      />
      <div class="flex-1 min-w-0">
        <p class="text-body leading-snug text-foreground">
          <strong>{{ t("sandbox.headlineStrong") }}</strong>
          {{ t("sandbox.headlineRest") }}
        </p>
        <!-- Compact-row actions: the secondary "expand" toggle and the
             primary "get desktop" CTA sit side by side so the user
             doesn't have to expand the notice to discover the most
             important affordance (the way out of the sandbox). The
             desktop link is visually weightier than the expand toggle
             because it's the action that actually solves the user's
             problem when they hit a limit. -->
        <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
          <a
            href="/download"
            class="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-caption font-medium text-amber-200 transition-colors hover:bg-amber-500/20 hover:text-amber-100"
          >
            <Icon icon="codicon:desktop-download" class="h-3.5 w-3.5" aria-hidden="true" />
            {{ t("sandbox.ctaCompact") }}
          </a>
          <button
            type="button"
            class="inline-flex items-center gap-1 text-caption text-muted-foreground hover:text-foreground"
            :aria-expanded="expanded"
            @click="toggle"
          >
            <span>{{ expanded ? t("sandbox.hideDetails") : t("sandbox.showDetails") }}</span>
            <Icon
              :icon="expanded ? 'codicon:chevron-up' : 'codicon:chevron-down'"
              class="h-3.5 w-3.5"
              aria-hidden="true"
            />
          </button>
        </div>
      </div>
      <button
        type="button"
        class="rounded-sm p-1 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        :title="t('sandbox.dismissTitle')"
        :aria-label="t('sandbox.dismissTitle')"
        @click="dismiss"
      >
        <Icon icon="codicon:close" class="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>

    <!-- Expanded body: limits chip, two-column can/cannot, CTA. -->
    <div
      v-if="expanded"
      class="border-t border-amber-500/20 px-4 py-4 text-body"
    >
      <!-- Hard limits, made obvious so power-users can size their
           work to fit (or pre-emptively go to desktop). The numbers
           here are the live VM's deploy/stack.env values — keep this
           string in sync with WORKSPACE_DISK_QUOTA_MB (currently 100)
           and PROMPT_TIMEOUT_SECONDS (currently 900) if either
           changes. Manual coupling, but the values shift rarely; an
           automated /api/config exposure can come later. -->
      <p class="mb-3 font-mono text-caption text-muted-foreground">
        {{ t("sandbox.limitsLine") }}
      </p>

      <div class="grid gap-4 md:grid-cols-2">
        <div>
          <p class="mb-2 text-caption font-semibold uppercase tracking-wide text-emerald-400">
            <Icon icon="codicon:check" class="mr-1 inline h-3.5 w-3.5" />
            {{ t("sandbox.worksHeader") }}
          </p>
          <ul class="space-y-1 text-foreground/90">
            <li>· {{ t("sandbox.worksTypst") }}</li>
            <li>· {{ t("sandbox.worksScripts") }}</li>
            <li>· {{ t("sandbox.worksDocs") }}</li>
            <li>· {{ t("sandbox.worksCompile") }}</li>
            <li>· {{ t("sandbox.worksExperiment") }}</li>
          </ul>
        </div>
        <div>
          <p class="mb-2 text-caption font-semibold uppercase tracking-wide text-amber-300">
            <Icon icon="codicon:warning" class="mr-1 inline h-3.5 w-3.5" />
            {{ t("sandbox.notForHeader") }}
          </p>
          <ul class="space-y-1 text-foreground/90">
            <li>· {{ t("sandbox.notForR") }}</li>
            <li>· {{ t("sandbox.notForBigData") }}</li>
            <li>· {{ t("sandbox.notForLong") }}</li>
            <li>· {{ t("sandbox.notForPersistent") }}</li>
            <li>· {{ t("sandbox.notForLocal") }}</li>
          </ul>
        </div>
      </div>

      <!-- Strong CTA: full-width link to the /download landing. We use
           an <a href> rather than a router-link because /download is
           also the page non-signed-in users land on, and we want the
           same navigation shape regardless of auth state. -->
      <a
        href="/download"
        class="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-body font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
      >
        <Icon icon="codicon:desktop-download" class="h-4 w-4" aria-hidden="true" />
        {{ t("sandbox.ctaDesktop") }}
      </a>
      <p class="mt-2 text-caption text-muted-foreground">
        {{ t("sandbox.ctaSubline") }}
      </p>
    </div>
  </div>
</template>
