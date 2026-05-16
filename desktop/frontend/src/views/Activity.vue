<!--
  Activity — per-user event log of every billable LLM call.

  Answers the question "where did my $2 free credit go?". Each row is
  one call to a provider (parent chat turn or a sub-LLM tool call like
  search_docs / web_search). Newest first.

  We deliberately don't add charts here — the data is line-item
  receipts, not aggregated analytics. The credit-remaining banner up
  top is the at-a-glance summary; the table is the audit trail.

  ─── Data fetching strategy (no polling, rewritten 2026-05-16) ─────
  The page never schedules a timer. The user gets:

    1. Initial load    → GET /api/usage/events?limit=100   (last 100)
    2. Manual refresh  → GET …?limit=100, "Refresh" button.
    3. "Load older"    → GET …?before=<oldest_ts>&limit=100 (APPEND)
                         cursor-based pagination; hides itself when
                         the server says no more pages.

  Earlier builds also ran a 30 s `pollNew` interval that pulled
  `?since=<newest>` increments. Removed — the table is an audit
  log, not a live feed, and the polling created a steady stream of
  background traffic for a number nothing was watching most of the
  time.

  Same shape mirrored on the BYOK table.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";

import AppFooter from "../components/AppFooter.vue";
import {
  getByokUsage,
  getUsage,
  getUsageEvents,
  type ByokEvent,
  type ByokSummary,
  type UsageEvent,
} from "../api/billing";
import { useBillingStore } from "../stores/billing";
import type { CreditSnapshot } from "../api/types";

const billing = useBillingStore();
// `credit` from the store is the live snapshot; the local `credit`
// ref below is the most recent /api/usage response from this view's
// own fetch (so the Plan / Spent cards always agree with the table
// even if the global store hasn't polled yet).
const { credit: storeCredit } = storeToRefs(billing);

// Page size for both "first page" and "load older". Capped at 500 by
// the server. 100 is a sweet spot: a typical user has well under 100
// events per day so the first page covers "today + a bit" without
// asking the server for a much larger window most users will never
// scroll through.
const PAGE_SIZE = 100;

// ── Cloud (subscription) events ────────────────────────────────────
const events = ref<UsageEvent[]>([]);
const cloudHasMore = ref(false);
const loadingCloud = ref(false);
const loadingMoreCloud = ref(false);

// ── BYOK (local key) events ────────────────────────────────────────
// The BYOK section is hidden in the UI for now — see Activity.vue
// template (`v-if="byokActive"` gates). Keep the refs / loaders in
// place so the page wiring stays intact for when we re-enable the
// path; `byokActive` is permanently `false` for now so the section
// never renders. Flip the assignment in `loadAll` back to
// `byok.byok_active` to bring it back.
const byokActive = ref(false);
const byokEvents = ref<ByokEvent[]>([]);
const byokSummary = ref<ByokSummary>({ total: {}, per_model: [] });
const byokHasMore = ref(false);
const loadingByok = ref(false);
const loadingMoreByok = ref(false);

// ── Top-of-page state ──────────────────────────────────────────────
const errMsg = ref("");
const credit = ref<CreditSnapshot | null>(null);
const lastFetchedAt = ref<string | null>(null);

const loading = computed(() => loadingCloud.value || loadingByok.value);

/**
 * Initial load — pull the most recent PAGE_SIZE rows from each table.
 * Replaces (does not append to) the local lists, so manually clicking
 * the Refresh button resets pagination back to "today".
 */
async function refresh(): Promise<void> {
  errMsg.value = "";
  loadingCloud.value = true;
  loadingByok.value = true;
  try {
    const [usage, evts, byok] = await Promise.all([
      getUsage(),
      getUsageEvents({ limit: PAGE_SIZE }),
      getByokUsage({ limit: PAGE_SIZE }),
    ]);
    credit.value = usage.credit;
    events.value = evts.events;
    cloudHasMore.value = evts.has_more;
    // Force-hidden — see ref declaration above. When re-enabling the
    // BYOK UI, restore: `byokActive.value = byok.byok_active`.
    byokActive.value = false;
    byokEvents.value = byok.events;
    byokSummary.value = byok.summary;
    byokHasMore.value = byok.has_more;
    lastFetchedAt.value = new Date().toISOString();
  } catch (exc) {
    errMsg.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loadingCloud.value = false;
    loadingByok.value = false;
  }
}

/**
 * "Load older" — append the next page back in history using the
 * oldest visible row's timestamp as the cursor.
 */
async function loadOlderCloud(): Promise<void> {
  const oldest = events.value[events.value.length - 1]?.ts;
  if (!oldest || loadingMoreCloud.value) return;
  loadingMoreCloud.value = true;
  try {
    const r = await getUsageEvents({ limit: PAGE_SIZE, before: oldest });
    events.value = [...events.value, ...r.events];
    cloudHasMore.value = r.has_more;
  } catch (exc) {
    errMsg.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loadingMoreCloud.value = false;
  }
}

async function loadOlderByok(): Promise<void> {
  const oldest = byokEvents.value[byokEvents.value.length - 1]?.ts;
  if (!oldest || loadingMoreByok.value) return;
  loadingMoreByok.value = true;
  try {
    const r = await getByokUsage({ limit: PAGE_SIZE, before: oldest });
    byokEvents.value = [...byokEvents.value, ...r.events];
    byokHasMore.value = r.has_more;
  } catch (exc) {
    errMsg.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loadingMoreByok.value = false;
  }
}

onMounted(() => {
  void refresh();
  // No setInterval polling. The page has a visible Refresh button
  // and a one-shot refresh on mount; anything else would mean
  // firing /api/usage at a number nobody is necessarily watching.
});

onBeforeUnmount(() => {
  // Nothing to clean up — no interval was started. Hook kept so
  // future side-effect registration has the symmetric pair.
});

// ── derived ────────────────────────────────────────────────────────
const totalCost = computed(() =>
  events.value.reduce((acc, e) => acc + (e.cost_usd || 0), 0),
);

const totalTokens = computed(() =>
  events.value.reduce(
    (acc, e) =>
      acc +
      (e.tokens.input || 0) +
      (e.tokens.output || 0) +
      (e.tokens.cacheRead || 0) +
      (e.tokens.cacheWrite || 0),
    0,
  ),
);

const summaryByModel = computed<Array<{ model: string; calls: number; cost: number }>>(() => {
  const map = new Map<string, { calls: number; cost: number }>();
  for (const e of events.value) {
    const key = e.model || "(unknown)";
    const cur = map.get(key) || { calls: 0, cost: 0 };
    cur.calls += 1;
    cur.cost += e.cost_usd || 0;
    map.set(key, cur);
  }
  return Array.from(map.entries())
    .map(([model, v]) => ({ model, ...v }))
    .sort((a, b) => b.cost - a.cost);
});

// ── formatters ─────────────────────────────────────────────────────
function fmtDollars(n: number, places = 4): string {
  return `$${n.toFixed(places)}`;
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // Local time, HH:MM:SS — same density as VS Code's terminal logs.
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function shortSession(sid: string | null): string {
  if (!sid) return "—";
  // Sessions are prefix-tagged (`s_xxxxxxx`). Show the last 6 chars
  // so the column doesn't blow up but the user can still recognise
  // the chat.
  return sid.length > 8 ? "…" + sid.slice(-6) : sid;
}

function eventLabel(e: UsageEvent): string {
  if (e.source === "tool") return e.tool || "tool";
  return "chat";
}

// ── BYOK derived ──────────────────────────────────────────────────
const byokTotalTokens = computed(() => {
  const t = byokSummary.value.total;
  return (
    (t.input_tokens || 0) +
    (t.output_tokens || 0) +
    (t.cache_read || 0) +
    (t.cache_write || 0)
  );
});
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col bg-background text-foreground">
    <main class="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
      <!-- HERO -->
      <header class="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 class="text-h1 font-semibold tracking-tight">Activity</h1>
          <p class="mt-1 max-w-2xl text-lead text-muted-foreground">
            Every billable model call from your account, newest first.
            Includes the parent chat turn <em>and</em> any sub-LLM
            calls fired inside tools (e.g. <code class="font-mono text-caption">search_docs</code>).
            We load the most recent {{ PAGE_SIZE }} rows and fetch older
            history on demand.
          </p>
        </div>
        <button
          type="button"
          class="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 text-body text-foreground transition-colors hover:border-primary/40 disabled:opacity-50"
          :disabled="loading"
          title="Refresh now"
          @click="refresh"
        >
          <Icon
            :icon="loading ? 'codicon:loading' : 'codicon:refresh'"
            :class="loading && 'animate-spin'"
            class="h-3.5 w-3.5"
          />
          {{ loading ? "Refreshing…" : "Refresh" }}
        </button>
      </header>

      <p
        v-if="errMsg"
        class="mb-4 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-body text-destructive"
      >
        Couldn't load activity: {{ errMsg }}
      </p>

      <!-- Section heading for the cloud-billed events. Hidden when
           BYOK is the only path (no cloud calls have ever happened
           on this machine) so the page doesn't scream "you owe $0". -->
      <h2
        v-if="byokActive"
        class="mb-3 flex items-center gap-2 text-lead font-semibold text-foreground"
      >
        <Icon icon="codicon:cloud" class="h-4 w-4 text-muted-foreground" />
        Cloud usage
        <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
          via your Digi Setu subscription
        </span>
      </h2>

      <!-- SUMMARY CARDS -->
      <section class="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <article class="rounded-md border border-border bg-card p-3">
          <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            Plan
          </p>
          <p class="mt-1 text-lead font-semibold">
            {{ credit?.plan?.label || storeCredit?.plan?.label || "—" }}
          </p>
          <p class="font-mono text-caption text-muted-foreground">
            ${{ (credit?.plan?.monthly_credit_usd ?? 0).toFixed(2) }} /
            {{ credit?.month || "—" }}
          </p>
        </article>

        <article class="rounded-md border border-border bg-card p-3">
          <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            Spent this month
          </p>
          <p class="mt-1 text-lead font-semibold">
            ${{ (credit?.spent_usd ?? 0).toFixed(4) }}
          </p>
          <p class="font-mono text-caption text-muted-foreground">
            {{ credit?.prompts ?? 0 }} chat turn{{ (credit?.prompts ?? 0) === 1 ? "" : "s" }}
          </p>
        </article>

        <article class="rounded-md border border-border bg-card p-3">
          <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            Events loaded
          </p>
          <p class="mt-1 text-lead font-semibold">
            {{ events.length }}
          </p>
          <p class="font-mono text-caption text-muted-foreground">
            {{ cloudHasMore ? "more available" : "complete" }}
          </p>
        </article>

        <article class="rounded-md border border-border bg-card p-3">
          <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            Tokens (loaded events)
          </p>
          <p class="mt-1 text-lead font-semibold">
            {{ fmtTokens(totalTokens) }}
          </p>
          <p class="font-mono text-caption text-muted-foreground">
            {{ fmtDollars(totalCost, 4) }} sub-total
          </p>
        </article>
      </section>

      <!-- BY-MODEL ROLLUP -->
      <section v-if="summaryByModel.length > 0" class="mb-6">
        <h2 class="mb-2 text-body font-semibold uppercase tracking-wide text-muted-foreground">
          By model (loaded events)
        </h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="row in summaryByModel"
            :key="row.model"
            class="inline-flex items-center gap-2 rounded-md border border-border bg-card px-2 py-1 font-mono text-caption"
            :title="`${row.calls} call${row.calls === 1 ? '' : 's'} on ${row.model} = ${fmtDollars(row.cost, 4)}`"
          >
            <span class="text-foreground">{{ row.model }}</span>
            <span class="text-muted-foreground">·</span>
            <span class="text-muted-foreground">{{ row.calls }}×</span>
            <span class="text-foreground">{{ fmtDollars(row.cost, 4) }}</span>
          </span>
        </div>
      </section>

      <!-- TABLE -->
      <section
        class="overflow-hidden rounded-md border border-border bg-card"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-body">
            <thead class="border-b border-border bg-muted/30 font-mono text-caption uppercase tracking-wide text-muted-foreground">
              <tr>
                <th class="px-3 py-2 text-left font-medium">When</th>
                <th class="px-3 py-2 text-left font-medium">Source</th>
                <th class="px-3 py-2 text-left font-medium">Model</th>
                <th class="px-3 py-2 text-right font-medium">In</th>
                <th class="px-3 py-2 text-right font-medium">Out</th>
                <th class="px-3 py-2 text-right font-medium">Cache R</th>
                <th class="px-3 py-2 text-right font-medium">Cache W</th>
                <th class="px-3 py-2 text-right font-medium">Cost</th>
                <th class="px-3 py-2 text-left font-medium">Session</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(e, i) in events"
                :key="`${e.ts}-${i}`"
                class="border-b border-border/40 last:border-b-0 hover:bg-muted/20"
              >
                <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption text-muted-foreground">
                  {{ fmtTime(e.ts) }}
                </td>
                <td class="px-3 py-1.5">
                  <span
                    class="inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 font-mono text-caption"
                    :class="
                      e.source === 'chat'
                        ? 'border-primary/40 bg-primary/10 text-primary'
                        : 'border-border bg-muted/40 text-muted-foreground'
                    "
                  >
                    <Icon
                      :icon="e.source === 'chat' ? 'codicon:comment' : 'codicon:tools'"
                      class="h-3 w-3"
                    />
                    {{ eventLabel(e) }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption">
                  {{ e.model || "—" }}
                </td>
                <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums">
                  {{ e.tokens.input ? fmtTokens(e.tokens.input) : "—" }}
                </td>
                <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums">
                  {{ e.tokens.output ? fmtTokens(e.tokens.output) : "—" }}
                </td>
                <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                  {{ e.tokens.cacheRead ? fmtTokens(e.tokens.cacheRead) : "—" }}
                </td>
                <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                  {{ e.tokens.cacheWrite ? fmtTokens(e.tokens.cacheWrite) : "—" }}
                </td>
                <td
                  class="whitespace-nowrap px-3 py-1.5 text-right font-mono font-semibold tabular-nums"
                  :title="
                    e.breakdown
                      ? `LLM ${fmtDollars(e.breakdown.llm_usd ?? 0, 6)} + VM ${fmtDollars(e.breakdown.vm_usd ?? 0, 6)} + Margin ${fmtDollars(e.breakdown.margin_usd ?? 0, 6)}`
                      : 'No breakdown available'
                  "
                >
                  {{ e.cost_usd > 0 ? fmtDollars(e.cost_usd, 4) : "—" }}
                </td>
                <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption text-muted-foreground">
                  <RouterLink
                    v-if="e.session_id"
                    :to="`/chat/${e.session_id}`"
                    class="hover:text-foreground hover:underline"
                    :title="e.session_id"
                  >{{ shortSession(e.session_id) }}</RouterLink>
                  <span v-else>—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Empty state -->
        <div
          v-if="!loading && events.length === 0"
          class="flex flex-col items-center justify-center gap-2 px-6 py-10 text-lead text-muted-foreground"
        >
          <Icon icon="codicon:graph-line" class="h-5 w-5" />
          <p>No activity yet.</p>
          <p class="text-caption">
            As soon as you send a prompt, the call shows up here with
            its tokens and cost.
          </p>
        </div>

        <!-- Pagination footer for the cloud table. Stays rendered as
             long as the server reports more pages back in history; the
             button itself disables while a fetch is in flight so a
             user can't double-trigger pagination. -->
        <div
          v-if="events.length > 0"
          class="flex items-center justify-between gap-3 border-t border-border bg-muted/10 px-3 py-2"
        >
          <span class="font-mono text-caption text-muted-foreground">
            Showing {{ events.length }}
            event{{ events.length === 1 ? "" : "s" }}
            <span v-if="cloudHasMore">· more available</span>
          </span>
          <button
            v-if="cloudHasMore"
            type="button"
            class="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-body text-foreground transition-colors hover:border-primary/40 disabled:opacity-50"
            :disabled="loadingMoreCloud"
            @click="loadOlderCloud"
          >
            <Icon
              :icon="loadingMoreCloud ? 'codicon:loading' : 'codicon:chevron-down'"
              :class="loadingMoreCloud && 'animate-spin'"
              class="h-3.5 w-3.5"
            />
            {{ loadingMoreCloud ? "Loading…" : `Load older ${PAGE_SIZE}` }}
          </button>
        </div>
      </section>

      <!-- ── BYOK SECTION ──────────────────────────────────────────
           Only renders when the desktop sidecar has at least one
           BYOK key in ~/.digi-setu/.env. We deliberately keep this
           visually distinct from the cloud table — different colour
           accent, no $ column, footer link to provider dashboards
           — so the user can't confuse "what we know" with "what
           your provider billed".  -->
      <section v-if="byokActive" class="mt-10">
        <h2 class="mb-3 flex items-center gap-2 text-lead font-semibold text-foreground">
          <Icon icon="codicon:key" class="h-4 w-4 text-success" />
          Local usage
          <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            via your AI keys (BYOK)
          </span>
        </h2>

        <p class="mb-4 max-w-2xl text-body text-muted-foreground">
          When you pick a model badged
          <span class="rounded border border-success/40 bg-success/10 px-1 py-px font-mono text-caption uppercase text-success">BYOK</span>,
          the call goes from this machine straight to the AI provider
          using the key you put in
          <code class="font-mono text-caption">~/.digi-setu/.env</code>.
          We track tokens here so you can see local activity, but the
          actual <strong>$ amount</strong> only your provider knows —
          their dashboard is the source of truth.
        </p>

        <section class="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
          <article class="rounded-md border border-success/30 bg-success/5 p-3">
            <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Local turns
            </p>
            <p class="mt-1 text-lead font-semibold">
              {{ byokSummary.total.turns ?? 0 }}
            </p>
            <p class="font-mono text-caption text-muted-foreground">all-time</p>
          </article>

          <article class="rounded-md border border-success/30 bg-success/5 p-3">
            <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Input tokens
            </p>
            <p class="mt-1 text-lead font-semibold">
              {{ fmtTokens(byokSummary.total.input_tokens || 0) }}
            </p>
            <p class="font-mono text-caption text-muted-foreground">prompt + cached</p>
          </article>

          <article class="rounded-md border border-success/30 bg-success/5 p-3">
            <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Output tokens
            </p>
            <p class="mt-1 text-lead font-semibold">
              {{ fmtTokens(byokSummary.total.output_tokens || 0) }}
            </p>
            <p class="font-mono text-caption text-muted-foreground">model replies</p>
          </article>

          <article class="rounded-md border border-success/30 bg-success/5 p-3">
            <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
              Total tokens
            </p>
            <p class="mt-1 text-lead font-semibold">
              {{ fmtTokens(byokTotalTokens) }}
            </p>
            <p class="font-mono text-caption text-muted-foreground">in + out + cache</p>
          </article>
        </section>

        <!-- Per-model rollup -->
        <div v-if="byokSummary.per_model.length > 0" class="mb-5 flex flex-wrap gap-2">
          <span
            v-for="row in byokSummary.per_model"
            :key="row.model_id"
            class="inline-flex items-center gap-2 rounded-md border border-success/30 bg-success/5 px-2 py-1 font-mono text-caption"
            :title="`${row.turns} turn${row.turns === 1 ? '' : 's'} · ${row.provider}`"
          >
            <span class="text-foreground">{{ row.model_id }}</span>
            <span class="text-muted-foreground">·</span>
            <span class="text-muted-foreground">{{ row.provider }}</span>
            <span class="text-muted-foreground">·</span>
            <span class="text-foreground">{{ row.turns }}×</span>
          </span>
        </div>

        <!-- Per-turn table -->
        <div class="overflow-hidden rounded-md border border-success/30 bg-card">
          <div class="overflow-x-auto">
            <table class="w-full text-body">
              <thead class="border-b border-border bg-success/5 font-mono text-caption uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th class="px-3 py-2 text-left font-medium">When</th>
                  <th class="px-3 py-2 text-left font-medium">Model</th>
                  <th class="px-3 py-2 text-left font-medium">Provider</th>
                  <th class="px-3 py-2 text-right font-medium">In</th>
                  <th class="px-3 py-2 text-right font-medium">Out</th>
                  <th class="px-3 py-2 text-right font-medium">Cache R</th>
                  <th class="px-3 py-2 text-right font-medium">Cache W</th>
                  <th class="px-3 py-2 text-left font-medium">Session</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(e, i) in byokEvents"
                  :key="`byok-${e.ts}-${i}`"
                  class="border-b border-border/40 last:border-b-0 hover:bg-success/5"
                >
                  <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption text-muted-foreground">
                    {{ fmtTime(e.ts) }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption">
                    {{ e.model_id }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption text-muted-foreground">
                    {{ e.provider }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums">
                    {{ e.input_tokens ? fmtTokens(e.input_tokens) : "—" }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums">
                    {{ e.output_tokens ? fmtTokens(e.output_tokens) : "—" }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                    {{ e.cache_read ? fmtTokens(e.cache_read) : "—" }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                    {{ e.cache_write ? fmtTokens(e.cache_write) : "—" }}
                  </td>
                  <td class="whitespace-nowrap px-3 py-1.5 font-mono text-caption text-muted-foreground">
                    <RouterLink
                      v-if="e.session_id"
                      :to="`/chat/${e.session_id}`"
                      class="hover:text-foreground hover:underline"
                      :title="e.session_id"
                    >{{ shortSession(e.session_id) }}</RouterLink>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Empty state -->
          <div
            v-if="!loading && byokEvents.length === 0"
            class="flex flex-col items-center justify-center gap-1 px-6 py-8 text-body text-muted-foreground"
          >
            <Icon icon="codicon:key" class="h-5 w-5" />
            <p>No local usage yet — pick a BYOK-badged model in the chat to see rows here.</p>
          </div>

          <!-- Pagination footer for the BYOK table. -->
          <div
            v-if="byokEvents.length > 0"
            class="flex items-center justify-between gap-3 border-t border-success/30 bg-success/5 px-3 py-2"
          >
            <span class="font-mono text-caption text-muted-foreground">
              Showing {{ byokEvents.length }}
              turn{{ byokEvents.length === 1 ? "" : "s" }}
              <span v-if="byokHasMore">· more available</span>
            </span>
            <button
              v-if="byokHasMore"
              type="button"
              class="flex items-center gap-1.5 rounded-md border border-success/40 bg-card px-2.5 py-1 text-body text-foreground transition-colors hover:border-success disabled:opacity-50"
              :disabled="loadingMoreByok"
              @click="loadOlderByok"
            >
              <Icon
                :icon="loadingMoreByok ? 'codicon:loading' : 'codicon:chevron-down'"
                :class="loadingMoreByok && 'animate-spin'"
                class="h-3.5 w-3.5"
              />
              {{ loadingMoreByok ? "Loading…" : `Load older ${PAGE_SIZE}` }}
            </button>
          </div>
        </div>

        <p class="mt-3 text-caption text-muted-foreground">
          Provider dashboards for $ figures:
          <a href="https://console.anthropic.com/settings/usage" target="_blank" rel="noopener noreferrer" class="font-mono text-foreground/80 hover:text-primary hover:underline">Anthropic</a>
          ·
          <a href="https://aistudio.google.com/usage" target="_blank" rel="noopener noreferrer" class="font-mono text-foreground/80 hover:text-primary hover:underline">Google AI Studio</a>
          ·
          <a href="https://platform.openai.com/usage" target="_blank" rel="noopener noreferrer" class="font-mono text-foreground/80 hover:text-primary hover:underline">OpenAI</a>
        </p>
      </section>

      <p
        v-if="lastFetchedAt"
        class="mt-3 font-mono text-caption text-muted-foreground"
      >
        Last refreshed {{ fmtTime(lastFetchedAt) }} · click Refresh for the latest numbers
      </p>
    </main>

    <!-- Desktop has its own per-view AppFooter (the web fork moved this
         into App.vue once a global header refactor landed; the desktop
         shell predates that and still needs it inline). -->
    <AppFooter />
  </div>
</template>
