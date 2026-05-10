<!--
  StorageCycleBanner — slim notice that appears 5 days before the
  rolling 90-day auto-cleanup sweep on web.

  Why this exists
  ---------------
  Web's storage policy is rolling — every 90 days, sweep all chats,
  audit rows, and uploads older than the cycle window. The user
  wanted explicit warning before that happens, so the SPA polls
  /api/storage/cycle on load and renders this banner when:
    * cycle is within `banner_lead_days` of being due, AND
    * there's actually pending data to clean (zero-content sweeps
      are silent — no point warning about them).

  What the user can do from here
  ------------------------------
    * "Clean now" → POST /api/storage/cycle/run with force=true.
      Runs immediately, banner disappears.
    * "Snooze" → just close the banner. The sweep STILL fires when
      due (auto-cleanup is the documented behavior); we only
      remember the dismiss locally so the banner doesn't keep
      re-appearing on every nav within the same session. The next
      page load after the cycle fires will pull a fresh state with
      `show_banner: false`, so the snooze doesn't outlive the sweep.

  We deliberately don't offer "skip this cycle" or "extend by 30
  days" — keeping the policy non-negotiable means the user knows
  exactly what'll happen, instead of having to reason about a
  per-account snooze counter.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";

import {
  getStorageCycle,
  runStorageCycle,
  type CycleStatus,
} from "../api/sessions";

const status = ref<CycleStatus | null>(null);
const dismissed = ref(false);
const cleaning = ref(false);
const error = ref<string | null>(null);

async function load(): Promise<void> {
  try {
    status.value = await getStorageCycle();
  } catch (exc) {
    // The banner is decorative — failing to fetch the cycle should
    // never break the rest of the SPA. We log + stay hidden.
    console.warn("[storage-cycle] load failed", exc);
    status.value = null;
  }
}

onMounted(load);

const visible = computed(() => {
  if (dismissed.value) return false;
  if (!status.value) return false;
  if (!status.value.show_banner) return false;
  // Don't bother the user if there's literally nothing to clean.
  if (status.value.pending.total_count === 0) return false;
  return true;
});

const headline = computed(() => {
  const s = status.value;
  if (!s) return "";
  if (s.days_until_cycle === 0) {
    return "Storage cleanup running soon";
  }
  if (s.days_until_cycle === 1) {
    return "Storage cleanup tomorrow";
  }
  return `Storage cleanup in ${s.days_until_cycle} days`;
});

const detail = computed(() => {
  const s = status.value;
  if (!s) return "";
  const p = s.pending;
  const parts: string[] = [];
  if (p.chats.count > 0) parts.push(`${p.chats.count} old chats`);
  if (p.audits.count > 0) parts.push(`${p.audits.count} audit rows`);
  if (p.uploads.count > 0) parts.push(`${p.uploads.count} attachments`);
  if (parts.length === 0) return "";
  return `Will remove ${parts.join(", ")} (~${fmtBytes(p.total_bytes)})`;
});

async function cleanNow(): Promise<void> {
  if (cleaning.value) return;
  cleaning.value = true;
  error.value = null;
  try {
    await runStorageCycle(true);
    await load();
    // After a successful run, ``show_banner`` flips false (next cycle
    // is now ~90 days out) so ``visible`` will be false on its own —
    // no need to manually set ``dismissed``.
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "cleanup failed";
  } finally {
    cleaning.value = false;
  }
}

function dismiss(): void {
  dismissed.value = true;
}

function fmtBytes(n: number): string {
  if (n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v >= 10 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}
</script>

<template>
  <div
    v-if="visible"
    class="flex items-center gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-1.5 text-caption text-amber-100"
    role="status"
  >
    <Icon icon="codicon:info" class="h-3.5 w-3.5 shrink-0" />
    <div class="flex-1 min-w-0">
      <span class="font-medium">{{ headline }}.</span>
      <span v-if="detail" class="text-amber-200/80"> {{ detail }}</span>
      <span v-if="error" class="ml-2 text-rose-300">· {{ error }}</span>
    </div>
    <button
      type="button"
      class="rounded border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 font-mono text-caption transition-colors hover:border-amber-400 hover:bg-amber-500/25 disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="cleaning"
      @click="cleanNow"
    >
      <span v-if="cleaning">Cleaning…</span>
      <span v-else>Clean now</span>
    </button>
    <button
      type="button"
      class="rounded p-0.5 text-amber-100/70 hover:bg-amber-500/20 hover:text-amber-50"
      title="Dismiss for this session"
      @click="dismiss"
    >
      <Icon icon="codicon:chrome-close" class="h-3 w-3" />
    </button>
  </div>
</template>
