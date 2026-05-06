<!--
  XtermView — interactive terminal session backed by a backend PTY.

  Lifecycle:
    1. Mount → connect to /ws/terminal/{id}.
    2. Pump keystrokes → ws (`{type:"input", data}`).
    3. Pump ws output → xterm.write(data).
    4. ResizeObserver → fit addon → ws (`{type:"resize", cols, rows}`).
    5. Unmount → close ws (but keep the PTY alive on the backend so a
       future re-mount picks up exactly where we left off).

  We intentionally do NOT kill the PTY on unmount — the user might just
  switch away to another terminal entry. Killing happens only when the
  user explicitly clicks the trash icon (handled by the parent).
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";

const props = defineProps<{
  terminalId: string;
  closed?: boolean;
}>();

const emit = defineEmits<{
  (e: "exit"): void;
}>();

const root = ref<HTMLDivElement | null>(null);
const status = ref<"connecting" | "open" | "exited" | "error">("connecting");
const errorMsg = ref<string | null>(null);

let term: Terminal | null = null;
let fitAddon: FitAddon | null = null;
let ws: WebSocket | null = null;
let resizeObs: ResizeObserver | null = null;
// We coalesce resize events so dragging the splitpane divider doesn't
// flood the websocket with hundreds of resize frames.
let resizeTimer: number | null = null;

function buildWsUrl(id: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  // Vite dev server proxies /ws/* to FastAPI on :8000.
  return `${proto}//${window.location.host}/ws/terminal/${encodeURIComponent(id)}`;
}

function fitAndSend(): void {
  if (!fitAddon || !ws || ws.readyState !== WebSocket.OPEN) return;
  try {
    fitAddon.fit();
    const cols = term?.cols ?? 80;
    const rows = term?.rows ?? 24;
    ws.send(JSON.stringify({ type: "resize", cols, rows }));
  } catch {
    // Resize during teardown is harmless.
  }
}

function scheduleFit(): void {
  if (resizeTimer != null) window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(() => {
    resizeTimer = null;
    fitAndSend();
  }, 80);
}

function setupTerminal(): void {
  if (!root.value) return;
  term = new Terminal({
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
    fontSize: 13,
    lineHeight: 1.2,
    cursorBlink: true,
    cursorStyle: "block",
    allowProposedApi: true,
    convertEol: false,
    scrollback: 5000,
    // VS Code "Dark+" inspired palette tuned to match our editor.
    theme: {
      background: "#0f0f12",
      foreground: "#e6e6ea",
      cursor: "#e6e6ea",
      cursorAccent: "#0f0f12",
      selectionBackground: "rgba(120, 200, 255, 0.25)",
      black: "#1f1f23",
      red: "#f15a5a",
      green: "#7ee787",
      yellow: "#f0c674",
      blue: "#79c0ff",
      magenta: "#d2a8ff",
      cyan: "#7fdbca",
      white: "#cfcfd4",
      brightBlack: "#5a5a64",
      brightRed: "#ff8080",
      brightGreen: "#a6f0a6",
      brightYellow: "#ffd580",
      brightBlue: "#9fcfff",
      brightMagenta: "#e2c3ff",
      brightCyan: "#a6f0e0",
      brightWhite: "#ffffff",
    },
  });
  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.loadAddon(new WebLinksAddon());
  term.open(root.value);
  // Initial sizing — must happen AFTER open() so the renderer has a
  // canvas to measure.
  requestAnimationFrame(() => {
    fitAndSend();
    term?.focus();
  });

  term.onData((data) => {
    // User typed something — forward raw bytes to the PTY.
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "input", data }));
    }
  });
}

function connect(): void {
  ws = new WebSocket(buildWsUrl(props.terminalId));
  ws.onopen = () => {
    status.value = "open";
    // Defer fitAndSend; xterm DOM may still be settling.
    requestAnimationFrame(fitAndSend);
  };
  ws.onmessage = (e) => {
    if (typeof e.data !== "string") return;
    let msg: { type?: string; data?: string };
    try {
      msg = JSON.parse(e.data);
    } catch {
      return;
    }
    if (msg.type === "output" && typeof msg.data === "string") {
      term?.write(msg.data);
    } else if (msg.type === "ready") {
      status.value = "open";
    } else if (msg.type === "exit") {
      status.value = "exited";
      term?.write("\r\n\x1b[2m[process exited]\x1b[0m\r\n");
      emit("exit");
    }
  };
  ws.onerror = () => {
    status.value = "error";
    errorMsg.value = "WebSocket error";
  };
  ws.onclose = () => {
    if (status.value !== "exited") status.value = "exited";
  };
}

onMounted(() => {
  setupTerminal();
  connect();
  if (root.value && typeof ResizeObserver !== "undefined") {
    resizeObs = new ResizeObserver(scheduleFit);
    resizeObs.observe(root.value);
  }
});

onBeforeUnmount(() => {
  resizeObs?.disconnect();
  resizeObs = null;
  if (resizeTimer != null) window.clearTimeout(resizeTimer);
  resizeTimer = null;
  // Leave the PTY alive — only close the ws.
  try {
    ws?.close();
  } catch {
    /* ignore */
  }
  ws = null;
  term?.dispose();
  term = null;
  fitAddon = null;
});

// If the parent reports the terminal closed (e.g. user killed it from
// the sidebar), tear down our ws — there's nothing to listen to.
watch(
  () => props.closed,
  (isClosed) => {
    if (isClosed && ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.close();
      } catch {
        /* ignore */
      }
    }
  },
);

// If the user picks a different terminal, the parent gives us a new
// :terminalId via :key remount — we don't have to handle id changes
// in-place here. (Keeping each xterm instance pinned to one PTY makes
// the buffers stable.)
</script>

<template>
  <div class="xterm-host relative flex h-full w-full flex-col bg-[#0f0f12]">
    <div ref="root" class="xterm-canvas flex-1 overflow-hidden p-1"></div>
    <div
      v-if="status !== 'open'"
      class="absolute right-2 top-2 rounded-sm bg-card/90 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground shadow"
    >
      {{ status }}<span v-if="errorMsg"> · {{ errorMsg }}</span>
    </div>
  </div>
</template>

<style scoped>
.xterm-host {
  /* xterm hates being smaller than its measured size; min-height keeps
     fitAddon happy when the pane is collapsed momentarily. */
  min-height: 80px;
}
.xterm-canvas :deep(.xterm) {
  height: 100%;
  width: 100%;
}
.xterm-canvas :deep(.xterm-viewport) {
  background-color: transparent !important;
}
</style>
