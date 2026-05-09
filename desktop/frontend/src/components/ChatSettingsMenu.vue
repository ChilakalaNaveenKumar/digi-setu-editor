<!--
  ChatSettingsMenu — single gear-icon button in the chat header that
  consolidates per-chat settings + status into one popover. Replaces
  the previous always-on `[ permission ] [ model ] [ credit ]` row
  which crammed three chips + an emoji into the header and overflowed
  on narrow widths.

  What lives here:
    - Permission mode picker (auto / approve_risky / approve_all)
    - Plan + credit usage with progress bar + Upgrade button
    - Quick links to /pricing and "Open billing portal"

  What does NOT live here: the model picker. Model is changed often
  (per prompt) so it stays as a first-class control next to the gear.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { Icon } from "@iconify/vue";

import { apiJson, apiPatch } from "../api/client";
import { useBillingStore } from "../stores/billing";
import { useConfigStore } from "../stores/config";

import PermissionModePicker from "./PermissionModePicker.vue";
import UpgradeModal from "./UpgradeModal.vue";

const billing = useBillingStore();
const cfg = useConfigStore();
const {
  credit,
  remainingPct,
  lowCredit,
  enabled,
  exhausted,
  isAuthoritative,
  isByok,
} = storeToRefs(billing);
const { mode: deployMode } = storeToRefs(cfg);

const open = ref(false);
const showUpgrade = ref(false);
const root = ref<HTMLDivElement | null>(null);

// ── Routing default (BYOK vs Cloud) ──────────────────────────────────
// Surfaced ONLY when the backend reports byok_mode = true (i.e. there
// IS at least one BYOK key in ~/.digi-setu/.env). Otherwise every model
// is cloud-routed and this toggle is meaningless visual noise. Web
// mode also short-circuits (BYOK only exists for desktop today).
type RoutingDefault = "byok" | "cloud";
interface PrefsResponse {
  permission_mode: string;
  routing_default?: RoutingDefault;
  byok_mode?: boolean;
}
const routingDefault = ref<RoutingDefault | null>(null);
const byokModeAvailable = ref(false);
const routingUpdating = ref(false);

let pollHandle: number | null = null;

async function loadPrefs(): Promise<void> {
  try {
    const r = await apiJson<PrefsResponse>("/api/me/prefs");
    byokModeAvailable.value = !!r.byok_mode;
    if (r.routing_default === "byok" || r.routing_default === "cloud") {
      routingDefault.value = r.routing_default;
    }
  } catch (exc) {
    console.warn("[chat-settings] prefs load failed", exc);
  }
}

async function setRoutingDefault(value: RoutingDefault): Promise<void> {
  if (value === routingDefault.value || routingUpdating.value) return;
  routingUpdating.value = true;
  // Optimistic update — if the PATCH fails we roll back. The
  // server is authoritative, so the next /api/me/prefs poll
  // would correct any drift anyway.
  const previous = routingDefault.value;
  routingDefault.value = value;
  try {
    const r = await apiPatch<{ routing_default: RoutingDefault }>(
      "/api/me/prefs/routing_default",
      { value },
    );
    routingDefault.value = r.routing_default;
  } catch (exc) {
    console.warn("[chat-settings] routing default update failed", exc);
    routingDefault.value = previous;
  } finally {
    routingUpdating.value = false;
  }
}

const showRoutingToggle = computed(
  () => deployMode.value === "desktop" && byokModeAvailable.value,
);

onMounted(() => {
  void billing.refreshStatus();
  void billing.refreshUsage();
  void loadPrefs();
  // 30 s is enough — usage rarely changes outside an active turn,
  // and message_end already nudges the ledger live.
  pollHandle = window.setInterval(() => void billing.refreshUsage(), 30_000);
  document.addEventListener("click", onDocClick);
});

onUnmounted(() => {
  if (pollHandle !== null) window.clearInterval(pollHandle);
  document.removeEventListener("click", onDocClick);
});

function onDocClick(e: MouseEvent): void {
  if (!root.value) return;
  if (!root.value.contains(e.target as Node)) open.value = false;
}

const usageLabel = computed(() => {
  const c = credit.value;
  if (!c) return "…";
  if (isByok.value) return "Your key";
  const cap = c.plan.monthly_credit_usd ?? 0;
  // Suppress the loud "$0.00 of $0" pair when we don't have an
  // authoritative cloud reading yet — show an em-dash placeholder
  // and let the small "Sign in to see live usage" hint below carry
  // the explanation.
  if (!isAuthoritative.value && cap === 0) return "—";
  if (cap === 0) return `$${c.remaining_usd.toFixed(2)}`;
  return `$${c.remaining_usd.toFixed(2)} of $${cap.toFixed(0)}`;
});

const usageBarWidth = computed(() => {
  if (!isAuthoritative.value) return "0%";
  if ((credit.value?.plan?.monthly_credit_usd ?? 0) === 0) return "0%";
  const pct = Math.max(0, Math.min(100, 100 - remainingPct.value));
  return `${pct}%`;
});

// Calm three-state palette: muted by default, amber for low, rose for
// real exhaustion (only authoritative; see store). Reserved-red is
// out — running low isn't an error, it's a billing nudge.
const usageBarColor = computed(() => {
  if (exhausted.value) return "bg-rose-500/70";
  if (lowCredit.value) return "bg-amber-500/70";
  return "bg-primary/70";
});

const usageLabelColor = computed(() => {
  if (exhausted.value) return "text-rose-300";
  if (lowCredit.value) return "text-amber-200";
  return "text-muted-foreground";
});

const planLabel = computed(() => credit.value?.plan?.label || "Free");

// Dot on the gear icon — only fires for real authoritative low/exhausted
// states, not for the offline fallback (which would always be "0/0").
const showAlert = computed(() => exhausted.value || lowCredit.value);

const showSignInHint = computed(
  () => !isAuthoritative.value && !isByok.value,
);

function close(): void {
  open.value = false;
}

function openUpgrade(): void {
  close();
  showUpgrade.value = true;
}
</script>

<template>
  <div ref="root" class="relative inline-flex items-center">
    <button
      type="button"
      class="relative flex h-6 w-6 items-center justify-center rounded border border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
      :class="open ? 'text-foreground' : ''"
      :title="`Chat settings · ${planLabel} ${usageLabel}`"
      @click="open = !open"
    >
      <Icon icon="codicon:settings-gear" class="h-[14px] w-[14px]" />
      <span
        v-if="showAlert"
        class="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full"
        :class="exhausted ? 'bg-rose-400' : 'bg-amber-400'"
        aria-hidden="true"
      />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-full z-30 mt-1 w-80 rounded border border-border bg-popover shadow-lg"
    >
      <!-- Permission mode -->
      <div class="border-b border-border px-3 py-2.5">
        <div class="mb-1.5 flex items-baseline justify-between">
          <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            permissions
          </span>
        </div>
        <PermissionModePicker />
        <p class="mt-1.5 text-caption leading-tight text-muted-foreground">
          Controls when pi asks before running tools. Audit trail is
          always recorded.
        </p>
      </div>

      <!-- Routing default (BYOK vs Cloud). Only surfaces when the
           desktop sidecar booted with at least one BYOK key in
           ~/.digi-setu/.env — see services/byok.py. The model picker
           still allows per-chat overrides; this toggle just sets the
           default when starting a fresh chat. -->
      <div v-if="showRoutingToggle" class="border-b border-border px-3 py-2.5">
        <div class="mb-1.5 flex items-baseline justify-between">
          <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            default ai source
          </span>
        </div>
        <div class="flex gap-1 rounded-md border border-border bg-background p-0.5">
          <button
            type="button"
            class="flex-1 rounded px-2 py-1 text-caption font-mono transition-colors disabled:opacity-50"
            :class="
              routingDefault === 'byok'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            "
            :disabled="routingUpdating"
            title="Use the AI keys you put in ~/.digi-setu/.env. Billed by your provider directly — no Digi Setu charge."
            @click="setRoutingDefault('byok')"
          >
            My keys
          </button>
          <button
            type="button"
            class="flex-1 rounded px-2 py-1 text-caption font-mono transition-colors disabled:opacity-50"
            :class="
              routingDefault === 'cloud'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            "
            :disabled="routingUpdating"
            title="Use Digi Setu cloud-relay models. Billed against your subscription credit."
            @click="setRoutingDefault('cloud')"
          >
            Cloud subscription
          </button>
        </div>
        <p class="mt-1.5 text-caption leading-tight text-muted-foreground">
          New chats start with a model from this source. The model picker
          can override per chat.
        </p>
      </div>

      <!-- Credit / plan -->
      <div class="border-b border-border px-3 py-2.5">
        <div class="mb-1.5 flex items-baseline justify-between">
          <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            credit · {{ planLabel.toLowerCase() }}
          </span>
          <span
            class="font-mono text-caption tabular-nums"
            :class="usageLabelColor"
          >
            {{ usageLabel }}
          </span>
        </div>
        <!-- thin progress bar so the gauge doesn't shout when it's 90%
             empty but still draws the eye when it's almost full. -->
        <div class="h-1 overflow-hidden rounded-full bg-muted">
          <div
            class="h-full transition-[width] duration-300"
            :class="usageBarColor"
            :style="{ width: usageBarWidth }"
          />
        </div>
        <p
          v-if="showSignInHint"
          class="mt-1.5 text-caption leading-tight text-muted-foreground"
        >
          Sign in to see your live plan and usage.
        </p>
        <div class="mt-2 flex items-center gap-2">
          <button
            type="button"
            class="flex-1 rounded border border-border bg-background px-2 py-1 font-mono text-caption hover:bg-muted"
            @click="openUpgrade"
          >
            Upgrade
          </button>
          <RouterLink
            to="/pricing"
            class="flex-1 rounded border border-border bg-background px-2 py-1 text-center font-mono text-caption text-foreground hover:bg-muted"
            @click="close"
          >
            See plans
          </RouterLink>
        </div>
      </div>

      <!-- Footer hint -->
      <div class="px-3 py-2 text-caption leading-tight text-muted-foreground">
        Settings live next to the model picker so you don't lose visual
        space in the chat. Open this menu any time to change permission
        or check usage.
      </div>
    </div>
  </div>

  <UpgradeModal v-if="showUpgrade" :enabled="enabled" @close="showUpgrade = false" />
</template>
