/**
 * Bottom terminal panel state: bash calls + bg processes + interactive PTYs.
 *
 * Three different sources merge into one chronological sidebar:
 *   - bash    — derived from chat messages (one entry per `bash` tool call)
 *   - bg      — derived from backend BackgroundProcessRegistry (live tail
 *               via `bg_*` WS events; the chat store fans them in here)
 *   - pty     — interactive shells the user opened in this pane
 *
 * The chat store calls `applyBgEvent()` whenever a `bg_*` WS event arrives.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

import * as bgApi from "../api/bg";
import * as termApi from "../api/terminals";
import type { ShellProfile } from "../api/types";
import type { ToolCall } from "../types/rpc";

import { useChatStore } from "./chat";
import { useUiStore } from "./ui";
import { useWorkspaceStore } from "./workspace";

// ── internal types ──────────────────────────────────────────────────────
interface BgProcess {
  id: string;
  name: string;
  command: string;
  pid: number;
  stdoutFile: string;
  stderrFile: string;
  startedAt: number;
  endedAt: number | null;
  exitCode: number | null;
  status: string;
  /** Capped at ~256 KB; oldest 25% drops when full. */
  output: string;
}

interface PtyTerminal {
  id: string;
  pid: number;
  shell: string;
  cwd: string;
  cols: number;
  rows: number;
  closed: boolean;
  startedAt: number;
}

interface BashTerminalEntry {
  kind: "bash";
  id: string;
  label: string;
  sortKey: number;
  call: ToolCall;
}
interface BgTerminalEntry {
  kind: "bg";
  id: string;
  label: string;
  sortKey: number;
  process: BgProcess;
}
interface PtyTerminalEntry {
  kind: "pty";
  id: string;
  label: string;
  sortKey: number;
  pty: PtyTerminal;
}
export type TerminalEntry = BashTerminalEntry | BgTerminalEntry | PtyTerminalEntry;

const BG_OUTPUT_MAX_BYTES = 256 * 1024;

function _appendBgOutput(rec: BgProcess, chunk: string): void {
  let next = rec.output + chunk;
  if (next.length > BG_OUTPUT_MAX_BYTES) {
    next = next.slice(next.length - Math.floor(BG_OUTPUT_MAX_BYTES * 0.75));
  }
  rec.output = next;
}

// ── localStorage helpers (terminal layout) ──────────────────────────────
function _loadNum(key: string, fallback: number, min: number, max: number): number {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(key);
  if (!raw) return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}
function _loadBool(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(key);
  if (raw === null) return fallback;
  return raw === "1" || raw === "true";
}
function _saveNum(key: string, value: number): void {
  try {
    window.localStorage.setItem(key, String(Math.round(value)));
  } catch {
    /* */
  }
}
function _saveBool(key: string, value: boolean): void {
  try {
    window.localStorage.setItem(key, value ? "1" : "0");
  } catch {
    /* */
  }
}

// ── bash command label ──────────────────────────────────────────────────
function _labelForBashCommand(cmd: string): string {
  if (!cmd) return "bash";
  let s = cmd.trim();
  const wrapper = /^(?:bash|sh|zsh|env(?:\s+\S+=\S+)*)\s+(?:-\w+\s+)*['"]?(.+?)['"]?$/;
  const m = wrapper.exec(s);
  if (m) s = m[1]!.trim();
  const firstLine = s.split("\n")[0]!.trim();
  const max = 32;
  return firstLine.length > max ? firstLine.slice(0, max - 1) + "…" : firstLine;
}

/**
 * Background-command heuristic. Pessimistic by design — false positives
 * are cheap (an extra badge); false negatives confuse the user when their
 * server "dies" (it didn't, the bash tool just exited).
 */
export function isBackgroundCommand(cmd: string): boolean {
  if (!cmd) return false;
  const lower = cmd.toLowerCase();
  if (/(?<![&>|])&(?!&)(?=[\s;#`'"]|$)/m.test(cmd)) return true;
  if (/\b(nohup|disown|setsid)\b/.test(lower)) return true;
  if (/\b(npm run dev|npm start|yarn dev|pnpm dev|vite|next dev|uvicorn|gunicorn|flask run|rails server)\b/.test(lower)) {
    return true;
  }
  return false;
}

export const useTerminalsStore = defineStore("terminals", () => {
  const ui = useUiStore();

  // Layout state (persisted)
  const expanded = ref(false);
  const focusedToolCallId = ref<string | null>(null);
  const focusedBgId = ref<string | null>(null);
  const height = ref<number>(_loadNum("pi.term.height", 320, 120, 1200));
  const wrap = ref<boolean>(_loadBool("pi.term.wrap", false));

  // Data state
  const bgProcesses = ref<Record<string, BgProcess>>({});
  const userTerminals = ref<PtyTerminal[]>([]);
  const activeUserTerminalId = ref<string | null>(null);
  const shellProfiles = ref<ShellProfile[]>([]);
  // Bash tool calls appear in the bottom Terminal Pane ONLY when the user
  // explicitly opts in via the "Open in Terminal Pane" menu item on a
  // BashToolCard. The previous behaviour — auto-show every bash call —
  // turned the panel into a noisy spam of every command the agent ran,
  // which the user explicitly didn't want. Empty set = nothing shown by
  // default. The pin survives until session reset; closing a pinned tab
  // (the "x" button on the entry) just removes it from this set.
  const pinnedBashIds = ref<Set<string>>(new Set());

  // ── derived ──────────────────────────────────────────────────────────
  const bashCalls = computed<ToolCall[]>(() => {
    const chat = useChatStore();
    const out: ToolCall[] = [];
    for (const m of chat.messages) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) if (tc.name === "bash") out.push(tc);
    }
    return out;
  });

  const processCalls = computed<ToolCall[]>(() => {
    const chat = useChatStore();
    const out: ToolCall[] = [];
    for (const m of chat.messages) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) if (tc.name === "process") out.push(tc);
    }
    return out;
  });

  const backgroundProcesses = computed<BgProcess[]>(() =>
    Object.values(bgProcesses.value).sort((a, b) => {
      const aLive = a.status === "running";
      const bLive = b.status === "running";
      if (aLive !== bLive) return aLive ? -1 : 1;
      return a.startedAt - b.startedAt;
    })
  );

  const activeBackgroundCount = computed(
    () => backgroundProcesses.value.filter((p) => p.status === "running").length
  );

  const entries = computed<TerminalEntry[]>(() => {
    const chat = useChatStore();
    const out: TerminalEntry[] = [];
    const pinned = pinnedBashIds.value;

    // Only bash calls the user explicitly pinned (via "Open in Terminal
    // Pane") appear here. Every bash call is still visible inline in
    // the chat as a BashToolCard — the terminal pane is a focused
    // sidebar, not an audit log of every command the agent ran.
    for (const m of chat.messages) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) {
        if (tc.name !== "bash" || !pinned.has(tc.id)) continue;
        const args = tc.args as { command?: unknown } | undefined;
        const cmd = typeof args?.command === "string" ? args.command : "";
        out.push({
          kind: "bash",
          id: `bash:${tc.id}`,
          label: _labelForBashCommand(cmd),
          sortKey: tc.startedAt ?? 0,
          call: tc,
        });
      }
    }

    for (const proc of backgroundProcesses.value) {
      out.push({
        kind: "bg",
        id: `bg:${proc.id}`,
        label: proc.name || proc.id,
        sortKey: proc.startedAt,
        process: proc,
      });
    }

    for (const t of userTerminals.value) {
      const shellName = t.shell.split("/").pop() ?? t.shell;
      out.push({
        kind: "pty",
        id: `pty:${t.id}`,
        label: shellName,
        sortKey: t.startedAt + 1e15,
        pty: t,
      });
    }

    out.sort((a, b) => a.sortKey - b.sortKey);
    return out;
  });

  // ── bg event ingestion (called by chat store on bg_* WS events) ──────
  function applyBgEvent(evt: Record<string, unknown>): boolean {
    const t = evt.type;
    if (t === "bg_started") {
      const proc = (evt.process ?? {}) as Record<string, unknown>;
      const id = String(proc.id ?? "");
      if (!id) return true;
      bgProcesses.value = {
        ...bgProcesses.value,
        [id]: {
          id,
          name: String(proc.name ?? id),
          command: String(proc.command ?? ""),
          pid: Number(proc.pid ?? 0),
          stdoutFile: String(proc.stdoutFile ?? ""),
          stderrFile: String(proc.stderrFile ?? ""),
          startedAt: Number(proc.startTime ?? Date.now()),
          endedAt: null,
          exitCode: null,
          status: String(proc.status ?? "running"),
          output: "",
        },
      };
      // We used to auto-expand the panel + auto-focus the new bg
      // process here. The user asked us to keep the terminal panel
      // passive — it should never pop open by itself, only when they
      // click. Background processes still get registered in the
      // store (so the count badge in the panel header updates and the
      // Process tool card has data to render) but the panel itself
      // stays collapsed.
      return true;
    }
    if (t === "bg_output") {
      const id = String(evt.id ?? "");
      const chunk = String(evt.chunk ?? "");
      const rec = bgProcesses.value[id];
      if (!rec || !chunk) return true;
      _appendBgOutput(rec, chunk);
      bgProcesses.value = { ...bgProcesses.value };
      return true;
    }
    if (t === "bg_ended") {
      const id = String(evt.id ?? "");
      const rec = bgProcesses.value[id];
      if (!rec) return true;
      const status = typeof evt.status === "string" ? (evt.status as string) : "exited";
      const exitCode = typeof evt.exitCode === "number" ? (evt.exitCode as number) : null;
      bgProcesses.value = {
        ...bgProcesses.value,
        [id]: { ...rec, status, exitCode, endedAt: Date.now() },
      };
      return true;
    }
    return false;
  }

  // ── interactive PTYs ─────────────────────────────────────────────────
  async function loadShellProfiles(): Promise<void> {
    try {
      const data = await termApi.listShellProfiles();
      shellProfiles.value = data.profiles;
    } catch {
      /* silent — profile listing is non-critical */
    }
  }

  /** Resolve the active workspace id, or null. All terminal/bg actions
   * are workspace-scoped on the backend now, so any call without an
   * active workspace is a no-op (the picker view never has terminals
   * open anyway). */
  function _activeWsid(): string | null {
    return useWorkspaceStore().activeId ?? null;
  }

  async function refreshUserTerminals(): Promise<void> {
    const wsid = _activeWsid();
    if (!wsid) return;
    try {
      const data = await termApi.listTerminals(wsid);
      userTerminals.value = (data.terminals ?? []) as PtyTerminal[];
    } catch {
      /* silent */
    }
  }

  async function createUserTerminal(shell?: string): Promise<PtyTerminal | null> {
    const wsid = _activeWsid();
    if (!wsid) {
      ui.toastError("No workspace open", "Pick a workspace before opening a terminal.");
      return null;
    }
    try {
      const term = (await termApi.createTerminal(wsid, {
        shell: shell ?? "default",
      })) as PtyTerminal;
      userTerminals.value = [...userTerminals.value, term];
      activeUserTerminalId.value = term.id;
      expanded.value = true;
      return term;
    } catch (exc) {
      ui.toastError("Could not create terminal", exc);
      return null;
    }
  }

  async function killUserTerminal(id: string): Promise<void> {
    const wsid = _activeWsid();
    if (wsid) {
      try {
        await termApi.deleteTerminal(wsid, id);
      } catch {
        /* swallow — the entry is removed locally regardless */
      }
    }
    userTerminals.value = userTerminals.value.filter((t) => t.id !== id);
    if (activeUserTerminalId.value === id) {
      activeUserTerminalId.value = userTerminals.value[0]?.id ?? null;
    }
  }

  function selectUserTerminal(id: string): void {
    activeUserTerminalId.value = id;
    expanded.value = true;
  }

  // ── focus + layout ───────────────────────────────────────────────────
  function focusToolCall(toolCallId: string): void {
    focusedToolCallId.value = toolCallId;
    expanded.value = true;
  }
  function setExpanded(value: boolean): void {
    expanded.value = value;
    if (!value) focusedToolCallId.value = null;
  }
  function clearFocus(): void {
    focusedToolCallId.value = null;
  }
  function setHeight(px: number): void {
    const clamped = Math.min(1200, Math.max(120, Math.round(px)));
    height.value = clamped;
    _saveNum("pi.term.height", clamped);
  }
  function toggleWrap(): void {
    wrap.value = !wrap.value;
    _saveBool("pi.term.wrap", wrap.value);
  }

  /** Pin a bash tool call into the terminal pane so it gets its own
   * tab. Called from BashToolCard's "Open in Terminal Pane" menu item.
   * Idempotent — pinning an already-pinned call is a no-op. */
  function pinBashCall(toolCallId: string): void {
    if (pinnedBashIds.value.has(toolCallId)) return;
    const next = new Set(pinnedBashIds.value);
    next.add(toolCallId);
    pinnedBashIds.value = next;
  }

  /** Remove a bash tab from the terminal pane (the "x" close button on
   * the entry). The chat-side BashToolCard is untouched; this is purely
   * "close this tab". The user can reopen via the same menu item. */
  function removeBashCall(toolCallId: string): void {
    if (!pinnedBashIds.value.has(toolCallId)) return;
    const next = new Set(pinnedBashIds.value);
    next.delete(toolCallId);
    pinnedBashIds.value = next;
  }

  // ── bg-process control + bash-rerun helpers ──────────────────────────
  /**
   * "Re-run" a previously-executed bash command. We send it back to the
   * agent wrapped in a "run literally" prompt so the agent doesn't try
   * to "improve" it. Cheaper than rebuilding the bash tool input
   * ourselves, and matches how a user would re-issue the command.
   */
  function rerunBashCommand(command: string): void {
    if (!command.trim()) return;
    const escaped = command.replace(/'/g, "'\\''");
    const chat = useChatStore();
    chat.sendPrompt(`Run this bash command literally, no edits or commentary: ${escaped}`);
  }

  /**
   * Ask the agent to start a process via @aliou/pi-processes. The first
   * round-trip must go through the LLM (it owns the tool call); the
   * follow-up tail/kill are direct backend calls.
   */
  function dispatchBackground(command: string, name?: string, reason?: string): void {
    if (!command.trim()) return;
    const escaped = command.replace(/"/g, '\\"');
    const nameClause = name ? `, name: "${name}"` : "";
    const reasonClause = reason ? ` Reason: ${reason}.` : "";
    const chat = useChatStore();
    chat.sendPrompt(
      `Use the process tool to start this command in the background. ` +
        `Call it with action: "start", command: "${escaped}"${nameClause}.${reasonClause} ` +
        `Do not commentate, just call the tool once.`
    );
  }

  async function killBackgroundProcess(processId: string): Promise<void> {
    const wsid = _activeWsid();
    if (!wsid) return;
    try {
      await bgApi.killBgProcess(wsid, processId);
    } catch (exc) {
      ui.toastError("Could not kill process", exc);
    }
  }

  // ── reset (called on session change) ────────────────────────────────
  function resetForNewSession(): void {
    bgProcesses.value = {};
    pinnedBashIds.value = new Set();
    focusedToolCallId.value = null;
    focusedBgId.value = null;
  }

  return {
    expanded,
    focusedToolCallId,
    focusedBgId,
    height,
    wrap,
    bgProcesses,
    backgroundProcesses,
    activeBackgroundCount,
    bashCalls,
    processCalls,
    userTerminals,
    activeUserTerminalId,
    shellProfiles,
    entries,
    applyBgEvent,
    loadShellProfiles,
    refreshUserTerminals,
    createUserTerminal,
    killUserTerminal,
    selectUserTerminal,
    focusToolCall,
    setExpanded,
    clearFocus,
    setHeight,
    toggleWrap,
    pinBashCall,
    removeBashCall,
    rerunBashCommand,
    dispatchBackground,
    killBackgroundProcess,
    resetForNewSession,
  };
});
