<!--
  ModelPicker — compact, Cursor-style model dropdown for the chat header.

  Design rules:
    1. Trigger button shows just the model name. No price, no blurb, no
       chevron eating space — the chat pane is narrow on purpose.
    2. The dropdown is teleported to <body> and positioned via fixed
       coordinates anchored to the trigger's bounding rect. This is the
       only way to render outside the chat pane's clipping box; without
       it, the popup gets cut by the narrow column on the left and looks
       broken (see the screenshots from earlier feedback).
    3. Search box on top — type-ahead is the fastest way to land on a
       model when the catalogue grows past ~5 entries.
    4. Each row: family icon · model name · "Fast/Medium/Smart" intelligence
       pill · ✓ if active. No prices in the list itself; the row's
       title attribute exposes price + blurb on hover. Locked rows get a
       subtle "PRO" tag instead.
    5. Switching a model takes effect on the *next* prompt; the running
       pi keeps its spawned model. We don't dramatize that here — the
       dot in the header (handled elsewhere) is enough.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { Icon } from "@iconify/vue";

import type { ModelInfo } from "../api/types";
import { useBillingStore } from "../stores/billing";
import { useChatStore } from "../stores/chat";
import { useModelsStore } from "../stores/models";

const models = useModelsStore();
const chat = useChatStore();
const billing = useBillingStore();
const { catalogue, activeModelId, activeModelName, byokMode } = storeToRefs(models);
const { enabled: billingEnabled } = storeToRefs(billing);

const open = ref(false);
const triggerRef = ref<HTMLButtonElement | null>(null);
const dropdownRef = ref<HTMLDivElement | null>(null);
const searchRef = ref<HTMLInputElement | null>(null);
const search = ref("");
const highlightId = ref<string | null>(null);

// Computed inline style for the floating dropdown. We anchor to the
// trigger's right edge (so it grows leftwards into the chat pane) but
// clamp to the viewport with an 8 px gutter on either side.
//
// Flip-up rule: this picker now lives in the composer toolbar at the
// bottom of the chat pane (it used to live in the header). Opening
// downward from there leaves it almost no room and clips the catalogue
// to one or two visible rows. Mirror the heuristic from
// PermissionModePicker — flip up when there's less than `desiredHeight`
// below AND more room above than below.
const popoverStyle = ref<Record<string, string>>({});
function reposition(): void {
  const t = triggerRef.value;
  if (!t) return;
  const rect = t.getBoundingClientRect();
  const margin = 8;
  const desiredWidth = 280;
  // 420 lets us show ~10 model rows + family headers + search + footer
  // without scrolling, which covers the current catalogue. Larger
  // catalogues will scroll inside the popover, so this is a soft
  // preference, not a hard requirement.
  const desiredHeight = 420;
  const availW = window.innerWidth - margin * 2;
  const width = Math.min(desiredWidth, availW);
  // Align right edge to the trigger's right edge.
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

onMounted(() => {
  void models.refresh();
  document.addEventListener("click", onDocClick);
  window.addEventListener("resize", reposition);
  window.addEventListener("scroll", reposition, true);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocClick);
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
});

function onDocClick(e: MouseEvent): void {
  const t = triggerRef.value;
  const d = dropdownRef.value;
  const target = e.target as Node;
  if (t && t.contains(target)) return;
  if (d && d.contains(target)) return;
  open.value = false;
}

watch(open, async (v) => {
  if (v) {
    await nextTick();
    reposition();
    searchRef.value?.focus();
    // Pre-highlight the active model so Enter picks it (a no-op but
    // confirms the user intended to keep it).
    highlightId.value = activeModelId.value || filtered.value[0]?.id || null;
  } else {
    search.value = "";
  }
});

const buttonLabel = computed(() => activeModelName.value || "select model");

// Group label only used for the screen-reader tag inside each row.
const familyLabels: Record<string, string> = {
  anthropic: "Anthropic",
  google: "Google",
};

const familyIcons: Record<string, string> = {
  // No emoji — codicon glyphs match the rest of the IDE chrome.
  anthropic: "codicon:sparkle",
  google: "codicon:circuit-board",
};

// Heuristic intelligence/speed badge derived from output cost. The
// catalogue has a `reasoning` flag for cot-style models, but cost ends
// up being the more honest proxy for "how slow & smart will this be".
function intelligenceBadge(m: ModelInfo): { label: string; class: string } {
  const out = m.cost_per_mtok_output;
  if (out >= 50) return { label: "Smartest", class: "text-fuchsia-400/90" };
  if (out >= 14) return { label: "Smart", class: "text-violet-400/90" };
  if (out >= 5) return { label: "Balanced", class: "text-sky-400/90" };
  return { label: "Fast", class: "text-emerald-400/90" };
}

function tooltipFor(m: ModelInfo): string {
  const price = `$${m.cost_per_mtok_input.toFixed(2)} / $${m.cost_per_mtok_output.toFixed(2)} per Mtok`;
  const lock = m.available ? "" : ` · requires ${m.min_plan.toUpperCase()}`;
  // Surface the routing path in BYOK-eligible deployments. We do
  // this in the title attribute (not as inline text) because the
  // dropdown row is already dense; users only need the detail when
  // they pause to read it.
  const route = m.route === "byok"
    ? "\nroute: your key (BYOK) — billed by your AI provider directly"
    : m.route === "cloud" && byokMode.value
      ? "\nroute: cloud relay — billed against your Digi Setu subscription"
      : "";
  return `${m.name} · ${price}${lock}\n${m.blurb}${route}`;
}

/**
 * Compact badge for the route column. Returned only when the user
 * has at least one BYOK key configured (otherwise every model is
 * cloud and the badge would just be noise).
 */
function routeBadge(m: ModelInfo): { label: string; class: string } | null {
  if (!byokMode.value) return null;
  if (m.route === "byok") {
    return {
      label: "BYOK",
      class: "border-success/40 bg-success/10 text-success",
    };
  }
  return {
    label: "CLOUD",
    class: "border-border bg-muted text-muted-foreground",
  };
}

const filtered = computed<ModelInfo[]>(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return catalogue.value;
  return catalogue.value.filter(
    (m) =>
      m.name.toLowerCase().includes(q) ||
      m.id.toLowerCase().includes(q) ||
      (familyLabels[m.family] || "").toLowerCase().includes(q),
  );
});

// Group filtered results by family for the visual hierarchy. We keep the
// family headers because Anthropic vs Google is a meaningful distinction
// (different rate limits, different token accounting).
const filteredGrouped = computed<{ family: string; models: ModelInfo[] }[]>(() => {
  const groups = new Map<string, ModelInfo[]>();
  for (const m of filtered.value) {
    if (!groups.has(m.family)) groups.set(m.family, []);
    groups.get(m.family)!.push(m);
  }
  return Array.from(groups.entries()).map(([family, models]) => ({ family, models }));
});

function moveHighlight(delta: number): void {
  const list = filtered.value;
  if (list.length === 0) return;
  const idx = list.findIndex((m) => m.id === highlightId.value);
  const next = idx === -1 ? 0 : (idx + delta + list.length) % list.length;
  highlightId.value = list[next].id;
}

// Cloud-model gate. In BYOK mode without a billing account we
// cannot route a chat through our cloud relay (no auth, no way
// to bill). Surface an upgrade nudge instead of silently failing
// at chat-start. Backend has the same gate as a defence in depth
// — see chat_ws.py `BYOK gate`.
const cloudGateMessage = ref<string | null>(null);
const cloudGateModel = ref<ModelInfo | null>(null);

function shouldGateCloud(m: ModelInfo): boolean {
  if (!byokMode.value) return false;
  if (m.route !== "cloud") return false;
  // billingEnabled is true when the backend has Stripe + Clerk
  // wired AND the user is signed in. In that state cloud-relay
  // works fine, so don't gate. In BYOK-only desktop launches the
  // ledger reports enabled=false, which is exactly when we want
  // to nudge.
  return !billingEnabled.value;
}

async function onPick(m: ModelInfo): Promise<void> {
  if (!m.available) return;
  if (shouldGateCloud(m)) {
    cloudGateModel.value = m;
    cloudGateMessage.value = (
      `${m.name} runs on Digi Setu's cloud relay. ` +
      `Pick a model badged BYOK to use the keys in ~/.digi-setu/.env, ` +
      `or sign in / subscribe to use cloud models.`
    );
    open.value = false;
    return;
  }
  open.value = false;
  const sid = chat.session?.id;
  if (!sid) return;
  try {
    // Skip the round trip if the user re-picked the active model; nothing
    // to do and a respawn would just disrupt the current pi for no reason.
    if (m.id === models.activeModelId) return;
    await models.pickForSession(sid, m.id);
    // Persisting the new pin in the registry isn't enough on its own —
    // pi keeps whatever model it spawned with. Recycle the WS so pi
    // respawns and the next prompt actually uses the new model. The
    // chat store's `reconnect()` aborts any in-flight stream first.
    await chat.reconnect();
  } catch (exc) {
    console.warn("[picker] set model failed", exc);
  }
}

function onKeyDown(e: KeyboardEvent): void {
  if (!open.value) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    moveHighlight(1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    moveHighlight(-1);
  } else if (e.key === "Enter") {
    e.preventDefault();
    const target = filtered.value.find((m) => m.id === highlightId.value);
    if (target) void onPick(target);
  } else if (e.key === "Escape") {
    e.preventDefault();
    open.value = false;
  }
}
</script>

<template>
  <div class="relative inline-flex items-center" v-if="catalogue.length > 0">
    <button
      ref="triggerRef"
      type="button"
      class="flex max-w-[180px] items-center gap-1 truncate rounded border border-border bg-background px-2 py-0.5 text-caption font-mono text-foreground hover:bg-muted"
      :title="`active model: ${activeModelId ?? buttonLabel}`"
      @click="open = !open"
    >
      <span class="truncate">{{ buttonLabel }}</span>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="dropdownRef"
        :style="popoverStyle"
        class="z-50 flex flex-col overflow-hidden rounded-md border border-border bg-popover text-foreground shadow-xl ring-1 ring-black/10"
        role="listbox"
        @keydown="onKeyDown"
      >
        <!-- Search row -->
        <div class="flex items-center gap-2 border-b border-border px-2.5 py-1.5">
          <Icon icon="codicon:search" class="h-3 w-3 shrink-0 text-muted-foreground" />
          <input
            ref="searchRef"
            v-model="search"
            type="text"
            class="w-full bg-transparent font-mono text-caption text-foreground placeholder:text-muted-foreground focus:outline-none"
            placeholder="Search models…"
            @keydown="onKeyDown"
          />
        </div>

        <!-- Results -->
        <div class="flex-1 overflow-y-auto py-1">
          <div
            v-if="filtered.length === 0"
            class="px-3 py-6 text-center font-mono text-caption text-muted-foreground"
          >
            No matches
          </div>

          <template v-for="group in filteredGrouped" :key="group.family">
            <div
              v-if="filteredGrouped.length > 1 || !search"
              class="px-2.5 pb-0.5 pt-1.5 font-mono text-caption uppercase tracking-wide text-muted-foreground/70"
            >
              {{ familyLabels[group.family] || group.family }}
            </div>
            <button
              v-for="m in group.models"
              :key="m.id"
              type="button"
              role="option"
              :aria-selected="m.id === activeModelId"
              class="flex w-full items-center gap-2 px-2.5 py-1.5 text-left font-mono text-caption disabled:cursor-not-allowed"
              :class="[
                m.id === highlightId ? 'bg-muted' : '',
                m.available ? 'hover:bg-muted' : 'opacity-55',
              ]"
              :title="tooltipFor(m)"
              :disabled="!m.available"
              @click="onPick(m)"
              @mouseenter="highlightId = m.id"
            >
              <Icon
                :icon="familyIcons[m.family] || 'codicon:circle-outline'"
                class="h-3 w-3 shrink-0 text-muted-foreground"
              />
              <span class="flex-1 truncate">{{ m.name }}</span>
              <span
                v-if="routeBadge(m)"
                class="shrink-0 rounded border px-1 py-px font-mono text-caption uppercase tracking-wide"
                :class="routeBadge(m)!.class"
              >{{ routeBadge(m)!.label }}</span>
              <span
                class="shrink-0 text-caption"
                :class="intelligenceBadge(m).class"
              >
                {{ intelligenceBadge(m).label }}
              </span>
              <Icon
                v-if="m.id === activeModelId"
                icon="codicon:check"
                class="h-3 w-3 shrink-0 text-success"
              />
              <span
                v-else-if="!m.available"
                class="shrink-0 rounded border border-border px-1 py-px font-mono text-caption uppercase text-muted-foreground"
              >{{ m.min_plan }}</span>
            </button>
          </template>
        </div>

        <!-- Footer hint — keeps the rows themselves uncluttered -->
        <div class="border-t border-border px-2.5 py-1 font-mono text-caption text-muted-foreground">
          ↑↓ navigate · ↵ pick · esc close · hover for price
        </div>
      </div>
    </Teleport>

    <!-- Upgrade modal (BYOK-only desktop trying to pick a cloud model).
         Kept inline here rather than reusing UpgradeModal because the
         copy is BYOK-specific — we want to clearly say "pick a BYOK
         model OR subscribe" rather than the generic "you're out of
         credit" pitch. -->
    <Teleport to="body">
      <div
        v-if="cloudGateMessage"
        class="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4"
        @click="cloudGateMessage = null"
      >
        <div
          class="w-full max-w-md rounded-lg border border-border bg-card p-5 shadow-2xl"
          @click.stop
        >
          <div class="mb-2 flex items-center gap-2">
            <Icon icon="codicon:cloud" class="h-5 w-5 text-warning" />
            <h2 class="text-lead font-semibold text-foreground">Cloud model selected</h2>
          </div>
          <p class="text-body leading-relaxed text-muted-foreground">{{ cloudGateMessage }}</p>
          <div class="mt-4 flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-md border border-border bg-background px-3 py-1.5 text-caption text-foreground hover:bg-muted"
              @click="cloudGateMessage = null"
            >
              Pick a different model
            </button>
            <RouterLink
              to="/pricing"
              class="rounded-md bg-primary px-3 py-1.5 text-caption font-semibold text-primary-foreground hover:opacity-90"
              @click="cloudGateMessage = null"
            >
              See plans
            </RouterLink>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
