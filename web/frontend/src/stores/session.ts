/**
 * Pinia store: WebSocket lifecycle + reduced ChatMessage list +
 * derived "current file" state for the editor pane.
 *
 * The editor pane is event-driven, not poll-driven: any time the agent
 * starts a `write` toolcall, we (1) create a reactive `currentFile`
 * record, (2) keep a pointer to the originating ToolCall, and (3) let
 * Vue reactivity push streaming content updates to the editor as
 * `toolcall_delta` events progressively fill in `args.content`.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { applyEvent, createRouterState, pushUserMessage } from "../lib/event-router";
import { parseDiff } from "../lib/diff-parse";
import { piDiffToUnified, writeContentToUnified } from "../lib/pi-diff-to-unified";
import type { ChatMessage, FileEntry, RpcEvent, ToolCall } from "../types/rpc";

const DEBUG_EVENTS =
  typeof window !== "undefined" && new URLSearchParams(window.location.search).has("debug");

// ── tiny localStorage helpers (for terminal layout persistence) ────────
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
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, String(Math.round(value)));
  } catch {
    /* quota / disabled — ignore */
  }
}

function _saveBool(key: string, value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value ? "1" : "0");
  } catch {
    /* quota / disabled — ignore */
  }
}

/**
 * Background-process detection. Returns true when the command will likely
 * fork off a long-running process that survives the bash tool's exit.
 *
 * Detection is deliberately pessimistic — we'd rather show the badge once
 * too often than confuse users into thinking a server is dead when it isn't.
 *
 * We DON'T strip quoted strings because the agent typically wraps the whole
 * command in `bash -c '...'`, putting the `&` inside the quotes. Instead the
 * regex carefully excludes `&&` (logical AND) and `>&N`/`2>&1` (fd redirects),
 * which covers the realistic false-positive cases without missing the real
 * background uses.
 */
export function isBackgroundCommand(cmd: string): boolean {
  if (!cmd) return false;
  const lower = cmd.toLowerCase();
  // Match a standalone `&` (background marker): NOT preceded by `&` `>` `|`,
  // NOT followed by `&`, AND followed by whitespace/EOL/`;`/`#`/backtick/quote.
  // Catches `cmd &`, `cmd & cmd`, `bash -c 'cmd &'`, etc. while excluding
  // `&&`, `2>&1`, `>&-`, `tail|& head`, etc.
  if (/(?<![&>|])&(?!&)(?=[\s;#`'"]|$)/m.test(cmd)) return true;
  // Always-daemon spawners.
  if (/\b(nohup|disown|setsid)\b/.test(lower)) return true;
  // Well-known dev-server entry points that block forever in fg.
  if (/\b(npm run dev|npm start|yarn dev|pnpm dev|vite|next dev|uvicorn|gunicorn|flask run|rails server)\b/.test(lower)) {
    return true;
  }
  return false;
}

interface SessionInfo {
  id: string;
  cwd?: string;
}

interface SavedSession {
  id: string;
  path: string;
  modified: string;
}

type ConnState = "idle" | "connecting" | "open" | "closing" | "closed" | "error";

/**
 * "Diff review" state for the editor pane (Mode C — Cursor-style).
 *
 * When non-null, EditorPane shows a full unified diff for one specific
 * tool call (write or edit) instead of the source code. Click "← Back to
 * file" in the editor header (or click any other file) to clear it.
 *
 * Per-operation diffs in chat tool cards remain untouched — review just
 * blows up that one card's diff into the editor for easier reading.
 */
export interface EditorReview {
  toolCallId: string;
  toolName: "write" | "edit";
  /** workspace-relative path, e.g. "calc.py". */
  path: string;
  /** Full unified-diff string ready for diff2html. */
  unifiedDiff: string;
  added: number;
  removed: number;
  status: ToolCall["status"];
}

/** A file the agent is currently writing/editing OR a file the user clicked open. */
export interface CurrentFile {
  /** "live" = streaming from a tool call; "static" = clicked from file tree. */
  source: "live" | "static";
  /** Set when source==="live"; identifies the originating ToolCall. */
  toolCallId?: string;
  path: string;
  content: string;
  /** "streaming" while args are arriving; "writing" during execute; "done"/"error" after; "loaded" for static. */
  status: "streaming" | "writing" | "done" | "error" | "loaded" | "loading";
  /** Did this write create a new file? Inferred from result text. */
  isNew?: boolean;
  /** Final result text from pi (e.g. "Successfully wrote 14 bytes …"). */
  resultText?: string;
  /** True if backend reported the file was binary or too big to display. */
  binary?: boolean;
  /** Backend's reason for not showing content (binary / too large). */
  reason?: string;
  /** Renderer hint from the backend: text/image/pdf/svg/audio/video/binary. */
  kind?: "text" | "image" | "pdf" | "svg" | "audio" | "video" | "binary";
}

export const useSessionStore = defineStore("session", () => {
  const router = createRouterState();
  const messages = ref<ChatMessage[]>([]);
  const session = ref<SessionInfo | null>(null);
  const connState = ref<ConnState>("idle");
  const isStreaming = ref(false);
  const lastError = ref<string | null>(null);
  const savedSessions = ref<SavedSession[]>([]);

  /**
   * Editor pane state. `null` = empty pane. Otherwise reactive — pushed
   * to from `syncEditorFromWriteCall()` on every WS message OR set by
   * `openFile()` when the user clicks a file in the tree.
   */
  const currentFile = ref<CurrentFile | null>(null);

  /** Flat workspace listing (sorted by path). The tree pane builds its
   *  hierarchy from this; we keep flat to make fs_change diffs trivial. */
  const fileEntries = ref<FileEntry[]>([]);

  /**
   * Editor "review mode" — set by enterReviewMode(), cleared by
   * exitReviewMode() or any explicit file-open action. When non-null the
   * EditorPane renders a full diff instead of the source.
   */
  const editorReview = ref<EditorReview | null>(null);

  /**
   * Terminal pane state. `expanded` controls the bottom strip's open/closed
   * state; `focusedToolCallId` is set when a bash card's "Open in Terminal"
   * is clicked, so the pane scrolls to and highlights that one. Cleared on
   * next user click in the pane.
   *
   * `height` and `wrap` persist across reloads so the user's terminal layout
   * preference sticks (same UX as VS Code's panel size memory).
   */
  const terminalExpanded = ref(false);
  const terminalFocusedToolCallId = ref<string | null>(null);
  /** ID of the bg process the terminal sidebar should auto-select.
   *  Set when a new bg process starts (so the user instantly sees its
   *  streaming output) or when the user clicks "open" on a process tool
   *  card in chat. */
  const terminalFocusedBgId = ref<string | null>(null);
  const terminalHeight = ref<number>(_loadNum("pi.term.height", 320, 120, 1200));
  const terminalWrap = ref<boolean>(_loadBool("pi.term.wrap", false));

  /** All bash tool calls across the chat, in chronological order. */
  const bashCalls = computed<ToolCall[]>(() => {
    const out: ToolCall[] = [];
    for (const m of messages.value) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) {
        if (tc.name === "bash") out.push(tc);
      }
    }
    return out;
  });

  /**
   * All `process` (from @aliou/pi-processes extension) tool calls. Used for
   * the chat tool-card render path; the actual *live* bg state comes from
   * `bgProcesses` below, which is driven by backend WS events instead.
   */
  const processCalls = computed<ToolCall[]>(() => {
    const out: ToolCall[] = [];
    for (const m of messages.value) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) {
        if (tc.name === "process") out.push(tc);
      }
    }
    return out;
  });

  /**
   * One bg process the user can see. Source of truth = backend's
   * BackgroundProcessRegistry, pushed to us via `bg_started` / `bg_output` /
   * `bg_ended` WS events. We never depend on LLM round-trips for this.
   */
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
    /** "running" | "exited" | "killed" | "terminating" | "terminate_timeout" */
    status: string;
    /**
     * Raw concatenated output buffer (stdout + stderr interleaved as they
     * arrive). Capped at ~256 KB so the page doesn't grow unbounded.
     */
    output: string;
  }

  /** id → live process record. */
  const bgProcesses = ref<Record<string, BgProcess>>({});

  const BG_OUTPUT_MAX_BYTES = 256 * 1024;

  function _appendBgOutput(rec: BgProcess, chunk: string): void {
    let next = rec.output + chunk;
    if (next.length > BG_OUTPUT_MAX_BYTES) {
      // Drop the oldest half — keeps the most recent activity visible without
      // unbounded memory growth on chatty daemons.
      next = next.slice(next.length - Math.floor(BG_OUTPUT_MAX_BYTES * 0.75));
    }
    rec.output = next;
  }

  function _ingestBgEvent(evt: RpcEvent & Record<string, unknown>): boolean {
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
      // Auto-open the terminal pane when a NEW background process starts.
      // Bash commands stay in chat (user clicks the bash card to open).
      // Background processes are long-running side-effects the user
      // probably wants to see streaming live.
      terminalExpanded.value = true;
      terminalFocusedBgId.value = id;
      return true;
    }
    if (t === "bg_output") {
      const id = String(evt.id ?? "");
      const chunk = String(evt.chunk ?? "");
      const rec = bgProcesses.value[id];
      if (!rec || !chunk) return true;
      _appendBgOutput(rec, chunk);
      // Trigger reactivity — we mutate the buffer in place but Vue won't see
      // it on its own since the chunk is just a string.
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

  /** All bg processes, ordered: still-running first, then ended (oldest → newest). */
  const backgroundProcesses = computed<BgProcess[]>(() =>
    Object.values(bgProcesses.value).sort((a, b) => {
      const aLive = a.status === "running";
      const bLive = b.status === "running";
      if (aLive !== bLive) return aLive ? -1 : 1;
      return a.startedAt - b.startedAt;
    }),
  );

  const activeBackgroundCount = computed(
    () => backgroundProcesses.value.filter((p) => p.status === "running").length,
  );

  /**
   * Unified "terminal" feed for the bottom panel: every bash call + every
   * background-shell session, in a single chronological list. The terminal
   * pane uses this to render a single sidebar (no more "bash here, bg over
   * there in a separate strip" split). Each entry carries enough context
   * to render itself in the main pane without further lookup.
   */
  interface BashTerminal {
    kind: "bash";
    id: string;
    label: string;
    /** ms-since-epoch — for chronological sort. */
    sortKey: number;
    /** The originating bash tool call. */
    call: ToolCall;
  }
  interface BgTerminal {
    kind: "bg";
    /** entry id = `bg:<process id>`. */
    id: string;
    label: string;
    sortKey: number;
    /** Live record from BackgroundProcessRegistry (via WS bg_* events). */
    process: BgProcess;
  }
  interface PtyTerminalEntry {
    kind: "pty";
    /** entry id = `pty:<term id>`. */
    id: string;
    label: string;
    sortKey: number;
    /** Live PTY record from /api/terminals. */
    pty: PtyTerminal;
  }
  type TerminalEntry = BashTerminal | BgTerminal | PtyTerminalEntry;

  /** Per-session set of bash tool-call IDs the user has hidden from the
   *  terminal sidebar via the × delete button. The chat card stays put;
   *  only the entry is removed from the bottom panel. */
  const hiddenBashIds = ref<Set<string>>(new Set());

  /** VS-Code-style tab label derived from the command. We grab the first
   *  meaningful "word" (skip env-vars and `bash -c "..."` wrappers) and
   *  truncate to ~28 chars. Falls back to "bash" if we can't find one. */
  function labelForBashCommand(cmd: string): string {
    if (!cmd) return "bash";
    let s = cmd.trim();
    // Strip `bash -c '...'` and similar wrappers — show the inner command.
    const wrapper = /^(?:bash|sh|zsh|env(?:\s+\S+=\S+)*)\s+(?:-\w+\s+)*['"]?(.+?)['"]?$/;
    const m = wrapper.exec(s);
    if (m) s = m[1]!.trim();
    // Take first 60 chars of the FIRST line so multi-line heredocs etc.
    // don't dominate the label.
    const firstLine = s.split("\n")[0]!.trim();
    const max = 32;
    return firstLine.length > max ? firstLine.slice(0, max - 1) + "…" : firstLine;
  }

  function removeBashCall(toolCallId: string): void {
    const next = new Set(hiddenBashIds.value);
    next.add(toolCallId);
    hiddenBashIds.value = next;
  }

  const terminalEntries = computed<TerminalEntry[]>(() => {
    const entries: TerminalEntry[] = [];
    const hidden = hiddenBashIds.value;

    // Bash — one entry per call (skip user-deleted ones).
    for (const m of messages.value) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) {
        if (tc.name !== "bash") continue;
        if (hidden.has(tc.id)) continue;
        const args = tc.args as { command?: unknown } | undefined;
        const cmd = typeof args?.command === "string" ? args.command : "";
        entries.push({
          kind: "bash",
          id: `bash:${tc.id}`,
          label: labelForBashCommand(cmd),
          sortKey: tc.startedAt ?? 0,
          call: tc,
        });
      }
    }

    // Bg — one entry per backend-tracked process (live, file-tailed).
    for (const proc of backgroundProcesses.value) {
      entries.push({
        kind: "bg",
        id: `bg:${proc.id}`,
        label: proc.name || proc.id,
        sortKey: proc.startedAt,
        process: proc,
      });
    }

    // User PTY terminals (xterm.js sessions) — one entry per backend
    // PTY. Always sort below bash/bg by adding a large constant to
    // sortKey so they live at the bottom of the sidebar.
    for (const t of userTerminals.value) {
      const shellName = t.shell.split("/").pop() ?? t.shell;
      entries.push({
        kind: "pty",
        id: `pty:${t.id}`,
        label: shellName,
        sortKey: t.startedAt + 1e15,
        pty: t,
      });
    }

    entries.sort((a, b) => a.sortKey - b.sortKey);
    return entries;
  });

  let ws: WebSocket | null = null;

  const totals = computed(() => {
    let input = 0;
    let output = 0;
    let cacheRead = 0;
    let cacheWrite = 0;
    let cost = 0;
    for (const m of messages.value) {
      if (m.kind !== "assistant" || !m.usage) continue;
      input += m.usage.input;
      output += m.usage.output;
      cacheRead += m.usage.cacheRead;
      cacheWrite += m.usage.cacheWrite;
      cost += m.usage.cost;
    }
    return { input, output, cacheRead, cacheWrite, cost };
  });

  // ── REST helpers ────────────────────────────────────────────────────────
  async function refreshSavedSessions(): Promise<void> {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { sessions: SavedSession[] };
      savedSessions.value = data.sessions;
    } catch (exc) {
      lastError.value = `Failed to list sessions: ${(exc as Error).message}`;
    }
  }

  async function newSessionId(): Promise<string> {
    const res = await fetch("/api/sessions", { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as { id: string };
    return data.id;
  }

  // ── Workspace files ─────────────────────────────────────────────────────
  async function refreshFileTree(): Promise<void> {
    try {
      const res = await fetch("/api/files");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { items: FileEntry[] };
      fileEntries.value = data.items;
    } catch (exc) {
      console.warn("[files] tree refresh failed", exc);
    }
  }

  // ── Tree UI state (rename / new-file / new-folder / collapse-all) ──────
  /**
   * Holds transient UI flags that the FileTreePane and TreeNodeRow share.
   * - renamingPath: when set, the matching node renders an inline <input>.
   * - creatingUnderPath/Kind: when set, that folder shows an inline new-file
   *   or new-folder slot under it.
   * - expandAllNonce/collapseAllNonce: nonces (incremented on each toolbar
   *   click) that every TreeNodeRow watches to expand/collapse globally.
   */
  const treeUiState = ref<{
    renamingPath: string | null;
    creatingUnderPath: string | null;
    creatingKind: "file" | "folder" | null;
    expandAllNonce: number;
    collapseAllNonce: number;
  }>({
    renamingPath: null,
    creatingUnderPath: null,
    creatingKind: null,
    expandAllNonce: 0,
    collapseAllNonce: 0,
  });

  function startRename(path: string): void {
    treeUiState.value = {
      ...treeUiState.value,
      renamingPath: path,
      creatingUnderPath: null,
      creatingKind: null,
    };
  }
  function cancelRename(): void {
    if (treeUiState.value.renamingPath !== null) {
      treeUiState.value = { ...treeUiState.value, renamingPath: null };
    }
  }
  function startCreate(parentPath: string, kind: "file" | "folder"): void {
    treeUiState.value = {
      ...treeUiState.value,
      creatingUnderPath: parentPath,
      creatingKind: kind,
      renamingPath: null,
    };
  }
  function cancelCreate(): void {
    if (treeUiState.value.creatingUnderPath !== null) {
      treeUiState.value = {
        ...treeUiState.value,
        creatingUnderPath: null,
        creatingKind: null,
      };
    }
  }
  function expandAll(): void {
    treeUiState.value = {
      ...treeUiState.value,
      expandAllNonce: treeUiState.value.expandAllNonce + 1,
    };
  }
  function collapseAll(): void {
    treeUiState.value = {
      ...treeUiState.value,
      collapseAllNonce: treeUiState.value.collapseAllNonce + 1,
    };
  }

  // ── Toast notifications (replaces window.alert blocking dialogs) ───────
  /**
   * Lightweight non-blocking notification system. The Toast.vue component
   * subscribes to `toasts` and renders the stack at bottom-right; entries
   * auto-dismiss after `ttl` ms (default 4s) or when the user clicks ×.
   */
  interface ToastEntry {
    id: string;
    message: string;
    kind: "info" | "success" | "error";
  }
  const toasts = ref<ToastEntry[]>([]);

  function toast(opts: {
    message: string;
    kind?: ToastEntry["kind"];
    ttl?: number;
  }): void {
    const id = `t_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const entry: ToastEntry = {
      id,
      message: opts.message,
      kind: opts.kind ?? "info",
    };
    toasts.value.push(entry);
    const ttl = opts.ttl ?? (entry.kind === "error" ? 6000 : 4000);
    window.setTimeout(() => dismissToast(id), ttl);
  }
  function dismissToast(id: string): void {
    const idx = toasts.value.findIndex((t) => t.id === id);
    if (idx >= 0) toasts.value.splice(idx, 1);
  }

  /**
   * Helper: format a thrown value into a readable error string and toast it.
   * Mirrors what the old `alert()` calls did, minus the page-blocking modal.
   */
  function toastError(prefix: string, exc: unknown): void {
    const msg = exc instanceof Error ? exc.message : String(exc);
    toast({ message: `${prefix}: ${msg}`, kind: "error" });
  }

  // ── File-system mutations (POST /api/fs/*) ─────────────────────────────
  /** Convert a workspace-relative path to backend form. The backend
   *  expects paths relative to the workspace root (no leading slash). */
  function _wsRel(path: string): string {
    return path.replace(/^\/+/, "").trim();
  }

  async function createFile(workspacePath: string, content = ""): Promise<void> {
    const body = JSON.stringify({ path: _wsRel(workspacePath), content });
    try {
      const res = await fetch("/api/fs/file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      cancelCreate();
      await refreshFileTree();
      // Auto-open the new file so the user can start typing immediately.
      void openFile(workspacePath);
    } catch (exc) {
      console.error("[fs] createFile failed", exc);
      toastError("Could not create file", exc);
    }
  }

  async function createFolder(workspacePath: string): Promise<void> {
    try {
      const res = await fetch("/api/fs/folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: _wsRel(workspacePath) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      cancelCreate();
      await refreshFileTree();
    } catch (exc) {
      console.error("[fs] createFolder failed", exc);
      toastError("Could not create folder", exc);
    }
  }

  async function deletePath(workspacePath: string): Promise<void> {
    try {
      const res = await fetch(`/api/fs/path?path=${encodeURIComponent(_wsRel(workspacePath))}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      // If the open file just got nuked, drop it from the editor pane.
      if (currentFile.value?.path === workspacePath) {
        currentFile.value = null;
      }
      await refreshFileTree();
    } catch (exc) {
      console.error("[fs] delete failed", exc);
      toastError("Could not delete", exc);
    }
  }

  /** Rename keeps the directory; `newName` is the new last segment only. */
  async function renamePath(workspacePath: string, newName: string): Promise<void> {
    const segs = workspacePath.split("/").filter(Boolean);
    if (segs.length === 0) return;
    segs[segs.length - 1] = newName;
    const newPath = segs.join("/");
    if (newPath === workspacePath) {
      cancelRename();
      return;
    }
    try {
      const res = await fetch("/api/fs/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: _wsRel(workspacePath), to: _wsRel(newPath) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      cancelRename();
      await refreshFileTree();
      if (currentFile.value?.path === workspacePath) {
        void openFile(newPath);
      }
    } catch (exc) {
      console.error("[fs] rename failed", exc);
      toastError("Could not rename", exc);
    }
  }

  // ── File-tree clipboard (cut/copy/paste) ────────────────────────
  /**
   * Workspace clipboard. Holds the path the user just Cut/Copied
   * from the file tree. Pasting then either copies or moves it into
   * the target folder. Mirrors macOS Finder behaviour: Cmd+C / Cmd+X
   * / Cmd+V on the focused tree row.
   */
  interface FsClipboard {
    op: "copy" | "cut";
    path: string;
    isDir: boolean;
  }
  const fsClipboard = ref<FsClipboard | null>(null);

  function clipboardCopy(workspacePath: string, isDir: boolean): void {
    fsClipboard.value = { op: "copy", path: workspacePath, isDir };
  }
  function clipboardCut(workspacePath: string, isDir: boolean): void {
    fsClipboard.value = { op: "cut", path: workspacePath, isDir };
  }
  function clipboardClear(): void {
    fsClipboard.value = null;
  }

  /**
   * Paste the clipboard entry into `targetDir` (a workspace-relative
   * directory; pass "" for the workspace root). Copy → /api/fs/copy,
   * Cut → /api/fs/move. The backend auto-disambiguates name collisions
   * (Finder-style "(copy)", "(copy 2)" suffix).
   */
  async function clipboardPaste(targetDir: string): Promise<void> {
    const c = fsClipboard.value;
    if (!c) return;
    const endpoint = c.op === "cut" ? "/api/fs/move" : "/api/fs/copy";
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: _wsRel(c.path), to: _wsRel(targetDir) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      // Cut consumes the clipboard; copy keeps it so user can paste
      // multiple times (Finder behaviour).
      if (c.op === "cut") fsClipboard.value = null;
      await refreshFileTree();
    } catch (exc) {
      console.error("[fs] paste failed", exc);
      toastError("Could not paste", exc);
    }
  }

  /**
   * Quick "Duplicate" — copies a file/folder next to itself with a
   * "(copy)" suffix. No clipboard interaction. Matches Finder Cmd+D.
   */
  async function duplicatePath(workspacePath: string): Promise<void> {
    try {
      const res = await fetch("/api/fs/copy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: _wsRel(workspacePath) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      await refreshFileTree();
    } catch (exc) {
      console.error("[fs] duplicate failed", exc);
      toastError("Could not duplicate", exc);
    }
  }

  /** Close whatever file is open in the editor (no FS side-effect).
   *  Routes through closeTab() so dirty-state confirmation kicks in. */
  function closeCurrentFile(): void {
    const p = currentFile.value?.path;
    if (p) {
      void closeTab(p);
    } else {
      currentFile.value = null;
      activeTabPath.value = null;
    }
  }

  // ── Interactive PTY terminals (xterm.js sessions) ─────────────────
  /**
   * A live interactive shell session running on the backend. Distinct
   * from `bashCalls` (one-shot agent commands) and `bgProcesses`
   * (long-running background tasks). The user types into these
   * directly via xterm.js.
   */
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
  interface ShellProfile {
    id: string;
    label: string;
    path: string;
    isDefault: string; // "true" | "false"
  }

  const userTerminals = ref<PtyTerminal[]>([]);
  const activeUserTerminalId = ref<string | null>(null);
  const shellProfiles = ref<ShellProfile[]>([]);

  async function loadShellProfiles(): Promise<void> {
    try {
      const res = await fetch("/api/terminals/profiles");
      if (!res.ok) return;
      const data = await res.json();
      if (Array.isArray(data?.profiles)) shellProfiles.value = data.profiles;
    } catch {
      /* silent */
    }
  }

  async function refreshUserTerminals(): Promise<void> {
    try {
      const res = await fetch("/api/terminals");
      if (!res.ok) return;
      const data = await res.json();
      if (Array.isArray(data?.terminals)) {
        userTerminals.value = data.terminals as PtyTerminal[];
      }
    } catch {
      /* silent */
    }
  }

  async function createUserTerminal(shell?: string): Promise<PtyTerminal | null> {
    try {
      const res = await fetch("/api/terminals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ shell: shell ?? "default" }),
      });
      if (!res.ok) return null;
      const term = (await res.json()) as PtyTerminal;
      userTerminals.value = [...userTerminals.value, term];
      activeUserTerminalId.value = term.id;
      // Also surface the terminal pane.
      terminalExpanded.value = true;
      return term;
    } catch {
      return null;
    }
  }

  async function killUserTerminal(id: string): Promise<void> {
    try {
      await fetch(`/api/terminals/${encodeURIComponent(id)}`, { method: "DELETE" });
    } catch {
      /* swallow */
    }
    userTerminals.value = userTerminals.value.filter((t) => t.id !== id);
    if (activeUserTerminalId.value === id) {
      activeUserTerminalId.value = userTerminals.value[0]?.id ?? null;
    }
  }

  function selectUserTerminal(id: string): void {
    activeUserTerminalId.value = id;
    terminalExpanded.value = true;
  }

  // ── Multi-tab editor ──────────────────────────────────────────────
  /**
   * An open editor tab. `kind` mirrors the backend's classification so the
   * tab strip can show the right icon without a re-fetch. `dirty` is
   * synced from CodeEditor's update:dirty events (see EditorPane).
   */
  interface OpenTab {
    path: string;
    kind: NonNullable<CurrentFile["kind"]>;
    dirty: boolean;
  }

  const TAB_LS_OPEN = "ui.tabs.open";
  const TAB_LS_ACTIVE = "ui.tabs.active";

  function _loadTabs(): { open: OpenTab[]; active: string | null } {
    if (typeof window === "undefined") return { open: [], active: null };
    try {
      const raw = window.localStorage.getItem(TAB_LS_OPEN);
      const active = window.localStorage.getItem(TAB_LS_ACTIVE);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          return {
            open: parsed.filter(
              (t): t is OpenTab =>
                t && typeof t.path === "string" && typeof t.kind === "string",
            ),
            active: typeof active === "string" ? active : null,
          };
        }
      }
    } catch {
      /* ignore */
    }
    return { open: [], active: null };
  }

  function _saveTabs(): void {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(TAB_LS_OPEN, JSON.stringify(openTabs.value));
      window.localStorage.setItem(TAB_LS_ACTIVE, activeTabPath.value ?? "");
    } catch {
      /* ignore */
    }
  }

  const _initial = _loadTabs();
  const openTabs = ref<OpenTab[]>(_initial.open);
  const activeTabPath = ref<string | null>(_initial.active);

  /** Add a tab if not present, mark it active. Caller is responsible for
   *  the actual file-load (openFile() does that). */
  function _ensureTab(path: string, kind: OpenTab["kind"]): void {
    const existing = openTabs.value.find((t) => t.path === path);
    if (existing) {
      existing.kind = kind;
    } else {
      openTabs.value = [...openTabs.value, { path, kind, dirty: false }];
    }
    activeTabPath.value = path;
    _saveTabs();
  }

  /** Update dirty flag for a tab (called from EditorPane on @update:dirty). */
  function setTabDirty(path: string, dirty: boolean): void {
    const t = openTabs.value.find((x) => x.path === path);
    if (!t || t.dirty === dirty) return;
    t.dirty = dirty;
    _saveTabs();
  }

  /** Close one tab. If `path` matches the active tab, switch to the
   *  neighbour (left first, then right). Returns false if cancelled
   *  due to unsaved changes. */
  async function closeTab(path: string): Promise<boolean> {
    const tab = openTabs.value.find((t) => t.path === path);
    if (!tab) return true;
    if (tab.dirty) {
      const ok = await confirm({
        title: "Discard unsaved changes?",
        description: `"${path}" has unsaved edits. They will be lost.`,
        confirmLabel: "Discard & close",
        cancelLabel: "Keep open",
        variant: "destructive",
      });
      if (!ok) return false;
    }
    const idx = openTabs.value.findIndex((t) => t.path === path);
    openTabs.value = openTabs.value.filter((t) => t.path !== path);
    if (activeTabPath.value === path) {
      const next = openTabs.value[idx - 1] ?? openTabs.value[idx] ?? null;
      if (next) {
        await openFile(next.path);
      } else {
        activeTabPath.value = null;
        currentFile.value = null;
      }
    }
    _saveTabs();
    return true;
  }

  async function closeOtherTabs(keepPath: string): Promise<void> {
    const others = openTabs.value.filter((t) => t.path !== keepPath);
    for (const t of others) {
      const ok = await closeTab(t.path);
      if (!ok) return;
    }
  }

  async function closeAllTabs(): Promise<void> {
    const all = [...openTabs.value];
    for (const t of all) {
      const ok = await closeTab(t.path);
      if (!ok) return;
    }
  }

  // ── Global confirm modal ───────────────────────────────────────────
  /** Holds a pending confirm dialog spec. `null` when no dialog is open. */
  interface ConfirmSpec {
    title: string;
    description?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    variant?: "default" | "destructive";
  }
  const confirmDialog = ref<ConfirmSpec | null>(null);
  let confirmResolver: ((value: boolean) => void) | null = null;

  /** Open a styled confirm dialog. Returns a Promise that resolves to
   *  true on confirm, false on cancel/Esc/backdrop click. */
  function confirm(spec: ConfirmSpec): Promise<boolean> {
    // If somehow a previous dialog is still pending, resolve it as cancel.
    if (confirmResolver) confirmResolver(false);
    confirmDialog.value = spec;
    return new Promise<boolean>((resolve) => {
      confirmResolver = resolve;
    });
  }
  function resolveConfirm(value: boolean): void {
    if (confirmResolver) {
      confirmResolver(value);
      confirmResolver = null;
    }
    confirmDialog.value = null;
  }

  /** Save a file's content (overwrite). Used by the editor's Cmd-S. */
  async function saveFile(workspacePath: string, content: string): Promise<void> {
    try {
      const res = await fetch("/api/fs/file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: _wsRel(workspacePath), content, overwrite: true }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    } catch (exc) {
      console.error("[fs] save failed", exc);
      throw exc;
    }
  }

  /**
   * Apply an `fs_change` event to the local file list. We patch in place
   * for speed and only refetch on schema-breaking events (rename/move).
   * Worst case the local mirror gets stale; the next created/deleted event
   * forces convergence. If a refetch is ever needed, call refreshFileTree().
   */
  function applyFsChange(events: Array<{ kind: string; path: string; is_dir: boolean; src?: string }>): void {
    if (!events.length) return;
    let needFullReload = false;
    const idx = new Map(fileEntries.value.map((e) => [e.path, e]));
    for (const ev of events) {
      switch (ev.kind) {
        case "deleted":
          idx.delete(ev.path);
          break;
        case "created":
          if (!idx.has(ev.path)) {
            idx.set(ev.path, {
              path: ev.path,
              is_dir: ev.is_dir,
              size: 0,
              mtime: Date.now() / 1000,
            });
          }
          break;
        case "modified": {
          const e = idx.get(ev.path);
          if (e) e.mtime = Date.now() / 1000;
          else
            idx.set(ev.path, {
              path: ev.path,
              is_dir: ev.is_dir,
              size: 0,
              mtime: Date.now() / 1000,
            });
          break;
        }
        case "moved":
          // Renames cascade to children too — just refetch.
          needFullReload = true;
          break;
      }
    }
    if (needFullReload) {
      void refreshFileTree();
      return;
    }
    fileEntries.value = Array.from(idx.values()).sort((a, b) => a.path.localeCompare(b.path));

    // If the open file got touched, keep the editor pane in sync:
    //   - "static" view (user opened from tree) → re-fetch on any modify/create.
    //   - "live"   view (was streamed from a write) → re-fetch ONLY if the
    //     write itself has finished, otherwise we'd fight the stream. This
    //     covers the case where the agent first WRITES a file, then EDITS it
    //     in a later turn while the user is still looking at it.
    //   - any source → null out the editor if the file was deleted.
    const cf = currentFile.value;
    if (!cf) return;
    const touched = events.find((ev) => ev.path === cf.path);
    if (!touched) return;
    if (touched.kind === "deleted") {
      currentFile.value = null;
      return;
    }
    const isFinishedLive = cf.source === "live" && (cf.status === "done" || cf.status === "error");
    if (cf.source === "static" || isFinishedLive) {
      void openFile(cf.path);
    }
  }

  /**
   * Normalize a path to workspace-relative form. The agent uses paths
   * relative to pi's CWD (= PROJECT_ROOT), so it writes "workspace/foo.py".
   * Our backend's WORKSPACE_ROOT is PROJECT_ROOT/workspace, so it expects
   * "foo.py". File-tree entries already come back workspace-relative.
   * Strip a single leading "workspace/" so both shapes converge.
   */
  function normalizeWorkspacePath(p: string): string {
    if (p.startsWith("workspace/")) return p.slice("workspace/".length);
    if (p === "workspace") return "";
    return p;
  }

  /** User clicked a file in the tree (or in a tool card). Load + show in editor.
   *  Always exits review mode — file-open is an explicit Mode-A intent. */
  async function openFile(rawPath: string): Promise<void> {
    editorReview.value = null;
    const path = normalizeWorkspacePath(rawPath);
    currentFile.value = {
      source: "static",
      path,
      content: "",
      status: "loading",
    };
    try {
      const res = await fetch(`/api/files/content?path=${encodeURIComponent(path)}`);
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        currentFile.value = {
          source: "static",
          path,
          content: "",
          status: "error",
          reason: typeof detail.detail === "string" ? detail.detail : `HTTP ${res.status}`,
        };
        return;
      }
      const data = (await res.json()) as {
        path: string;
        content: string;
        binary: boolean;
        truncated: boolean;
        size: number;
        reason?: string;
        kind?: CurrentFile["kind"];
      };
      currentFile.value = {
        source: "static",
        path: data.path,
        content: data.content,
        status: "loaded",
        binary: data.binary,
        reason: data.reason,
        kind: data.kind ?? "text",
      };
      _ensureTab(data.path, data.kind ?? "text");
    } catch (exc) {
      currentFile.value = {
        source: "static",
        path,
        content: "",
        status: "error",
        reason: (exc as Error).message,
      };
    }
  }

  // ── Editor state derivation ─────────────────────────────────────────────

  /**
   * Snapshot the latest write tool call into currentFile. Runs on EVERY ws
   * message so streaming args propagate live. Cheap: it just walks the last
   * assistant's toolCalls (typically a handful) and copies fields.
   *
   * Why not Vue's `watch()`: trackedWriteCall is a plain JS variable, not a
   * Vue ref, so watch() never knows to re-run when we reassign it. Direct
   * push from the WS handler is simpler and avoids that whole footgun.
   */
  function syncEditorFromWriteCall(): void {
    const last = router.messages[router.messages.length - 1];
    if (!last || last.kind !== "assistant") return;
    let latest: ToolCall | null = null;
    for (let i = last.toolCalls.length - 1; i >= 0; i--) {
      if (last.toolCalls[i].name === "write") {
        latest = last.toolCalls[i];
        break;
      }
    }
    if (!latest) return;

    const args = latest.args as { path?: unknown; content?: unknown } | undefined;
    const path = typeof args?.path === "string" ? normalizeWorkspacePath(args.path) : "";
    const content = typeof args?.content === "string" ? args.content : "";
    const status: CurrentFile["status"] =
      latest.status === "running"
        ? "writing"
        : latest.status === "success"
        ? "done"
        : latest.status === "error"
        ? "error"
        : "streaming";

    const cur = currentFile.value;
    // Don't steal focus from a "static" view the user explicitly opened
    // unless the agent is writing to that same file.
    if (cur && cur.source === "static" && cur.path !== path) {
      // Honor user's selection — track silently in the background. Newer
      // write calls will refocus only if user is in live view OR clicks the
      // chat tool card.
      return;
    }
    if (!cur || cur.toolCallId !== latest.id) {
      currentFile.value = {
        source: "live",
        toolCallId: latest.id,
        path,
        content,
        status,
        resultText: latest.result?.text,
        isNew: latest.result
          ? !(latest.result.text ?? "").toLowerCase().includes("overwr")
          : undefined,
      };
      return;
    }

    if (path) cur.path = path;
    cur.content = content;
    cur.status = status;
    if (latest.result) {
      cur.resultText = latest.result.text;
      cur.isNew = !(latest.result.text ?? "").toLowerCase().includes("overwr");
    }
  }

  // ── WS lifecycle ────────────────────────────────────────────────────────
  function connect(sessionId: string): void {
    if (ws) {
      ws.close();
      ws = null;
    }
    router.messages = [];
    router.toolCallIndex.clear();
    messages.value = [];
    session.value = { id: sessionId };
    isStreaming.value = false;
    lastError.value = null;
    currentFile.value = null;
    void refreshFileTree();

    connState.value = "connecting";
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws/sessions/${sessionId}`);

    ws.onopen = () => {
      connState.value = "open";
    };
    ws.onerror = () => {
      connState.value = "error";
      lastError.value = "WebSocket error (see backend logs)";
    };
    ws.onclose = () => {
      connState.value = "closed";
      isStreaming.value = false;
    };
    ws.onmessage = (e: MessageEvent<string>) => {
      let evt: RpcEvent;
      try {
        evt = JSON.parse(e.data);
      } catch {
        return;
      }

      if (DEBUG_EVENTS) {
        const sub = (evt as any).assistantMessageEvent?.type;
        // eslint-disable-next-line no-console
        console.debug("[rpc]", evt.type, sub ? `(${sub})` : "", evt);
      }

      if (evt.type === "agent_start" || evt.type === "turn_start") {
        isStreaming.value = true;
      } else if (evt.type === "agent_end") {
        isStreaming.value = false;
      }

      if (evt.type === "session" && session.value) {
        session.value = { id: session.value.id, cwd: String((evt as any).cwd ?? "") };
      }

      // Workspace file events come from the backend FS watcher, NOT pi.
      // Keep them out of the chat reducer.
      if (evt.type === "fs_change") {
        applyFsChange(((evt as any).events ?? []) as Array<{
          kind: string;
          path: string;
          is_dir: boolean;
          src?: string;
        }>);
        return;
      }

      // Background-process events (from our backend registry, not pi). They
      // populate the live bg-process buffer the terminal pane streams from.
      if (
        evt.type === "bg_started" ||
        evt.type === "bg_output" ||
        evt.type === "bg_ended"
      ) {
        _ingestBgEvent(evt as RpcEvent & Record<string, unknown>);
        return;
      }

      applyEvent(router, evt);
      syncEditorFromWriteCall();
      messages.value = router.messages.slice();
    };
  }

  function disconnect(): void {
    if (!ws) return;
    connState.value = "closing";
    ws.close();
    ws = null;
  }

  function sendPrompt(text: string): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      lastError.value = "Not connected";
      return;
    }
    if (!text.trim()) return;
    const reqId = `req-${Date.now()}`;
    pushUserMessage(router, text, reqId);
    messages.value = [...router.messages];
    ws.send(JSON.stringify({ id: reqId, type: "prompt", message: text }));
    isStreaming.value = true;
  }

  function abort(): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "abort" }));
  }

  /** Manually focus a specific tool call's file in the editor (chat → editor jump).
   *  Used while a write is still streaming so the user can pin the live
   *  view to that call. Always exits review mode.
   */
  function focusToolCall(toolCallId: string): void {
    editorReview.value = null;
    for (const m of messages.value) {
      if (m.kind !== "assistant") continue;
      const tc = m.toolCalls.find((c) => c.id === toolCallId);
      if (!tc) continue;
      if (tc.name !== "write") return;
      const args = tc.args as { path?: unknown; content?: unknown } | undefined;
      currentFile.value = {
        source: "live",
        toolCallId: tc.id,
        path: typeof args?.path === "string" ? normalizeWorkspacePath(args.path) : "",
        content: typeof args?.content === "string" ? args.content : "",
        status:
          tc.status === "running"
            ? "writing"
            : tc.status === "success"
            ? "done"
            : tc.status === "error"
            ? "error"
            : "streaming",
        resultText: tc.result?.text,
      };
      return;
    }
  }

  // ── Review mode (Mode C — full diff in editor) ──────────────────────────

  /** Locate a tool call across all messages by its id. */
  function findToolCall(toolCallId: string): ToolCall | null {
    for (const m of messages.value) {
      if (m.kind !== "assistant") continue;
      const tc = m.toolCalls.find((c) => c.id === toolCallId);
      if (tc) return tc;
    }
    return null;
  }

  /**
   * Count added/removed lines in a unified-diff string. Anchored on the
   * exact +/- prefix at column 0, ignoring the leading file-header lines
   * (`+++`, `---`).
   */
  function countDiffStats(unified: string): { added: number; removed: number } {
    let added = 0;
    let removed = 0;
    for (const line of unified.split("\n")) {
      if (line.startsWith("+++") || line.startsWith("---")) continue;
      if (line.startsWith("+")) added++;
      else if (line.startsWith("-")) removed++;
    }
    return { added, removed };
  }

  /**
   * Enter review mode for a specific write/edit tool call.
   *
   * Source of truth: the backend shadow-git repo (Cline/Roo Code/Aider
   * pattern). We hit `/api/snapshots/{tool_call_id}/diff` which returns a
   * full-context unified diff resolved against the workspace state RIGHT
   * BEFORE that specific tool call ran — correct even after dozens of
   * subsequent edits to the same file.
   *
   * Fallback: if the backend has no snapshot (e.g. legacy session or the
   * call was an in-memory error), synthesize a sparse diff from the
   * tool call's own args/result so the user still sees something.
   */
  async function enterReviewMode(toolCallId: string): Promise<void> {
    const tc = findToolCall(toolCallId);
    if (!tc) return;
    if (tc.name !== "write" && tc.name !== "edit") return;

    let path = "";
    let unifiedDiff = "";
    let added = 0;
    let removed = 0;

    try {
      const res = await fetch(`/api/snapshots/${encodeURIComponent(toolCallId)}/diff`);
      if (res.ok) {
        const payload = (await res.json()) as {
          path?: string;
          unified_diff?: string;
        };
        if (typeof payload.unified_diff === "string" && payload.unified_diff.trim()) {
          unifiedDiff = payload.unified_diff;
          path = normalizeWorkspacePath(
            typeof payload.path === "string" ? payload.path : "",
          );
          const stats = countDiffStats(unifiedDiff);
          added = stats.added;
          removed = stats.removed;
        }
      }
    } catch (err) {
      console.warn(`[review] backend snapshot fetch failed for ${toolCallId}:`, err);
    }

    if (!unifiedDiff) {
      if (tc.name === "write") {
        const args = tc.args as { path?: unknown; content?: unknown } | undefined;
        const rawPath = typeof args?.path === "string" ? args.path : "";
        const content = typeof args?.content === "string" ? args.content : "";
        path = normalizeWorkspacePath(rawPath);
        if (!path || !content) return;
        unifiedDiff = writeContentToUnified(content, path);
        const lines = content.split("\n");
        added =
          lines.length > 1 && lines[lines.length - 1] === ""
            ? lines.length - 1
            : lines.length;
      } else {
        const args = tc.args as { path?: unknown } | undefined;
        const rawPath = typeof args?.path === "string" ? args.path : "";
        path = normalizeWorkspacePath(rawPath);
        const details = tc.result?.details as { diff?: unknown } | undefined;
        const piDiff = typeof details?.diff === "string" ? details.diff : "";
        if (!path || !piDiff) return;
        unifiedDiff = piDiffToUnified(piDiff, path);
        const parsed = parseDiff(piDiff);
        added = parsed.added;
        removed = parsed.removed;
      }
    }

    if (!unifiedDiff) return;

    editorReview.value = {
      toolCallId,
      toolName: tc.name as "write" | "edit",
      path,
      unifiedDiff,
      added,
      removed,
      status: tc.status,
    };
  }

  function exitReviewMode(): void {
    editorReview.value = null;
  }

  /** Bash card → "Open in Terminal Pane": expand pane and pin focus. */
  function focusTerminal(toolCallId: string): void {
    terminalFocusedToolCallId.value = toolCallId;
    terminalExpanded.value = true;
  }

  function setTerminalExpanded(value: boolean): void {
    terminalExpanded.value = value;
    if (!value) terminalFocusedToolCallId.value = null;
  }

  function clearTerminalFocus(): void {
    terminalFocusedToolCallId.value = null;
  }

  function setTerminalHeight(px: number): void {
    const clamped = Math.min(1200, Math.max(120, Math.round(px)));
    terminalHeight.value = clamped;
    _saveNum("pi.term.height", clamped);
  }

  function toggleTerminalWrap(): void {
    terminalWrap.value = !terminalWrap.value;
    _saveBool("pi.term.wrap", terminalWrap.value);
  }

  /**
   * "Re-run" a previously-executed bash command. Sends the raw command
   * back to the agent wrapped in a "run literally" prompt so the agent
   * doesn't try to "improve" it. Cheaper than rebuilding the bash tool
   * input ourselves and matches how a user would re-issue the command.
   */
  function rerunBashCommand(command: string): void {
    if (!command.trim()) return;
    // Surround in single quotes after escaping any embedded single quotes,
    // so the agent receives the command verbatim regardless of shell tricks.
    const escaped = command.replace(/'/g, "'\\''");
    sendPrompt(`Run this bash command literally, no edits or commentary: ${escaped}`);
  }

  /**
   * Background-process control via @aliou/pi-processes.
   *
   * `dispatchBackground` is the only LLM-driven helper — we have to ask the
   * agent to call `process(action: "start", ...)` once because that's the
   * only path that registers a tracker in the extension. Once it's running,
   * everything else (live output, kill) goes through our backend's
   * BackgroundProcessRegistry directly — zero LLM round-trips for tail/stop.
   */
  function dispatchBackground(command: string, name?: string, reason?: string): void {
    if (!command.trim()) return;
    const escaped = command.replace(/"/g, '\\"');
    const nameClause = name ? `, name: "${name}"` : "";
    const reasonClause = reason ? ` Reason: ${reason}.` : "";
    sendPrompt(
      `Use the process tool to start this command in the background. ` +
      `Call it with action: "start", command: "${escaped}"${nameClause}.${reasonClause} ` +
      `Do not commentate, just call the tool once.`,
    );
  }

  /**
   * Kill a bg process directly via the backend (sends SIGTERM to pid, then
   * SIGKILL after 5s). No LLM in the loop — the UI updates from the
   * `bg_ended` event the registry broadcasts.
   */
  async function killBackgroundProcess(processId: string): Promise<void> {
    try {
      const res = await fetch(
        `/api/bg/${encodeURIComponent(processId)}/kill`,
        { method: "POST" },
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(
          typeof detail.detail === "string"
            ? detail.detail
            : `Kill failed: HTTP ${res.status}`,
        );
      }
    } catch (exc) {
      lastError.value = (exc as Error).message;
    }
  }

  /**
   * Restore: rewind workspace to the state RIGHT BEFORE this tool call ran.
   * Touches every file this call (and every later call) modified. Files
   * the user manually edited (never tracked by the agent) are untouched.
   *
   * After success: refresh the file tree, re-load the editor's current
   * file (it may have changed or been deleted), and exit review mode.
   *
   * Returns the list of restored files for UI feedback.
   */
  async function restoreToolCall(toolCallId: string): Promise<string[]> {
    const res = await fetch(
      `/api/snapshots/${encodeURIComponent(toolCallId)}/restore`,
      { method: "POST" },
    );
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(
        typeof detail.detail === "string"
          ? detail.detail
          : `Restore failed: HTTP ${res.status}`,
      );
    }
    const data = (await res.json()) as { restored_files?: string[] };
    const files = Array.isArray(data.restored_files) ? data.restored_files : [];
    await _refreshAfterMutation(files);
    return files;
  }

  /**
   * Revert all file changes made in response to a single user prompt.
   * Equivalent to clicking "Restore" on the FIRST tool call of that turn.
   */
  async function revertTurn(userMessageId: string): Promise<string[]> {
    const res = await fetch(
      `/api/turns/${encodeURIComponent(userMessageId)}/revert`,
      { method: "POST" },
    );
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(
        typeof detail.detail === "string"
          ? detail.detail
          : `Revert failed: HTTP ${res.status}`,
      );
    }
    const data = (await res.json()) as { restored_files?: string[] };
    const files = Array.isArray(data.restored_files) ? data.restored_files : [];
    await _refreshAfterMutation(files);
    return files;
  }

  /** Common cleanup after a restore/revert mutates the workspace. */
  async function _refreshAfterMutation(files: string[]): Promise<void> {
    editorReview.value = null;
    await refreshFileTree();
    const open = currentFile.value;
    if (open && files.includes(open.path)) {
      // Re-fetch — file may have changed contents OR been deleted.
      await openFile(open.path).catch(() => {
        // openFile sets status='error' itself; nothing more to do.
      });
    }
  }

  return {
    messages,
    session,
    connState,
    isStreaming,
    lastError,
    savedSessions,
    totals,
    currentFile,
    fileEntries,
    editorReview,
    refreshSavedSessions,
    newSessionId,
    refreshFileTree,
    openFile,
    treeUiState,
    startRename,
    cancelRename,
    startCreate,
    cancelCreate,
    expandAll,
    collapseAll,
    createFile,
    createFolder,
    deletePath,
    renamePath,
    saveFile,
    closeCurrentFile,
    fsClipboard,
    clipboardCopy,
    clipboardCut,
    clipboardClear,
    clipboardPaste,
    duplicatePath,
    toasts,
    toast,
    toastError,
    dismissToast,
    confirmDialog,
    confirm,
    resolveConfirm,
    openTabs,
    activeTabPath,
    setTabDirty,
    closeTab,
    closeOtherTabs,
    closeAllTabs,
    userTerminals,
    activeUserTerminalId,
    shellProfiles,
    loadShellProfiles,
    refreshUserTerminals,
    createUserTerminal,
    killUserTerminal,
    selectUserTerminal,
    connect,
    disconnect,
    sendPrompt,
    abort,
    focusToolCall,
    enterReviewMode,
    exitReviewMode,
    restoreToolCall,
    revertTurn,
    bashCalls,
    processCalls,
    backgroundProcesses,
    activeBackgroundCount,
    terminalEntries,
    terminalExpanded,
    terminalFocusedToolCallId,
    terminalFocusedBgId,
    terminalHeight,
    terminalWrap,
    focusTerminal,
    setTerminalExpanded,
    clearTerminalFocus,
    setTerminalHeight,
    toggleTerminalWrap,
    rerunBashCommand,
    removeBashCall,
    dispatchBackground,
    killBackgroundProcess,
    normalizeWorkspacePath,
  };
});
