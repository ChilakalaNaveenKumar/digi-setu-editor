<!--
  BashToolCard — Cursor-style terminal card for the `bash` tool.

  Layout:
    ┌─ header ──────────────────────────────────────────────────────────┐
    │ >_  bash   the · command · preview                bash · 1.2s  ⋯  │
    ├───────────────────────────────────────────────────────────────────┤
    │ $ shiki-highlighted command                                       │
    ├───────────────────────────────────────────────────────────────────┤
    │ ┃ live (or final) stdout/stderr, last N lines, expand to see all  │
    └───────────────────────────────────────────────────────────────────┘

  Streaming source: `tool_execution_update` events deliver the cumulative
  stdout as a snapshot. The event-router writes them to `call.streamingOutput`
  and Vue reactivity pushes the update straight into the body — no
  diff/concat work in the component.

  ⋯ menu items (dropdown, no extra deps):
    • Copy command
    • Copy output
    • Open in Terminal Pane
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useChatStore } from "../../stores/chat";
import { isBackgroundCommand, useTerminalsStore } from "../../stores/terminals";
import { getHighlighter } from "../../lib/highlighter";
import { useFloatingMenu } from "../../lib/floating-menu";
import type { ToolCall } from "../../types/rpc";

const props = defineProps<{ call: ToolCall }>();

const chat = useChatStore();
const terminals = useTerminalsStore();

/** True when the command will likely fork a long-running background process. */
const isBackground = computed(() => isBackgroundCommand(command.value));

/**
 * pi attaches `details.truncation` (TruncationResult) and
 * `details.fullOutputPath` to the bash result when output exceeded the
 * default limits. Surface that explicitly so the user knows the on-card
 * preview isn't the full story.
 */
interface BashTruncation {
  truncated: boolean;
  truncatedBy: "lines" | "bytes" | null;
  totalLines?: number;
  outputLines?: number;
  totalBytes?: number;
  maxBytes?: number;
}
const truncationInfo = computed<{
  truncation: BashTruncation | null;
  fullOutputPath: string | null;
}>(() => {
  const details = props.call.result?.details as
    | { truncation?: BashTruncation; fullOutputPath?: string }
    | undefined;
  return {
    truncation: details?.truncation && details.truncation.truncated ? details.truncation : null,
    fullOutputPath: typeof details?.fullOutputPath === "string" ? details.fullOutputPath : null,
  };
});

const command = computed(() => {
  const args = props.call.args as { command?: unknown } | undefined;
  return typeof args?.command === "string" ? args.command : "";
});

const timeout = computed(() => {
  const args = props.call.args as { timeout?: unknown } | undefined;
  return typeof args?.timeout === "number" ? args.timeout : null;
});

/** Live or final output — whichever we have. */
const output = computed(() => {
  if (props.call.status === "running" || props.call.status === "pending") {
    return props.call.streamingOutput ?? "";
  }
  return props.call.result?.text ?? props.call.streamingOutput ?? "";
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
      return { label: "done", color: "text-success bg-success/15" };
    case "error":
      return { label: "error", color: "text-destructive bg-destructive/15" };
  }
});

/** Formatted duration ("0.4s", "12s", "1m 03s"). Live ticks while running. */
const tickNow = ref(Date.now());
let tickHandle: number | null = null;
onMounted(() => {
  tickHandle = window.setInterval(() => {
    tickNow.value = Date.now();
  }, 250);
});
onUnmounted(() => {
  if (tickHandle !== null) window.clearInterval(tickHandle);
});

const durationLabel = computed(() => {
  const start = props.call.startedAt;
  if (start === undefined) return "";
  const end = props.call.endedAt ?? tickNow.value;
  const ms = Math.max(0, end - start);
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const mins = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${mins}m ${rem.toString().padStart(2, "0")}s`;
});

// ── shiki highlight for the command body ───────────────────────────────
const highlightedHtml = ref<string>("");

async function refreshHighlight(): Promise<void> {
  const src = command.value;
  if (!src) {
    highlightedHtml.value = "";
    return;
  }
  try {
    const hl = await getHighlighter();
    // codeToHtml gives a self-contained <pre><code> but we want to control
    // padding/scrolling, so use codeToTokens and stitch ourselves.
    const tokens = hl.codeToTokens(src, { lang: "bash", theme: "github-dark-default" });
    const lines = tokens.tokens
      .map((line) =>
        line
          .map(
            (tok) =>
              `<span style="color:${tok.color ?? "inherit"}">${escapeHtml(tok.content)}</span>`,
          )
          .join(""),
      )
      .join("\n");
    highlightedHtml.value = lines;
  } catch {
    highlightedHtml.value = escapeHtml(src);
  }
}

watch(command, refreshHighlight, { immediate: true });

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── output truncation ───────────────────────────────────────────────────
const expanded = ref(false);
const PREVIEW_LINES = 12;

const outputLines = computed(() => {
  const o = output.value;
  if (!o) return [] as string[];
  return o.split("\n");
});

const visibleOutputLines = computed(() => {
  const lines = outputLines.value;
  if (expanded.value || lines.length <= PREVIEW_LINES) return lines;
  // Show the LAST N lines (terminals show recent output, not the head)
  return lines.slice(-PREVIEW_LINES);
});

const hiddenLineCount = computed(() => {
  if (expanded.value) return 0;
  return Math.max(0, outputLines.value.length - PREVIEW_LINES);
});

// ── ⋯ menu ──────────────────────────────────────────────────────────────
//
// The menu used to be `<div class="absolute right-0 top-6 z-20 w-48">`,
// which clipped at the bottom of the chat scroll on tool cards rendered
// near the viewport edge — users couldn't see "Copy output" / "Re-run"
// / "Open in Terminal Pane". Now it teleports to <body>, positions
// itself fixed via useFloatingMenu, and flips up automatically when
// there's no room below the trigger.
const menuOpen = ref(false);
const menuRef = ref<HTMLDivElement | null>(null);
const menuTriggerRef = ref<HTMLButtonElement | null>(null);
const menuPopoverRef = ref<HTMLDivElement | null>(null);

// Width 192 px = w-48; height 160 px = 4 buttons (~32 px) + 1 separator
// (~1 px) + a little padding. The composable clamps maxHeight to the
// available space below/above and the popover element gets its own
// `overflow-y-auto` so even on a 320-px-tall viewport every action is
// reachable via scrolling inside the menu.
const { menuStyle, reposition: repositionMenu } = useFloatingMenu(
  menuTriggerRef,
  { width: 192, height: 160, align: "right" },
);

function toggleMenu(): void {
  if (!menuOpen.value) {
    // Reposition BEFORE the menu becomes visible so the first paint
    // already lands at the right anchor — eliminates the flash that
    // would otherwise happen if we let the off-screen default styles
    // through.
    repositionMenu();
  }
  menuOpen.value = !menuOpen.value;
}

function closeMenu(): void {
  menuOpen.value = false;
}

watch(menuOpen, async (v) => {
  if (!v) return;
  await nextTick();
  repositionMenu();
});

function onDocClick(e: MouseEvent): void {
  // Click outside both the trigger AND the teleported popover closes.
  // Without checking the popover too, clicking inside the popover
  // (e.g. the action buttons) would close the menu out from under
  // the user before the action ran.
  const target = e.target as Node;
  if (menuTriggerRef.value && menuTriggerRef.value.contains(target)) return;
  if (menuPopoverRef.value && menuPopoverRef.value.contains(target)) return;
  // Legacy menuRef still wraps the trigger button — keep compat.
  if (menuRef.value && menuRef.value.contains(target)) return;
  closeMenu();
}

onMounted(() => document.addEventListener("click", onDocClick));
onUnmounted(() => document.removeEventListener("click", onDocClick));

const copiedFlash = ref<"command" | "output" | null>(null);

async function copyCommand(): Promise<void> {
  await navigator.clipboard.writeText(command.value);
  copiedFlash.value = "command";
  setTimeout(() => (copiedFlash.value = null), 1200);
  closeMenu();
}

async function copyOutput(): Promise<void> {
  await navigator.clipboard.writeText(output.value);
  copiedFlash.value = "output";
  setTimeout(() => (copiedFlash.value = null), 1200);
  closeMenu();
}

function openInTerminal(): void {
  // Pin this bash call into the terminal pane (it isn't there by
  // default — the user opted in by clicking this menu item), then
  // expand the pane and focus the new entry. The watch in
  // TerminalPane.vue picks up `focusedToolCallId` and selects the
  // matching tab.
  terminals.pinBashCall(props.call.id);
  terminals.setExpanded(true);
  terminals.focusToolCall(props.call.id);
  closeMenu();
}

function stopRunning(): void {
  // pi RPC abort kills the WHOLE turn (and SIGKILL on the bash process
  // group). It's the only stop hook pi exposes, but for the user this is
  // the expected behaviour: "stop what the agent is doing right now".
  chat.abort();
}

function rerun(): void {
  terminals.rerunBashCommand(command.value);
  closeMenu();
}

const runtimeBadge = computed(() => {
  if (!isBackground.value) return null;
  return {
    label: "background",
    title:
      "This command spawns a background process. The card will flip to 'done' when the foreground exits — but the daemon keeps running. Use `nohup … &` + redirect for clean detach.",
  };
});
</script>

<template>
  <div
    class="group my-1.5 overflow-hidden rounded-md border border-border bg-card transition-colors hover:border-border/80"
  >
    <!-- ── HEADER (meta only — full command lives in body) ────────────── -->
    <div class="flex items-center gap-2 px-2.5 py-1.5 font-mono text-body">
      <span
        class="inline-flex h-4 w-4 items-center justify-center rounded-sm bg-muted text-caption font-semibold text-muted-foreground"
      >&gt;_</span>
      <span class="font-semibold text-foreground/90">bash</span>
      <span class="text-muted-foreground">·</span>
      <span
        :class="['tabular-nums text-caption', statusBadge.color, 'rounded-sm px-1.5 py-0.5']"
      >{{ statusBadge.label }}</span>
      <span
        v-if="durationLabel"
        :class="[
          'text-caption tabular-nums',
          isStreaming ? 'text-warning' : 'text-muted-foreground',
        ]"
      >{{ durationLabel }}</span>
      <span
        v-if="timeout !== null"
        class="text-caption text-muted-foreground"
      >· timeout {{ timeout }}s</span>

      <!-- background hint badge — shown for `cmd &`, nohup, common dev servers -->
      <span
        v-if="runtimeBadge"
        class="inline-flex items-center gap-1 rounded-sm bg-primary/15 px-1.5 py-0.5 text-caption text-primary"
        :title="runtimeBadge.title"
      >
        <span class="inline-block h-1 w-1 rounded-full bg-primary"></span>
        {{ runtimeBadge.label }}
      </span>

      <!-- spacer pushes menu to the right -->
      <div class="flex-1"></div>

      <!-- STOP BUTTON — only visible while the command is in flight -->
      <button
        v-if="isStreaming"
        type="button"
        class="flex items-center gap-1 rounded-sm bg-destructive/15 px-1.5 py-0.5 text-caption text-destructive hover:bg-destructive/25"
        title="Stop this bash call (aborts the whole agent turn — kills the bash process group)"
        @click="stopRunning"
      >
        <span class="inline-block h-1.5 w-1.5 rounded-sm bg-destructive"></span>
        stop
      </button>

      <!-- ⋯ MENU TRIGGER -->
      <div ref="menuRef" class="relative">
        <button
          ref="menuTriggerRef"
          type="button"
          class="flex h-5 w-5 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          :title="menuOpen ? 'Close menu' : 'More actions'"
          @click.stop="toggleMenu"
        >⋯</button>

        <!-- Teleport so the popover escapes the chat scroll's
             overflow:hidden box and can render anywhere on the
             viewport without being clipped. Position + flip + maxHeight
             come from useFloatingMenu via menuStyle. -->
        <Teleport to="body">
          <div
            v-if="menuOpen"
            ref="menuPopoverRef"
            :style="menuStyle"
            class="z-50 max-h-[calc(100vh-16px)] overflow-y-auto overflow-x-hidden rounded-md border border-border bg-card shadow-lg"
            @click.stop
          >
            <button
              type="button"
              class="flex w-full items-center justify-between px-3 py-1.5 text-left text-body text-foreground hover:bg-accent"
              :disabled="!command"
              @click="copyCommand"
            >
              <span>Copy command</span>
              <span v-if="copiedFlash === 'command'" class="text-success text-caption">copied ✓</span>
            </button>
            <button
              type="button"
              class="flex w-full items-center justify-between px-3 py-1.5 text-left text-body text-foreground hover:bg-accent"
              :disabled="!output"
              @click="copyOutput"
            >
              <span>Copy output</span>
              <span v-if="copiedFlash === 'output'" class="text-success text-caption">copied ✓</span>
            </button>
            <div class="border-t border-border" />
            <button
              type="button"
              class="block w-full px-3 py-1.5 text-left text-body text-foreground hover:bg-accent"
              :disabled="!command || isStreaming"
              @click="rerun"
            >Re-run command</button>
            <button
              type="button"
              class="block w-full px-3 py-1.5 text-left text-body text-foreground hover:bg-accent"
              @click="openInTerminal"
            >Open in Terminal Pane</button>
          </div>
        </Teleport>
      </div>
    </div>

    <!-- ── COMMAND (full, wraps to next line, no truncation) ──────────── -->
    <div class="border-t border-border bg-editor">
      <pre
        class="max-h-64 overflow-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-[11.5px] leading-[1.55]"
      ><span class="select-none text-muted-foreground">$ </span><code
        v-if="highlightedHtml"
        v-html="highlightedHtml"
      /><code v-else>{{ command || "(streaming command…)" }}</code></pre>
    </div>

    <!-- ── OUTPUT ─────────────────────────────────────────────────────── -->
    <div
      v-if="output || isStreaming"
      class="border-t border-border bg-background"
    >
      <!-- Truncation banner (pi caps bash output to 2K lines / 256KB) -->
      <div
        v-if="truncationInfo.truncation"
        class="flex items-center justify-between gap-2 border-b border-warning/30 bg-warning/10 px-3 py-1 font-mono text-caption text-warning"
      >
        <span>
          ⚠ truncated by pi: showing
          <span class="tabular-nums">{{ truncationInfo.truncation.outputLines }}</span>
          of
          <span class="tabular-nums">{{ truncationInfo.truncation.totalLines }}</span>
          lines<template v-if="truncationInfo.truncation.truncatedBy === 'bytes'"> (byte limit hit)</template>
        </span>
        <span
          v-if="truncationInfo.fullOutputPath"
          class="truncate"
          :title="truncationInfo.fullOutputPath"
        >full output: {{ truncationInfo.fullOutputPath }}</span>
      </div>

      <div
        v-if="hiddenLineCount > 0"
        class="cursor-pointer select-none px-3 py-1 text-caption italic text-muted-foreground hover:bg-accent/30"
        @click="expanded = true"
      >
        … {{ hiddenLineCount }} earlier line{{ hiddenLineCount === 1 ? "" : "s" }} hidden · click to expand
      </div>
      <div
        v-if="expanded && outputLines.length > PREVIEW_LINES"
        class="cursor-pointer select-none px-3 py-1 text-caption italic text-muted-foreground hover:bg-accent/30"
        @click="expanded = false"
      >
        ▾ click to collapse
      </div>

      <pre
        class="max-h-72 overflow-auto whitespace-pre px-3 py-2 font-mono text-[11.5px] leading-[1.5] text-foreground"
      ><template v-if="visibleOutputLines.length"><span
          v-for="(line, i) in visibleOutputLines"
          :key="i"
        >{{ line }}<br /></span></template><span
        v-else-if="isStreaming"
        class="italic text-muted-foreground"
      >waiting for output…</span></pre>
    </div>

    <!-- ── ERROR FOOTER ───────────────────────────────────────────────── -->
    <div
      v-if="call.status === 'error' && !output"
      class="border-t border-destructive/30 bg-destructive/10 px-3 py-1.5 font-mono text-caption text-destructive"
    >
      {{ call.result?.text || "command failed" }}
    </div>
  </div>
</template>

<style scoped>
/*
 * Output `<br />` shim: <br> in a <pre> is fine but Safari sometimes
 * collapses two consecutive ones. Force normal line height to keep blanks
 * visible without needing to materialize a non-breaking space.
 */
pre :deep(br) {
  line-height: 1.5;
}
</style>
