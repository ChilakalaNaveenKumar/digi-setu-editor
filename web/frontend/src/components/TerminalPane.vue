<!--
  TerminalPane — VS Code-style bottom panel for ALL terminals.

  A "terminal" here is one of two things:
    • bash      — a single bash tool call (one row per call)
    • bg        — a pi-interactive-shell background session (one row per
                  sessionId, accumulating spawn + every check + kill).

  Layout (when expanded, ≥1 entry):
    ┌─ resize handle (drag to grow/shrink panel) ─────────────────────┐
    ├─ ▾ terminal · 4 · 1 running · 2 bg   [↵ wrap] [stop] hide       ┤
    ├─────────────────────────────────────────────┬──────────────────┤
    │  MAIN PANE                                   │ SIDEBAR          │
    │                                              │                   │
    │  ● lucky-comet · running · 2m 14s            │ ● bash 1          │
    │    background · dispatch · headless          │ ● bash 2          │
    │                                              │ ─────────         │
    │  $ python3 -m http.server 9999               │ background        │
    │                                              │ ● lucky-comet     │
    │  [last checked 12s ago]                      │ ○ fresh-orbit     │
    │  Serving HTTP on 0.0.0.0:9999 (...)          │                   │
    │  127.0.0.1 - - "GET / HTTP/1.1" 200          │                   │
    │                                              │                   │
    │            [↻ refresh]  [■ stop]             │                   │
    └─────────────────────────────────────────────┴──────────────────┘

  bg-session output is sourced from the latest interactive_shell `check`
  result (or the spawn result if no check has been issued yet). The
  extension only persists output in-process, so polling requires an LLM
  round-trip — hence the explicit "↻ refresh" button instead of free
  auto-poll. Click it once → agent calls interactive_shell with sessionId
  → result text lands here.
-->
<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";
import { isBackgroundCommand, useSessionStore } from "../stores/session";
import type { ToolCall } from "../types/rpc";
import XtermView from "./XtermView.vue";

const store = useSessionStore();

// Hydrate shell profiles + existing PTYs on mount so the "+" picker has
// data immediately.
onMounted(() => {
  void store.loadShellProfiles();
  void store.refreshUserTerminals();
});

// ── New terminal picker (the + button + dropdown) ─────────────────────
const showShellPicker = ref(false);
function toggleShellPicker(): void {
  showShellPicker.value = !showShellPicker.value;
}
async function newTerminal(shellPath?: string): Promise<void> {
  showShellPicker.value = false;
  const t = await store.createUserTerminal(shellPath);
  if (t) selectedId.value = `pty:${t.id}`;
}
async function killSelectedPty(): Promise<void> {
  const e = selectedEntry.value;
  if (!e || e.kind !== "pty") return;
  const ok = await store.confirm({
    title: "Close terminal?",
    description: `Kill the ${e.label} session (PID ${e.pty.pid}) and remove it from the sidebar.`,
    confirmLabel: "Close terminal",
    variant: "destructive",
  });
  if (!ok) return;
  await store.killUserTerminal(e.pty.id);
}

const collapsed = computed({
  get: () => !store.terminalExpanded,
  set: (v: boolean) => store.setTerminalExpanded(!v),
});

const entries = computed(() => store.terminalEntries);

const runningCount = computed(
  () =>
    entries.value.filter((e) => {
      if (e.kind === "bash") {
        return e.call.status === "running" || e.call.status === "pending";
      }
      if (e.kind === "bg") {
        return e.process.status === "running" || e.process.status === "terminating";
      }
      // pty: running ↔ not closed
      return !e.pty.closed;
    }).length,
);

// Group sidebar entries: bash first, then bg (for the "background" header).
const bashEntries = computed(() =>
  entries.value.filter((e): e is Extract<typeof entries.value[number], { kind: "bash" }> => e.kind === "bash"),
);
const bgEntries = computed(() =>
  entries.value.filter((e): e is Extract<typeof entries.value[number], { kind: "bg" }> => e.kind === "bg"),
);
const ptyEntries = computed(() =>
  entries.value.filter((e): e is Extract<typeof entries.value[number], { kind: "pty" }> => e.kind === "pty"),
);

// ── selection ────────────────────────────────────────────────────────
const selectedId = ref<string | null>(null);

watch(
  () => entries.value.length,
  (n, prev) => {
    if (n > 0 && (prev ?? 0) < n) {
      selectedId.value = entries.value[n - 1]!.id;
    }
    if (n === 0) selectedId.value = null;
  },
);

// Bridge from chat-card "Open in Terminal Pane" → select the matching
// bash entry (focused id is a tool-call id; entry id is `bash:<tcId>`).
watch(
  () => store.terminalFocusedToolCallId,
  (tcId) => {
    if (!tcId) return;
    const hit = entries.value.find(
      (e) => e.kind === "bash" && e.call.id === tcId,
    );
    if (hit) selectedId.value = hit.id;
    setTimeout(() => store.clearTerminalFocus(), 2000);
  },
);

// Bridge from process card "open" OR auto-open when a new bg process
// starts. The store sets `terminalFocusedBgId` which we mirror onto
// our selection. We clear it after consuming so a future re-click can
// re-trigger.
watch(
  () => store.terminalFocusedBgId,
  (bgId) => {
    if (!bgId) return;
    const hit = entries.value.find(
      (e) => e.kind === "bg" && e.process.id === bgId,
    );
    if (hit) selectedId.value = hit.id;
    setTimeout(() => {
      store.terminalFocusedBgId = null;
    }, 2000);
  },
);

const selectedEntry = computed(() => {
  const id = selectedId.value;
  if (!id) return entries.value[entries.value.length - 1] ?? null;
  return entries.value.find((e) => e.id === id) ?? null;
});

function selectEntry(id: string): void {
  selectedId.value = id;
}

function commandFor(call: ToolCall): string {
  const args = call.args as { command?: unknown } | undefined;
  return typeof args?.command === "string" ? args.command : "";
}

/**
 * Hide a terminal entry from the sidebar. The chat card and the underlying
 * tool call are untouched — this is purely a "tab close" in the bottom
 * panel. If the active entry was the one removed, fall back to the latest
 * remaining entry (or null).
 */
function removeEntry(entryId: string): void {
  const tcId = entryId.startsWith("bash:") ? entryId.slice(5) : null;
  if (!tcId) return;
  store.removeBashCall(tcId);
  if (selectedId.value === entryId) {
    const next = entries.value.filter((e) => e.id !== entryId);
    selectedId.value = next.length > 0 ? next[next.length - 1]!.id : null;
  }
}

const autoOpenedOnce = ref(false);
watch(
  () => entries.value.length,
  (n) => {
    if (n > 0 && !autoOpenedOnce.value) {
      autoOpenedOnce.value = true;
      collapsed.value = false;
    }
  },
);

// ── sticky-bottom autoscroll for the output region ────────────────────
const outputScroller = ref<HTMLDivElement | null>(null);
const stickToBottom = ref(true);

function onOutputScroll(): void {
  const el = outputScroller.value;
  if (!el) return;
  const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
  stickToBottom.value = distance < 60;
}

/**
 * Manually jump back to the latest output and re-arm the sticky-bottom
 * autoscroll. Triggered by the floating "↓ jump to latest" button that
 * appears whenever the user scrolled away from the bottom.
 */
async function jumpToLatest(): Promise<void> {
  stickToBottom.value = true;
  await nextTick();
  const el = outputScroller.value;
  if (el) el.scrollTop = el.scrollHeight;
}

const selectedOutput = computed(() => {
  const e = selectedEntry.value;
  if (!e) return "";
  if (e.kind === "bash") {
    if (e.call.status === "running" || e.call.status === "pending") {
      return e.call.streamingOutput ?? "";
    }
    return e.call.result?.text ?? e.call.streamingOutput ?? "";
  }
  if (e.kind === "bg") {
    // bg: live tail from the backend's file watcher (WS bg_output events).
    return e.process.output;
  }
  // pty: handled by XtermView, not by this scrollable text pane.
  return "";
});

watch(selectedOutput, async () => {
  if (!stickToBottom.value || collapsed.value) return;
  await nextTick();
  const el = outputScroller.value;
  if (el) el.scrollTop = el.scrollHeight;
});

watch(selectedId, () => {
  stickToBottom.value = true;
  nextTick(() => {
    const el = outputScroller.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
});

// ── helpers ───────────────────────────────────────────────────────────
const tickNow = ref(Date.now());
let tickHandle: number | null = null;
onMounted(() => {
  tickHandle = window.setInterval(() => {
    tickNow.value = Date.now();
  }, 500);
});
onUnmounted(() => {
  if (tickHandle !== null) window.clearInterval(tickHandle);
});

function bashStatusDot(call: ToolCall): string {
  switch (call.status) {
    case "pending":
      return "bg-muted-foreground/50";
    case "running":
      return "bg-warning animate-pulse";
    case "success":
      return "bg-success";
    case "error":
      return "bg-destructive";
  }
}

function bgStatusDot(finished: boolean): string {
  return finished
    ? "bg-muted-foreground/50"
    : "bg-primary animate-pulse";
}

function bashStatusColor(call: ToolCall): string {
  switch (call.status) {
    case "running":
      return "text-warning";
    case "success":
      return "text-success";
    case "error":
      return "text-destructive";
    default:
      return "text-muted-foreground";
  }
}

function bashStatusLabel(call: ToolCall): string {
  switch (call.status) {
    case "pending":
      return "queued";
    case "running":
      return "running";
    case "success":
      return "exit 0";
    case "error":
      return "failed";
  }
}

function durationFor(start: number | undefined, end: number | undefined): string {
  if (start === undefined) return "";
  const e = end ?? tickNow.value;
  const ms = Math.max(0, e - start);
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const mins = Math.floor(s / 60);
  return `${mins}m ${Math.floor(s % 60).toString().padStart(2, "0")}s`;
}

// ── selected-entry derived state (split per kind for type safety) ────
const selectedBashCall = computed<ToolCall | null>(() =>
  selectedEntry.value?.kind === "bash" ? selectedEntry.value.call : null,
);
const selectedBg = computed(() =>
  selectedEntry.value?.kind === "bg" ? selectedEntry.value : null,
);
const selectedPty = computed(() =>
  selectedEntry.value?.kind === "pty" ? selectedEntry.value : null,
);

const selectedCommand = computed(() => {
  const e = selectedEntry.value;
  if (!e) return "";
  if (e.kind === "bash") {
    const args = e.call.args as { command?: unknown } | undefined;
    return typeof args?.command === "string" ? args.command : "";
  }
  if (e.kind === "bg") return e.process.command;
  // pty: show the shell binary path.
  return e.pty.shell;
});

const selectedIsRunning = computed(() => {
  const e = selectedEntry.value;
  if (!e) return false;
  if (e.kind === "bash") {
    return e.call.status === "running" || e.call.status === "pending";
  }
  if (e.kind === "bg") {
    return e.process.status === "running" || e.process.status === "terminating";
  }
  return !e.pty.closed;
});

const selectedIsBackground = computed(() => {
  const e = selectedEntry.value;
  if (!e) return false;
  if (e.kind === "bash") return isBackgroundCommand(selectedCommand.value);
  return true;
});

interface BashTruncation {
  truncated: boolean;
  truncatedBy: "lines" | "bytes" | null;
  totalLines?: number;
  outputLines?: number;
}
const selectedTruncation = computed<{
  truncation: BashTruncation | null;
  fullOutputPath: string | null;
}>(() => {
  const call = selectedBashCall.value;
  if (!call) return { truncation: null, fullOutputPath: null };
  const details = call.result?.details as
    | { truncation?: BashTruncation; fullOutputPath?: string }
    | undefined;
  return {
    truncation: details?.truncation && details.truncation.truncated ? details.truncation : null,
    fullOutputPath: typeof details?.fullOutputPath === "string" ? details.fullOutputPath : null,
  };
});

// Resizing is now owned by AppShell's Splitpanes — no internal drag handle.

// ── actions wired to the store ────────────────────────────────────────
function stopCurrentBash(): void {
  store.abort();
}

function toggleWrap(): void {
  store.toggleTerminalWrap();
}

function killBg(): void {
  const e = selectedBg.value;
  if (e) void store.killBackgroundProcess(e.process.id);
}
</script>

<template>
  <section
    :class="[
      'relative flex w-full min-h-0 flex-col border-t border-border bg-card text-sm',
      collapsed ? 'h-auto shrink-0' : 'h-full',
    ]"
  >
    <!-- ── HEADER ──────────────────────────────────────────────────── -->
    <header
      class="flex items-center justify-between gap-2 border-b border-transparent px-3 py-1.5 text-xs text-muted-foreground"
      :class="!collapsed && 'border-border/60'"
    >
      <button
        type="button"
        class="flex flex-1 items-center gap-2 hover:text-foreground"
        @click="collapsed = !collapsed"
      >
        <span class="select-none">{{ collapsed ? "▸" : "▾" }}</span>
        <span class="font-mono font-semibold text-foreground/80">terminal</span>
        <span
          v-if="entries.length > 0"
          class="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] tabular-nums"
        >{{ entries.length }}</span>
        <span
          v-if="runningCount > 0"
          class="flex items-center gap-1 rounded-sm bg-warning/15 px-1.5 py-0.5 text-[10px] text-warning"
        >
          <span class="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-warning"></span>
          {{ runningCount }} running
        </span>
        <span
          v-if="store.activeBackgroundCount > 0"
          class="flex items-center gap-1 rounded-sm bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary"
          title="Active background sessions (pi-interactive-shell). Click to expand the panel."
        >
          <span class="inline-block h-1.5 w-1.5 rounded-full bg-primary"></span>
          {{ store.activeBackgroundCount }} bg
        </span>
      </button>

      <!-- TOOLBAR — wrap toggle + stop button (right side, only when open) -->
      <div v-if="!collapsed" class="flex items-center gap-1.5">
        <button
          type="button"
          class="rounded-sm px-1.5 py-0.5 text-[10px] hover:bg-accent hover:text-foreground"
          :class="store.terminalWrap && 'bg-accent text-foreground'"
          :title="store.terminalWrap ? 'Disable line wrap' : 'Enable line wrap'"
          @click="toggleWrap"
        >↵ wrap</button>
        <button
          v-if="selectedBashCall && selectedIsRunning"
          type="button"
          class="flex items-center gap-1 rounded-sm bg-destructive/15 px-1.5 py-0.5 text-[10px] text-destructive hover:bg-destructive/25"
          title="Stop the current agent turn (kills the running bash process group)"
          @click="stopCurrentBash"
        >
          <span class="inline-block h-1.5 w-1.5 rounded-sm bg-destructive"></span>
          stop
        </button>
        <button
          type="button"
          class="text-[11px] hover:text-foreground"
          @click="collapsed = true"
        >hide</button>
      </div>
      <div v-else class="text-[11px]">expand</div>
    </header>

    <!-- ── BODY: split view ──────────────────────────────────────── -->
    <div v-if="!collapsed" class="flex min-h-0 flex-1">
      <!-- ─── MAIN VIEW ─────────────────────────────────────────── -->
      <div class="flex min-w-0 flex-1 flex-col bg-background">
        <!-- BASH ENTRY -->
        <template v-if="selectedBashCall">
          <!-- Status strip with badges -->
          <div
            class="flex items-center gap-2 border-b border-border/60 bg-card/40 px-3 py-1.5 font-mono text-[11px]"
          >
            <span :class="['inline-block h-2 w-2 rounded-full', bashStatusDot(selectedBashCall)]"></span>
            <span class="font-semibold text-foreground/80">bash</span>
            <span class="text-muted-foreground">·</span>
            <span :class="['tabular-nums', bashStatusColor(selectedBashCall)]">
              {{ bashStatusLabel(selectedBashCall) }}
              <template v-if="durationFor(selectedBashCall.startedAt, selectedBashCall.endedAt)">
                · {{ durationFor(selectedBashCall.startedAt, selectedBashCall.endedAt) }}
              </template>
            </span>
            <span
              v-if="selectedIsBackground"
              class="ml-1 inline-flex items-center gap-1 rounded-sm bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary"
              title="This command spawns a background process. The daemon keeps running after the foreground exits."
            >
              <span class="inline-block h-1 w-1 rounded-full bg-primary"></span>
              background
            </span>
          </div>

          <!-- Command (full, wraps, never truncated) -->
          <pre
            class="border-b border-border/60 bg-editor px-3 py-2 font-mono text-[11.5px] leading-[1.55] text-foreground/95 whitespace-pre-wrap break-words"
          ><span class="select-none text-muted-foreground">$ </span>{{ selectedCommand || "(streaming command…)" }}</pre>

          <!-- Truncation banner -->
          <div
            v-if="selectedTruncation.truncation"
            class="flex items-center justify-between gap-2 border-b border-warning/30 bg-warning/10 px-3 py-1 font-mono text-[10px] text-warning"
          >
            <span>
              ⚠ truncated by pi: showing
              <span class="tabular-nums">{{ selectedTruncation.truncation.outputLines }}</span>
              of
              <span class="tabular-nums">{{ selectedTruncation.truncation.totalLines }}</span>
              lines<template v-if="selectedTruncation.truncation.truncatedBy === 'bytes'"> (byte limit hit)</template>
            </span>
            <span
              v-if="selectedTruncation.fullOutputPath"
              class="truncate"
              :title="selectedTruncation.fullOutputPath"
            >full output: {{ selectedTruncation.fullOutputPath }}</span>
          </div>

          <!-- Output (live or final) -->
          <div class="relative min-h-0 flex-1">
            <div
              ref="outputScroller"
              class="absolute inset-0 overflow-auto"
              @scroll="onOutputScroll"
            >
              <pre
                v-if="selectedOutput"
                :class="[
                  'px-3 py-2 font-mono text-[11.5px] leading-[1.5] text-foreground/90',
                  store.terminalWrap ? 'whitespace-pre-wrap break-words' : 'whitespace-pre',
                ]"
              >{{ selectedOutput }}</pre>
              <div
                v-else-if="selectedIsRunning"
                class="px-3 py-2 font-mono text-[11px] italic text-muted-foreground"
              >waiting for output…</div>
            </div>
            <button
              v-if="!stickToBottom && selectedOutput"
              type="button"
              class="absolute bottom-3 right-4 z-10 inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-card/95 px-3 py-1 text-[11px] text-primary shadow-md backdrop-blur-sm transition hover:bg-primary/15"
              title="Auto-scroll paused. Click to jump back to the latest output."
              @click="jumpToLatest"
            >
              <span class="text-base leading-none">↓</span>
              <span>jump to latest</span>
            </button>
          </div>
        </template>

        <!-- BG ENTRY -->
        <template v-else-if="selectedBg">
          <!-- Status strip -->
          <div
            class="flex items-center gap-2 border-b border-border/60 bg-card/40 px-3 py-1.5 font-mono text-[11px]"
          >
            <span :class="['inline-block h-2 w-2 rounded-full', bgStatusDot(selectedBg.process.status !== 'running')]"></span>
            <span class="font-semibold text-foreground/80">{{ selectedBg.process.name }}</span>
            <span class="text-muted-foreground">·</span>
            <span
              :class="
                selectedBg.process.status === 'running'
                  ? 'text-primary'
                  : selectedBg.process.status === 'killed'
                  ? 'text-destructive'
                  : 'text-muted-foreground'
              "
            >
              {{ selectedBg.process.status }}
              <template v-if="selectedBg.process.exitCode !== null"> · exit {{ selectedBg.process.exitCode }}</template>
              <template v-if="durationFor(selectedBg.process.startedAt, selectedBg.process.endedAt ?? undefined)">
                · {{ durationFor(selectedBg.process.startedAt, selectedBg.process.endedAt ?? undefined) }}
              </template>
            </span>
            <span
              class="ml-1 inline-flex items-center gap-1 rounded-sm bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary"
              title="Live tail — backend is reading the on-disk log file every 100ms"
            >
              <span class="inline-block h-1 w-1 rounded-full bg-primary"></span>
              live
            </span>
            <span
              v-if="selectedBg.process.pid > 0"
              class="text-[10px] text-muted-foreground tabular-nums"
            >pid {{ selectedBg.process.pid }}</span>
          </div>

          <!-- Command -->
          <pre
            class="border-b border-border/60 bg-editor px-3 py-2 font-mono text-[11.5px] leading-[1.55] text-foreground/95 whitespace-pre-wrap break-words"
          ><span class="select-none text-muted-foreground">$ </span>{{ selectedCommand }}</pre>

          <!-- Live output (file-tailed by the backend, no refresh button needed) -->
          <div class="relative min-h-0 flex-1">
            <div
              ref="outputScroller"
              class="absolute inset-0 overflow-auto"
              @scroll="onOutputScroll"
            >
              <pre
                v-if="selectedOutput"
                :class="[
                  'px-3 py-2 font-mono text-[11.5px] leading-[1.5] text-foreground/90',
                  store.terminalWrap ? 'whitespace-pre-wrap break-words' : 'whitespace-pre',
                ]"
              >{{ selectedOutput }}</pre>
              <div
                v-else-if="selectedBg.process.status === 'running'"
                class="px-3 py-2 font-mono text-[11px] italic text-muted-foreground"
              >waiting for output…</div>
              <div
                v-else
                class="px-3 py-2 font-mono text-[11px] italic text-muted-foreground"
              >no output captured</div>
            </div>
            <button
              v-if="!stickToBottom && selectedOutput"
              type="button"
              class="absolute bottom-3 right-4 z-10 inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-card/95 px-3 py-1 text-[11px] text-primary shadow-md backdrop-blur-sm transition hover:bg-primary/15"
              title="Auto-scroll paused. Click to jump back to the latest output."
              @click="jumpToLatest"
            >
              <span class="text-base leading-none">↓</span>
              <span>jump to latest</span>
            </button>
          </div>

          <!-- Action footer (kill = direct backend POST, instant) -->
          <div class="flex items-center justify-end gap-2 border-t border-border/60 bg-card/40 px-3 py-1.5">
            <button
              v-if="selectedBg.process.status === 'running'"
              type="button"
              class="rounded-sm bg-destructive/15 px-2 py-1 text-[11px] text-destructive hover:bg-destructive/25"
              title="SIGTERM this process directly via the backend (5s grace, then SIGKILL)"
              @click="killBg"
            >■ stop</button>
            <span
              v-else
              class="text-[10px] text-muted-foreground"
            >process ended</span>
          </div>
        </template>

        <!-- USER PTY (xterm.js interactive terminal) -->
        <template v-else-if="selectedPty">
          <!-- Header with shell + pid + close -->
          <div class="flex items-center justify-between gap-2 border-b border-border bg-card/60 px-3 py-1 text-[11px]">
            <div class="flex min-w-0 items-center gap-2">
              <span :class="['inline-block h-2 w-2 rounded-full', selectedPty.pty.closed ? 'bg-muted-foreground/50' : 'bg-success']"></span>
              <span class="font-semibold text-foreground/80">{{ selectedPty.label }}</span>
              <span class="font-mono text-muted-foreground">pid {{ selectedPty.pty.pid }}</span>
              <span class="truncate font-mono text-[10px] text-muted-foreground">{{ selectedPty.pty.cwd }}</span>
            </div>
            <button
              type="button"
              class="rounded-sm border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-destructive/15 hover:text-destructive"
              title="Close terminal"
              @click="killSelectedPty"
            >× close</button>
          </div>

          <!-- The xterm canvas itself. v-show keeps every PTY's xterm
               instance mounted so switching between terminals is instant
               and preserves their scrollback. :key on the wrapper isn't
               used here on purpose — re-using the same XtermView would
               re-create the ws on switch. -->
          <div class="relative flex-1 min-h-0">
            <div
              v-for="e in ptyEntries"
              v-show="selectedEntry?.id === e.id"
              :key="e.id"
              class="absolute inset-0"
            >
              <XtermView :terminal-id="e.pty.id" :closed="e.pty.closed" />
            </div>
          </div>
        </template>

        <!-- EMPTY STATE -->
        <div
          v-else
          class="flex h-full flex-col items-center justify-center px-4 text-center text-xs text-muted-foreground"
        >
          <p class="mb-2">No terminal selected.</p>
          <button
            type="button"
            class="rounded-sm border border-border bg-background px-3 py-1 text-[11px] text-foreground hover:bg-accent"
            @click="newTerminal()"
          >+ New terminal</button>
        </div>
      </div>

      <!-- ─── SIDEBAR — VS Code-style terminal tab list ───────────── -->
      <aside
        class="flex w-56 shrink-0 flex-col border-l border-border bg-card"
      >
        <!-- Sidebar header: + new terminal button + dropdown picker -->
        <div class="relative flex items-center justify-between border-b border-border bg-card/60 px-2 py-1.5">
          <span class="text-[10px] uppercase tracking-wider text-muted-foreground">terminals</span>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="flex h-5 w-5 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              title="New terminal (default shell)"
              @click="newTerminal()"
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
                <path d="M8 3v10M3 8h10"/>
              </svg>
            </button>
            <button
              type="button"
              class="flex h-5 w-5 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              title="Choose shell…"
              @click="toggleShellPicker"
            >
              <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor"><path d="M3 5l5 6 5-6z"/></svg>
            </button>
          </div>
          <!-- Shell picker dropdown -->
          <div
            v-if="showShellPicker"
            class="absolute right-2 top-full z-30 mt-1 min-w-[180px] overflow-hidden rounded-md border border-border bg-card shadow-lg"
            @click.stop
          >
            <div class="border-b border-border/60 px-3 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              shell profile
            </div>
            <button
              v-for="p in store.shellProfiles"
              :key="p.id"
              type="button"
              class="block w-full px-3 py-1.5 text-left text-[12px] hover:bg-accent"
              @click="newTerminal(p.path)"
            >
              <span class="font-mono">{{ p.label }}</span>
              <span v-if="p.isDefault === 'true'" class="ml-2 text-[10px] text-muted-foreground">(default)</span>
              <div class="text-[10px] text-muted-foreground">{{ p.path }}</div>
            </button>
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto py-1">
          <!-- BASH SECTION -->
          <template v-if="bashEntries.length > 0">
            <div
              v-for="e in bashEntries"
              :key="e.id"
              :class="[
                'group/row flex cursor-pointer items-center gap-2 px-3 py-1.5 text-left transition-colors',
                selectedEntry && selectedEntry.id === e.id
                  ? 'bg-accent text-foreground'
                  : 'text-foreground/75 hover:bg-accent/40',
              ]"
              :title="commandFor(e.call)"
              @click="selectEntry(e.id)"
            >
              <span :class="['inline-block h-1.5 w-1.5 shrink-0 rounded-full', bashStatusDot(e.call)]"></span>
              <span class="min-w-0 flex-1 truncate font-mono text-[11px]">{{ e.label }}</span>
              <button
                type="button"
                class="opacity-0 group-hover/row:opacity-100 focus:opacity-100 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-destructive/20 hover:text-destructive"
                title="Remove from terminal list (chat card stays)"
                aria-label="Remove terminal entry"
                @click.stop="removeEntry(e.id)"
              >
                <!-- trash icon (12×12 stroke) -->
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M2.5 4h11"/>
                  <path d="M6.5 4V2.5h3V4"/>
                  <path d="M3.5 4l.7 9a1.2 1.2 0 0 0 1.2 1.1h5.2a1.2 1.2 0 0 0 1.2-1.1l.7-9"/>
                  <path d="M6.5 7v5"/>
                  <path d="M9.5 7v5"/>
                </svg>
              </button>
            </div>
          </template>

          <!-- BG SECTION (only when there are bg sessions) -->
          <template v-if="bgEntries.length > 0">
            <div class="mt-2 border-t border-border/50 px-3 pb-1 pt-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
              background
            </div>
            <div
              v-for="e in bgEntries"
              :key="e.id"
              :class="[
                'group/row flex cursor-pointer items-center gap-2 px-3 py-1.5 text-left transition-colors',
                selectedEntry && selectedEntry.id === e.id
                  ? 'bg-accent text-foreground'
                  : 'text-foreground/75 hover:bg-accent/40',
              ]"
              :title="e.process.command"
              @click="selectEntry(e.id)"
            >
              <span :class="['inline-block h-1.5 w-1.5 shrink-0 rounded-full', bgStatusDot(e.process.status !== 'running')]"></span>
              <span class="min-w-0 flex-1 truncate font-mono text-[11px]">{{ e.label }}</span>
            </div>
          </template>

          <!-- USER PTY SECTION — interactive terminals the user spawned -->
          <template v-if="ptyEntries.length > 0">
            <div class="mt-2 border-t border-border/50 px-3 pb-1 pt-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
              user terminals
            </div>
            <div
              v-for="e in ptyEntries"
              :key="e.id"
              :class="[
                'group/row flex cursor-pointer items-center gap-2 px-3 py-1.5 text-left transition-colors',
                selectedEntry && selectedEntry.id === e.id
                  ? 'bg-accent text-foreground'
                  : 'text-foreground/75 hover:bg-accent/40',
              ]"
              :title="`${e.pty.shell} · pid ${e.pty.pid} · ${e.pty.cwd}`"
              @click="selectEntry(e.id)"
            >
              <span :class="['inline-block h-1.5 w-1.5 shrink-0 rounded-full', e.pty.closed ? 'bg-muted-foreground/50' : 'bg-success']"></span>
              <span class="min-w-0 flex-1 truncate font-mono text-[11px]">
                {{ e.label }} <span class="text-muted-foreground">· {{ e.pty.pid }}</span>
              </span>
              <button
                type="button"
                class="opacity-0 group-hover/row:opacity-100 focus:opacity-100 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-destructive/20 hover:text-destructive"
                title="Close terminal"
                @click.stop="store.killUserTerminal(e.pty.id)"
              >
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
                  <path d="M4 4l8 8M12 4l-8 8"/>
                </svg>
              </button>
            </div>
          </template>

          <!-- Empty state — nudge the user to create their first terminal -->
          <div
            v-if="entries.length === 0"
            class="px-3 py-3 text-center text-[10px] text-muted-foreground"
          >
            No terminals yet.<br />
            Click <span class="font-mono text-foreground">+</span> to start one.
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>
