<!--
  ChatErrorCard — full-card overlay for ANY chat-state error.

  Replaces the bottom strip (ChatErrorBanner) for everything that
  surfaces via `chat.lastError`. Users complained that errors at the
  bottom of the chat were easy to miss and looked like "another
  toolbar" — this card pops front-and-centre so the failure is
  unmissable AND the recovery action is one click away.

  How it works:
    - One overlay component, but the title / icon / action button /
      colour all flex based on the error code's kind. We derive kind
      from the `errors.<code>` key, falling back to "generic" for
      anything unknown so the surface stays graceful as backend codes
      evolve.
    - Body text is fully sourced from the i18n catalogue so copy
      changes are localisable without touching this file.
    - The "primary" button per kind:
          terminal  → Reload page
          auth      → Sign in (emits 'signIn'; parent routes)
          credit    → Upgrade (emits 'upgrade'; parent opens modal)
          network   → Reconnect (emits 'reconnect')
          rate      → Try again (just dismiss — bridge auto-retries)
          policy    → no primary (the user has to rephrase)
          storage   → no primary (free space first)
          generic   → Try again (dismiss)
      Every kind also has a "Dismiss" secondary so the user can close
      the card and keep using the rest of the surface (e.g. read prior
      messages, copy text out) without forced action.

  Filename kept for git history continuity even though the scope grew
  beyond just disconnect — too many call-sites to rename.
-->
<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { Icon } from "@iconify/vue";

const props = defineProps<{ code: string }>();
const emit = defineEmits<{
  dismiss: [];
  reconnect: [];
  signIn: [];
  upgrade: [];
  reload: [];
}>();

const { t, te } = useI18n();

type Kind =
  | "terminal"
  | "auth"
  | "credit"
  | "network"
  | "rate"
  | "policy"
  | "storage"
  | "generic";

const kind = computed<Kind>(() => {
  switch (props.code) {
    case "session_kicked":
    case "too_many_chats":
    case "session_unknown":
    case "workspace_missing":
      return "terminal";
    case "setup_required":
    case "session_expired":
    case "provider_auth":
      return "auth";
    case "quota_exceeded":
    case "upgrade_required":
    case "provider_billing":
    case "provider_quota_exhausted":
      return "credit";
    case "ws_send_failed":
    case "not_connected":
    case "network":
    case "capacity":
    case "provider_network":
    case "provider_overloaded":
      return "network";
    case "rate_limit":
    case "provider_rate_limit":
    case "timeout":
    case "provider_timeout":
      return "rate";
    case "provider_safety_block":
    case "provider_usage_policy":
      return "policy";
    case "storage_full":
      return "storage";
    default:
      return "generic";
  }
});

const title = computed(() => {
  switch (props.code) {
    case "session_kicked":
      return "This tab was disconnected";
    case "too_many_chats":
      return "Too many chats open";
    case "session_unknown":
      return "Chat unavailable";
    case "workspace_missing":
      return "Folder unavailable";
    case "setup_required":
    case "session_expired":
    case "provider_auth":
      return "Sign-in needed";
    case "quota_exceeded":
    case "upgrade_required":
    case "provider_billing":
    case "provider_quota_exhausted":
      return "Plan limit reached";
    case "ws_send_failed":
      return "Couldn't send your message";
    case "not_connected":
    case "network":
    case "provider_network":
      return "Connection lost";
    case "capacity":
    case "provider_overloaded":
      return "Service is busy";
    case "rate_limit":
    case "provider_rate_limit":
      return "Slow down a moment";
    case "timeout":
    case "provider_timeout":
      return "That took too long";
    case "provider_safety_block":
      return "Response blocked by safety filter";
    case "provider_usage_policy":
      return "Blocked by usage policy";
    case "storage_full":
      return "Workspace is full";
    case "provider_context_too_large":
      return "Conversation too long";
    case "provider_model_unavailable":
      return "Model unavailable";
    case "provider_invalid_request":
      return "AI couldn't process that";
    case "aborted":
      return "Stopped";
    case "internal":
    case "provider_error":
    default:
      return "Something went wrong";
  }
});

const body = computed(() => {
  const key = `errors.${props.code}`;
  return te(key) ? (t(key) as string) : (t("errors.internal") as string);
});

// Multi-paragraph rendering. The locale strings use `\n\n` between
// paragraphs so we can author a long explanation without a wall of
// text in the markup.
const paragraphs = computed(() =>
  body.value.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean),
);

const icon = computed(() => {
  switch (kind.value) {
    case "terminal":
      return props.code === "too_many_chats"
        ? "codicon:multiple-windows"
        : "codicon:debug-disconnect";
    case "auth":
      return "codicon:key";
    case "credit":
      return "codicon:credit-card";
    case "network":
      return "codicon:debug-disconnect";
    case "rate":
      return "codicon:watch";
    case "policy":
      return "codicon:shield";
    case "storage":
      return "codicon:database";
    default:
      return "codicon:warning";
  }
});

// Tailwind palette per kind. Terminal/auth/credit get amber accents,
// network/rate amber too (recoverable, not panic), policy/storage
// muted, true unknowns get destructive red.
const accentClass = computed(() => {
  switch (kind.value) {
    case "policy":
    case "storage":
      return "border-muted-foreground/30 bg-muted/30 text-muted-foreground";
    case "generic":
      return "border-destructive/40 bg-destructive/10 text-destructive";
    default:
      return "border-amber-500/30 bg-amber-500/15 text-amber-400";
  }
});

const cardBorderClass = computed(() => {
  switch (kind.value) {
    case "policy":
    case "storage":
      return "border-border";
    case "generic":
      return "border-destructive/40";
    default:
      return "border-amber-500/30";
  }
});

const primaryAction = computed<{
  label: string;
  emitName: "reconnect" | "signIn" | "upgrade" | "reload" | "dismiss";
} | null>(() => {
  switch (kind.value) {
    case "terminal":
      return props.code === "too_many_chats"
        ? null
        : { label: "Reload page", emitName: "reload" };
    case "auth":
      return { label: "Sign in", emitName: "signIn" };
    case "credit":
      return { label: "Upgrade plan", emitName: "upgrade" };
    case "network":
      return { label: "Reconnect", emitName: "reconnect" };
    case "rate":
      return { label: "Try again", emitName: "dismiss" };
    case "generic":
      return { label: "Try again", emitName: "dismiss" };
    default:
      return null;
  }
});

function clickPrimary(): void {
  const a = primaryAction.value;
  if (!a) return;
  emit(a.emitName as never);
}
</script>

<template>
  <div
    class="absolute inset-0 z-30 flex items-end justify-center bg-background/70 px-4 pb-6 backdrop-blur-sm sm:items-center sm:pb-4"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="`err-card-title-${code}`"
  >
    <div
      class="w-full max-w-md rounded-xl border bg-card text-card-foreground shadow-2xl"
      :class="cardBorderClass"
    >
      <div class="flex items-start gap-3 px-5 pt-5">
        <div
          class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
          :class="accentClass"
        >
          <Icon :icon="icon" class="h-5 w-5" />
        </div>
        <div class="min-w-0 flex-1">
          <h2
            :id="`err-card-title-${code}`"
            class="text-lead font-semibold leading-snug text-foreground"
          >
            {{ title }}
          </h2>
          <div class="mt-2 space-y-2 text-body text-muted-foreground">
            <p
              v-for="(p, i) in paragraphs"
              :key="i"
              class="leading-relaxed"
            >
              {{ p }}
            </p>
          </div>
          <p class="mt-3 font-mono text-caption text-muted-foreground/70">
            error code: {{ code }}
          </p>
        </div>
        <button
          type="button"
          class="-m-1 ml-2 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Dismiss"
          @click="emit('dismiss')"
        >
          <Icon icon="codicon:close" class="h-4 w-4" />
        </button>
      </div>
      <div
        class="mt-5 flex flex-col-reverse items-stretch gap-2 border-t border-border px-5 py-3 sm:flex-row sm:justify-end"
      >
        <button
          type="button"
          class="rounded-md border border-border px-3 py-1.5 text-body text-foreground transition-colors hover:bg-muted"
          @click="emit('dismiss')"
        >
          Dismiss
        </button>
        <button
          v-if="primaryAction"
          type="button"
          class="rounded-md bg-primary px-4 py-1.5 text-body font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          @click="clickPrimary"
        >
          {{ primaryAction.label }}
        </button>
      </div>
    </div>
  </div>
</template>
