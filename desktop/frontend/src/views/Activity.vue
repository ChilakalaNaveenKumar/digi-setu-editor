<!--
  Activity — per-user event log of every billable LLM call.

  Answers the question "where did my $2 free credit go?". Each row is
  one call to a provider (parent chat turn or a sub-LLM tool call like
  search_docs / web_search). Newest first.

  We deliberately don't add charts here — the data is line-item
  receipts, not aggregated analytics. The credit-remaining banner up
  top is the at-a-glance summary; the table is the audit trail.

  Why a server-side ring buffer instead of pulling from pi's JSONL
  log: a single chat turn produces many events (one per tool call),
  and the JSONL files split by RPC connection. Aggregating them
  client-side would be slow on the first paint of a long-running
  workspace. The ledger already sees every billable event because
  it's the one charging credit; reusing that source means the table
  always matches the dollar number on the chip.

  Pagination: ring buffer is 500 events, surfaced via `?limit=500`.
  When users start asking for older history we'll persist to SQLite
  and add a date picker, but everyone who's tested this so far just
  wants "show me what's happened today".
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

const events = ref<UsageEvent[]>([]);
const loading = ref(false);
const errMsg = ref("");
const credit = ref<CreditSnapshot | null>(null);
const lastFetchedAt = ref<string | null>(null);
// BYOK side: separate fetch so the cloud table loads on web installs
// without paying for a sidecar round-trip on every refresh.
const byokActive = ref(false);
const byokEvents = ref<ByokEvent[]>([]);
const byokSummary = ref<ByokSummary>({ total: {}, per_model: [] });
let refreshTimer: ReturnType<typeof setInterval> | null = null;

async function refresh(): Promise<void> {
  loading.value = true;
  errMsg.value = "";
  try {
    const [usage, evts, byok] = await Promise.all([
      getUsage(),
      getUsageEvents({ limit: 500 }),
      getByokUsage({ limit: 500 }),
    ]);
    credit.value = usage.credit;
    events.value = evts.events;
    byokActive.value = byok.byok_active;
    byokEvents.value = byok.events;
    byokSummary.value = byok.summary;
    lastFetchedAt.value = new Date().toISOString();
  } catch (exc) {
    errMsg.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void refresh();
  // Light auto-refresh while the tab is open so a chat happening in
  // a different tab shows up here without a manual reload. 30 s is
  // a reasonable middle ground — frequent enough to feel live, rare
  // enough that it doesn't show up in the network panel.
  refreshTimer = setInterval(() => {
    if (document.visibilityState === "visible") void refresh();
  }, 30_000);
});

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
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
            Recent events shown
          </p>
          <p class="mt-1 text-lead font-semibold">
            {{ events.length }}
          </p>
          <p class="font-mono text-caption text-muted-foreground">
            ring buffer (last 500)
          </p>
        </article>

        <article class="rounded-md border border-border bg-card p-3">
          <p class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
            Tokens (visible window)
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
          By model (visible window)
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
        Last refreshed {{ fmtTime(lastFetchedAt) }} · auto-refreshes every 30s
      </p>
    </main>

    <AppFooter />
  </div>
</template>
