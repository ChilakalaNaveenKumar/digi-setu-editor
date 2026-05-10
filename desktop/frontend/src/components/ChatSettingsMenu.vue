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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { Icon } from "@iconify/vue";

import { apiJson, apiPatch } from "../api/client";
import { useBillingStore } from "../stores/billing";
import { useConfigStore } from "../stores/config";
import { useWorkspaceStore } from "../stores/workspace";

import PermissionModePicker from "./PermissionModePicker.vue";
import StorageCleanupSection from "./StorageCleanupSection.vue";
import UpgradeModal from "./UpgradeModal.vue";

const billing = useBillingStore();
const cfg = useConfigStore();
const workspace = useWorkspaceStore();
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
const triggerRef = ref<HTMLButtonElement | null>(null);
const popoverRef = ref<HTMLDivElement | null>(null);

// Same fixed-position-via-Teleport trick PermissionModePicker /
// ModelPicker use, for the same two reasons:
//   1. The composer toolbar where this gear lives is at the BOTTOM of
//      the chat pane. Opening downward (the previous absolute top-full
//      behaviour) pushed the popover off-screen and the user couldn't
//      reach the credit / upgrade controls.
//   2. The chat pane has overflow-hidden, so any absolutely-positioned
//      child that needs to escape the pane's clip box has to be
//      teleported to <body> with fixed coordinates.
//
// Flip rule mirrors the other pickers: prefer up when there's not
// enough room below AND there's more room above.
const popoverStyle = ref<Record<string, string>>({});
function reposition(): void {
  const t = triggerRef.value;
  if (!t) return;
  const rect = t.getBoundingClientRect();
  const margin = 8;
  const desiredWidth = 320;
  // Estimated content height — permissions + (optional) routing toggle
  // + credit + storage cleanup section + footer. We've grown over time;
  // the popover scrolls internally when this is exceeded so an
  // overestimate just shows a tighter scroll handle.
  const desiredHeight = 560;
  const width = Math.min(desiredWidth, window.innerWidth - margin * 2);
  let left = rect.right - width;
  if (left < margin) left = margin;
  if (left + width > window.innerWidth - margin) {
    left = window.innerWidth - margin - width;
  }
  const spaceBelow = window.innerHeight - rect.bottom - margin;
  const spaceAbove = rect.top - margin;
  const flipUp = spaceBelow < desiredHeight && spaceAbove > spaceBelow;
  if (flipUp) {
    popoverStyle.value = {
      position: "fixed",
      top: "auto",
      bottom: `${window.innerHeight - rect.top + 4}px`,
      left: `${left}px`,
      width: `${width}px`,
      maxHeight: `${Math.min(desiredHeight, spaceAbove)}px`,
    };
    return;
  }
  popoverStyle.value = {
    position: "fixed",
    top: `${rect.bottom + 4}px`,
    left: `${left}px`,
    width: `${width}px`,
    maxHeight: `${Math.min(desiredHeight, spaceBelow)}px`,
  };
}

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
  // Same capture-phase listeners the other pickers use so we
  // re-anchor when ANY ancestor scrolls (chat pane scroll, page
  // scroll on smaller viewports), not just the document.
  window.addEventListener("resize", reposition);
  window.addEventListener("scroll", reposition, true);
});

onUnmounted(() => {
  if (pollHandle !== null) window.clearInterval(pollHandle);
  document.removeEventListener("click", onDocClick);
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
});

watch(open, async (v) => {
  if (!v) return;
  await nextTick();
  reposition();
});

function onDocClick(e: MouseEvent): void {
  // Click outside both the trigger AND the teleported popover closes.
  // Without checking the popover too, clicking inside the popover
  // (e.g. the permission-mode buttons) would close the parent menu
  // out from under the user.
  const t = triggerRef.value;
  const p = popoverRef.value;
  const target = e.target as Node;
  if (t && t.contains(target)) return;
  if (p && p.contains(target)) return;
  open.value = false;
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
  <div class="relative inline-flex items-center">
    <button
      ref="triggerRef"
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

    <Teleport to="body">
      <div
        v-if="open"
        ref="popoverRef"
        :style="popoverStyle"
        class="z-[60] flex flex-col overflow-hidden rounded-md border border-border bg-popover shadow-xl ring-1 ring-black/10"
      >
        <div class="flex-1 overflow-y-auto">
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

          <!-- Per-workspace storage cleanup (chats, audits, uploads,
               shadows). Surfaces only when there's an active workspace
               id — opening the menu before picking a workspace would
               give us nothing to clean. -->
          <StorageCleanupSection
            v-if="workspace.activeId"
            :wsid="workspace.activeId"
          />

          <!-- Footer hint -->
          <div class="px-3 py-2 text-caption leading-tight text-muted-foreground">
            Settings live next to the composer so you don't lose visual
            space in the chat. Open this menu any time to change
            permission or check usage.
          </div>
        </div>
      </div>
    </Teleport>
  </div>

  <UpgradeModal v-if="showUpgrade" :enabled="enabled" @close="showUpgrade = false" />
</template>
