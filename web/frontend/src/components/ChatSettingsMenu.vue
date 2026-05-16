<!--
  ChatSettingsMenu — single gear-icon button in the chat header that
  consolidates per-chat settings + status into one popover. Replaces
  the previous always-on `[ permission ] [ model ] [ credit ]` row
  which crammed three chips + an emoji into the header and overflowed
  on narrow widths.

  What lives here:
    - Plan + credit usage with progress bar + Upgrade button
    - Routing default (BYOK vs cloud), only when byok keys exist
    - Quick links to /pricing and "Open billing portal"
    - Manage skills modal trigger

  What used to live here but doesn't anymore:
    - Permission mode picker. Web runs pi inside our sandbox
      container, so tool calls are safe by construction and the
      modal-prompt UX has zero upside — it can only stall the chat
      behind a hidden prompt. Locked to `approve_all` server-side
      (see web/backend/services/user_prefs.py).

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

import SkillsModal from "./SkillsModal.vue";
import UpgradeModal from "./UpgradeModal.vue";

const billing = useBillingStore();
const cfg = useConfigStore();
const { credit, remainingPct, lowCredit, enabled } = storeToRefs(billing);
// `cfg` is referenced here for future feature flags (e.g. plan-aware
// chrome). Reading it pulls the store into the dep graph for HMR.
void cfg;

const open = ref(false);
const showUpgrade = ref(false);
const showSkills = ref(false);
const triggerRef = ref<HTMLButtonElement | null>(null);
const popoverRef = ref<HTMLDivElement | null>(null);

// Same fixed-position-via-Teleport trick ModelPicker uses, for the
// same two reasons:
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
  // Estimated content height — permissions row + credit row + footer
  // hint. Used for flip detection AND the maxHeight clamp so the
  // popover never spills off-screen.
  const desiredHeight = 360;
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

// BYOK + the BYOK/Cloud routing toggle are desktop-only features.
// The web edition always runs cloud-routed, so this toggle is
// permanently hidden here. (The desktop hard-fork has its own version
// of this component that flips this on when byok_mode is true.)
const showRoutingToggle = computed(() => false);

onMounted(() => {
  void loadPrefs();
  document.addEventListener("click", onDocClick);
  // Same capture-phase listeners the other pickers use so we
  // re-anchor when ANY ancestor scrolls (chat pane scroll, page
  // scroll on smaller viewports), not just the document.
  window.addEventListener("resize", reposition);
  window.addEventListener("scroll", reposition, true);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocClick);
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
});

// We deliberately do NOT keep a setInterval polling /api/usage.
// Earlier builds fired refreshUsage every 30 seconds while the
// chat was visible; for a power user with 8 tabs open that meant
// ~14k unnecessary cloud round-trips a day, all to refresh a
// number that nothing reads until the user clicks the gear.
// Instead: fetch on click. The popover opens, we hit /api/usage
// + /api/billing/status once, and the numbers are correct for
// the entire time the popover is visible. Closing it cancels any
// in-flight refresh next time round.
watch(open, async (v) => {
  if (!v) return;
  // Fire-and-forget — `refreshStatus` reads the plan catalogue
  // (cached server-side, ~1 ms) and `refreshUsage` reads the
  // credit gauge. Both writes go through the shared billing
  // store, so any other surface watching them updates too.
  void billing.refreshStatus();
  void billing.refreshUsage();
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
  if (!c) return "loading…";
  return `$${c.remaining_usd.toFixed(2)} of $${c.plan.monthly_credit_usd.toFixed(0)}`;
});

const usageBarWidth = computed(() => {
  const pct = Math.max(0, Math.min(100, 100 - remainingPct.value));
  return `${pct}%`;
});

const usageBarColor = computed(() => {
  if (!credit.value) return "bg-muted";
  if (credit.value.remaining_usd <= 0) return "bg-destructive";
  if (lowCredit.value) return "bg-warning";
  return "bg-primary";
});

const planLabel = computed(() => credit.value?.plan?.label || "Free");

// Subtle red dot on the gear when credit is below the warning threshold,
// so users notice without us having to keep the chip in the header.
const showAlert = computed(
  () => !!credit.value && (credit.value.remaining_usd <= 0 || lowCredit.value),
);

function close(): void {
  open.value = false;
}

function openUpgrade(): void {
  close();
  showUpgrade.value = true;
}

function openSkills(): void {
  close();
  showSkills.value = true;
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
        :class="credit && credit.remaining_usd <= 0 ? 'bg-destructive' : 'bg-warning'"
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
      <!--
        Permission mode picker removed on web in 2026-05-16. Backend
        locks the mode to `approve_all` for every user — pi runs in
        our sandbox container so there's no host-side surface to
        prompt about. See web/backend/services/user_prefs.py
        (`DEFAULT_PERMISSION_MODE` doc comment).
      -->

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
            class="font-mono text-caption"
            :class="
              credit && credit.remaining_usd <= 0
                ? 'text-destructive'
                : lowCredit
                ? 'text-warning'
                : 'text-muted-foreground'
            "
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

          <!-- Skills -->
          <div class="border-b border-border px-3 py-2.5">
            <div class="mb-1.5 flex items-baseline justify-between">
              <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
                skills
              </span>
            </div>
            <button
              type="button"
              class="flex w-full items-center justify-between rounded border border-border bg-background px-2 py-1 text-body hover:bg-muted"
              @click="openSkills"
            >
              <span>Manage skills</span>
              <Icon icon="codicon:arrow-right" class="h-3.5 w-3.5 text-muted-foreground" />
            </button>
            <p class="mt-1.5 text-caption leading-tight text-muted-foreground">
              Markdown docs that extend pi. Reference inline with
              <code class="rounded bg-muted px-1">@name</code>.
            </p>
          </div>

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

  <SkillsModal v-if="showSkills" @close="showSkills = false" />
  <UpgradeModal v-if="showUpgrade" :enabled="enabled" @close="showUpgrade = false" />
</template>
