<!--
  ChatErrorBanner — bottom strip used for inline rate-limit / credit /
  websocket / generic chat errors.

  Renders one dismissible row with:
    • An icon that hints at the kind of error (auth ↔ key,
      network ↔ broken-link, server ↔ warning, …).
    • A friendly localised message — input is either a stable code
      (e.g. "ws_unauthorized") which we translate via
      `chat.error.<code>`, or pre-rendered free-form text (legacy /
      backend "_bridge_error" surfacing).
    • A primary action that depends on the kind:
        – credit_exhausted → "Upgrade" → opens UpgradeModal.
        – auth-class codes → "Sign in" RouterLink to /login.
        – network-class codes → "Reconnect" → @reconnect emit.
    • Dismiss ✕.

  This replaces the bare "websocket error" / "Something's not working"
  rows that used to leak raw English to the UI.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { Icon } from "@iconify/vue";

import UpgradeModal from "./UpgradeModal.vue";
import { useBillingStore } from "../stores/billing";

const props = defineProps<{ message: string; creditExhausted: boolean }>();
const emit = defineEmits<{
  dismiss: [];
  reconnect: [];
}>();

const billing = useBillingStore();
const { t, te } = useI18n();
const showUpgrade = ref(false);

// Stable code namespace: any string in `code` matching one of these
// triggers translation + the matching action button. Anything else
// is treated as already-translated free-form text (chat backend's
// `_bridge_error`, ApiError detail, …) and rendered as-is so we
// don't accidentally hide useful debug context for unknown errors.
const KNOWN_CODES = new Set([
  "ws_error",
  "ws_unauthorized",
  "ws_forbidden",
  "ws_kicked",
  "ws_too_many_chats",
  "ws_rate_limited",
  "ws_send_failed",
  "ws_unreachable",
]);

const isCode = computed(() => KNOWN_CODES.has(props.message));

const text = computed(() => {
  if (props.creditExhausted) {
    return te("chat.error.credit_exhausted")
      ? t("chat.error.credit_exhausted")
      : "You've used all of your monthly credit.";
  }
  if (isCode.value) {
    const key = `chat.error.${props.message}`;
    return te(key) ? t(key) : t("chat.error.generic");
  }
  return props.message;
});

type Kind = "auth" | "network" | "rate" | "credit" | "generic";

const kind = computed<Kind>(() => {
  if (props.creditExhausted) return "credit";
  if (!isCode.value) return "generic";
  switch (props.message) {
    case "ws_unauthorized":
    case "ws_forbidden":
      return "auth";
    case "ws_rate_limited":
      return "rate";
    case "ws_error":
    case "ws_unreachable":
    case "ws_send_failed":
      return "network";
    case "ws_kicked":
    case "ws_too_many_chats":
      return "generic";
    default:
      return "generic";
  }
});

const icon = computed(() => {
  switch (kind.value) {
    case "auth":
      return "codicon:key";
    case "network":
      return "codicon:debug-disconnect";
    case "rate":
      return "codicon:watch";
    case "credit":
      return "codicon:credit-card";
    default:
      return "codicon:warning";
  }
});

const actionLabel = computed(() => {
  switch (kind.value) {
    case "credit":
      return t("chat.error.action.upgrade");
    case "auth":
      return t("chat.error.action.signIn");
    case "network":
      return t("chat.error.action.reconnect");
    case "rate":
      return t("chat.error.action.reconnect");
    default:
      return null;
  }
});

// Per-kind theming. Red is reserved for real unknown errors only;
// credit is amber (upsell, not panic), auth is neutral muted, and
// transient network/rate states are also amber. This avoids the
// "scary red banner" effect for routine, recoverable conditions.
const themeClass = computed(() => {
  switch (kind.value) {
    case "credit":
      return "border-amber-500/30 bg-amber-500/[0.06] text-amber-200";
    case "rate":
    case "network":
      return "border-amber-500/30 bg-amber-500/[0.06] text-amber-200";
    case "auth":
      return "border-border bg-muted/40 text-foreground";
    default:
      return "border-rose-500/30 bg-rose-500/[0.06] text-rose-200";
  }
});

const primaryBtnClass = computed(() => {
  switch (kind.value) {
    case "credit":
      return "bg-primary text-primary-foreground hover:opacity-90";
    case "auth":
      return "bg-primary text-primary-foreground hover:opacity-90";
    case "network":
    case "rate":
      return "border border-amber-500/40 bg-amber-500/10 text-amber-100 hover:bg-amber-500/20";
    default:
      return "border border-rose-500/40 bg-rose-500/10 text-rose-100 hover:bg-rose-500/20";
  }
});
</script>

<template>
  <div
    class="flex items-start gap-2 border-t px-3 py-1.5 text-caption transition-colors"
    :class="themeClass"
    role="alert"
  >
    <Icon :icon="icon" class="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-80" />
    <span class="flex-1 leading-snug">{{ text }}</span>
    <div class="flex shrink-0 items-center gap-1.5">
      <button
        v-if="kind === 'credit'"
        type="button"
        class="rounded-md px-2.5 py-0.5 text-caption font-semibold tracking-wide"
        :class="primaryBtnClass"
        @click="showUpgrade = true"
      >
        {{ actionLabel }}
      </button>
      <RouterLink
        v-else-if="kind === 'auth'"
        to="/login"
        class="rounded-md px-2.5 py-0.5 text-caption font-semibold"
        :class="primaryBtnClass"
      >
        {{ actionLabel }}
      </RouterLink>
      <button
        v-else-if="actionLabel"
        type="button"
        class="rounded-md px-2.5 py-0.5 text-caption font-semibold"
        :class="primaryBtnClass"
        @click="emit('reconnect')"
      >
        {{ actionLabel }}
      </button>
      <button
        type="button"
        class="rounded px-1 text-body opacity-60 hover:bg-foreground/5 hover:opacity-100"
        :aria-label="t('common.cancel')"
        @click="emit('dismiss')"
      >
        ✕
      </button>
    </div>
    <UpgradeModal v-if="showUpgrade" :enabled="billing.enabled" @close="showUpgrade = false" />
  </div>
</template>
