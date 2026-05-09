<!--
  ProcessToolCard — renders @aliou/pi-processes `process` tool calls.

  The `process` tool dispatches by `action`:

    start       spawn a daemon, returns {id, pid, stdoutFile, stderrFile}
    list        list every process the extension currently tracks
    output      tail the stdout/stderr of one process
    logs        return file paths so the agent can read() them directly
    kill        SIGTERM (then SIGKILL) one process by id
    clear       drop finished processes from the extension's list
    write       send input to a running process's stdin

  We render each variant with a compact header + the result text. The
  TerminalPane is what surfaces *live* output (via WS bg_* events); the
  card is just the chat record of "the agent did this".
-->
<script setup lang="ts">
import { computed } from "vue";
import { useTerminalsStore } from "../../stores/terminals";
import type { ToolCall } from "../../types/rpc";

const props = defineProps<{ call: ToolCall }>();
const terminals = useTerminalsStore();

interface ProcessArgs {
  action?: unknown;
  name?: unknown;
  command?: unknown;
  id?: unknown;
  input?: unknown;
}

const args = computed<ProcessArgs>(() => (props.call.args ?? {}) as ProcessArgs);

const action = computed(() => {
  const a = args.value.action;
  return typeof a === "string" ? a : "process";
});

/** Header glyph + label per action. */
const title = computed<{ icon: string; label: string; tone: string }>(() => {
  switch (action.value) {
    case "start":
      return { icon: "⏵", label: "start", tone: "text-primary" };
    case "list":
      return { icon: "≡", label: "list", tone: "text-muted-foreground" };
    case "output":
      return { icon: "↻", label: "output", tone: "text-muted-foreground" };
    case "logs":
      return { icon: "📄", label: "logs", tone: "text-muted-foreground" };
    case "kill":
      return { icon: "■", label: "kill", tone: "text-destructive" };
    case "clear":
      return { icon: "✕", label: "clear", tone: "text-muted-foreground" };
    case "write":
      return { icon: "→", label: "write stdin", tone: "text-foreground/90" };
    default:
      return { icon: "·", label: action.value, tone: "text-muted-foreground" };
  }
});

const command = computed(() => {
  const c = args.value.command;
  return typeof c === "string" ? c : "";
});

const name = computed(() => {
  const n = args.value.name;
  return typeof n === "string" ? n : "";
});

const targetId = computed(() => {
  const i = args.value.id;
  return typeof i === "string" ? i : "";
});

interface ProcessDetails {
  action?: string;
  success?: boolean;
  message?: string;
  process?: {
    id?: string;
    name?: string;
    pid?: number;
    command?: string;
    stdoutFile?: string;
    stderrFile?: string;
    status?: string;
    exitCode?: number | null;
  };
  processes?: Array<{ id?: string; name?: string; status?: string; pid?: number }>;
  logFiles?: { stdoutFile?: string; stderrFile?: string };
}

const details = computed<ProcessDetails>(
  () => (props.call.result?.details as ProcessDetails) ?? {},
);

const startedProcess = computed(() => {
  if (action.value !== "start") return null;
  return details.value.process ?? null;
});

const isStreaming = computed(
  () => props.call.status === "pending" || props.call.status === "running",
);
const statusBadge = computed(() => {
  switch (props.call.status) {
    case "pending":
      return { label: "queued", color: "text-muted-foreground bg-muted" };
    case "running":
      return { label: "running", color: "text-warning bg-warning/15" };
    case "success":
      return { label: "ok", color: "text-success bg-success/15" };
    case "error":
      return { label: "error", color: "text-destructive bg-destructive/15" };
  }
});

const resultText = computed(() => props.call.result?.text ?? "");

function focusTerminalForProcess(processId: string): void {
  // Open the terminal pane and select this process's bg entry. The
  // TerminalPane watches `focusedBgId` and switches its sidebar
  // selection accordingly.
  terminals.setExpanded(true);
  terminals.focusedBgId = processId;
}

function killProcess(processId: string): void {
  void terminals.killBackgroundProcess(processId);
}
</script>

<template>
  <div
    class="group my-1.5 overflow-hidden rounded-md border border-border bg-card transition-colors hover:border-border/80"
  >
    <!-- ── HEADER ─────────────────────────────────────────────────────── -->
    <div class="flex items-center gap-2 px-2.5 py-1.5 font-mono text-body">
      <span class="inline-flex h-4 w-4 items-center justify-center rounded-sm bg-muted text-caption font-semibold text-muted-foreground">
        ⌘
      </span>
      <span class="font-semibold text-foreground/90">process</span>
      <span class="text-muted-foreground">·</span>
      <span :class="['truncate', title.tone]">
        <span class="select-none">{{ title.icon }}</span>
        <span class="ml-1">{{ title.label }}</span>
      </span>
      <span
        v-if="name && action === 'start'"
        class="ml-1 truncate text-foreground/80"
      >&quot;{{ name }}&quot;</span>
      <span
        v-else-if="targetId"
        class="ml-1 truncate text-foreground/80"
      >{{ targetId }}</span>

      <span class="flex-1"></span>

      <span :class="['rounded-sm px-1.5 py-0.5 text-caption', statusBadge.color]">{{ statusBadge.label }}</span>

      <!-- For successful start: open terminal + kill buttons -->
      <template v-if="!isStreaming && startedProcess?.id">
        <button
          type="button"
          class="rounded-sm bg-muted px-1.5 py-0.5 text-caption hover:bg-accent hover:text-foreground"
          title="Open this process in the terminal pane (live tail)"
          @click="focusTerminalForProcess(startedProcess.id!)"
        >open</button>
        <button
          type="button"
          class="rounded-sm bg-destructive/15 px-1.5 py-0.5 text-caption text-destructive hover:bg-destructive/25"
          title="SIGTERM this process directly via the backend"
          @click="killProcess(startedProcess.id!)"
        >stop</button>
      </template>
    </div>

    <!-- ── COMMAND (only shown for start) ─────────────────────────────── -->
    <div v-if="command && action === 'start'" class="border-t border-border bg-editor">
      <pre
        class="max-h-48 overflow-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-[11.5px] leading-[1.55] text-foreground/95"
      ><span class="select-none text-muted-foreground">$ </span>{{ command }}</pre>
    </div>

    <!-- ── RESULT TEXT ────────────────────────────────────────────────── -->
    <div
      v-if="resultText"
      class="border-t border-border bg-background"
    >
      <pre
        class="max-h-72 overflow-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-[11.5px] leading-[1.5] text-foreground/90"
      >{{ resultText }}</pre>
      <div
        v-if="startedProcess && startedProcess.id && startedProcess.pid"
        class="border-t border-border/60 bg-muted/30 px-3 py-1 font-mono text-caption text-muted-foreground"
      >
        id: <span class="text-foreground/80">{{ startedProcess.id }}</span>
        · pid: <span class="text-foreground/80 tabular-nums">{{ startedProcess.pid }}</span>
        <span v-if="startedProcess.stdoutFile" class="ml-2 italic">
          live output streams in the terminal pane below ↓
        </span>
      </div>
    </div>

    <div
      v-else-if="isStreaming"
      class="border-t border-border bg-background px-3 py-2 font-mono text-caption italic text-muted-foreground"
    >waiting for tool result…</div>
  </div>
</template>
