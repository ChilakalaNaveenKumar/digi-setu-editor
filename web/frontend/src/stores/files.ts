/**
 * Workspace files: tree mirror, current file, tabs, clipboard, tree UI.
 *
 * The "current file" model has two flavours:
 *   - source: "static"  — user clicked a file in the tree.
 *   - source: "live"    — agent is mid-write; content streams in via the
 *                          chat store's `applyLiveWrite()` callback.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import * as fsApi from "../api/files";
import type { FileEntry, FsChangeEvent } from "../api/types";

import { useUiStore } from "./ui";
import { useWorkspaceStore } from "./workspace";

export type FileKind =
  | "text"
  | "image"
  | "pdf"
  | "svg"
  | "audio"
  | "video"
  | "office"
  | "spreadsheet"
  | "word"
  | "slides"
  | "sqlite"
  | "binary";

export interface CurrentFile {
  source: "live" | "static";
  toolCallId?: string;
  path: string;
  content: string;
  status: "streaming" | "writing" | "done" | "error" | "loaded" | "loading";
  isNew?: boolean;
  resultText?: string;
  binary?: boolean;
  reason?: string;
  kind?: FileKind;
}

export interface OpenTab {
  path: string;
  kind: FileKind;
  dirty: boolean;
}

export interface TreeUiState {
  renamingPath: string | null;
  creatingUnderPath: string | null;
  creatingKind: "file" | "folder" | null;
  expandAllNonce: number;
  collapseAllNonce: number;
}

export interface FsClipboard {
  op: "copy" | "cut";
  path: string;
  isDir: boolean;
}

const TAB_LS_OPEN = "ui.tabs.open";
const TAB_LS_ACTIVE = "ui.tabs.active";

function _wsRel(path: string): string {
  return path.replace(/^\/+/, "").trim();
}

/**
 * The agent writes paths relative to pi's CWD (the workspace folder),
 * so it produces "workspace/foo.py". Our backend's user-files root is
 * `<workspace>/workspace/`, so the API layer expects "foo.py". Strip
 * a single leading "workspace/" so both shapes converge.
 */
export function normalizeWorkspacePath(p: string): string {
  if (p.startsWith("workspace/")) return p.slice("workspace/".length);
  if (p === "workspace") return "";
  return p;
}

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
            (t): t is OpenTab => t && typeof t.path === "string" && typeof t.kind === "string"
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

export const useFilesStore = defineStore("files", () => {
  const ui = useUiStore();
  const workspace = useWorkspaceStore();

  // ── core state ──────────────────────────────────────────────────────────
  const fileEntries = ref<FileEntry[]>([]);
  const currentFile = ref<CurrentFile | null>(null);

  const _initial = _loadTabs();
  const openTabs = ref<OpenTab[]>(_initial.open);
  const activeTabPath = ref<string | null>(_initial.active);

  const treeUiState = ref<TreeUiState>({
    renamingPath: null,
    creatingUnderPath: null,
    creatingKind: null,
    expandAllNonce: 0,
    collapseAllNonce: 0,
  });

  const fsClipboard = ref<FsClipboard | null>(null);

  // ── selection model ─────────────────────────────────────────────────
  // Tracks which tree nodes are highlighted for batch operations
  // (multi-drag, future Cmd+C / Cmd+X). Rendered nodes look up
  // membership via `isSelected(path)`.
  //
  // Mutated by `selectPath()` which understands three modes — same
  // contract as VS Code's tree:
  //
  //   • "single"  Plain click. Replace the selection with [path].
  //   • "toggle"  Cmd/Ctrl+Click. Add or remove `path` from selection.
  //   • "range"   Shift+Click. Select all paths between the last anchor
  //               and `path` (in the visible-flat-order the tree
  //               displays). Falls back to "single" if there's no
  //               anchor yet.
  //
  // The "range anchor" is the last path that was the click target of
  // a single or toggle action. We keep it as a ref so range-extends
  // chain naturally (Click A → Shift+Click B → Shift+Click C grows
  // the range A..C as expected).
  const selectedPaths = ref<Set<string>>(new Set());
  const _selectionAnchor = ref<string | null>(null);

  function isSelected(path: string): boolean {
    return selectedPaths.value.has(path);
  }

  function selectPath(
    path: string,
    mode: "single" | "toggle" | "range",
    visibleOrderedPaths?: string[],
  ): void {
    if (mode === "toggle") {
      const next = new Set(selectedPaths.value);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      selectedPaths.value = next;
      _selectionAnchor.value = path;
      return;
    }
    if (mode === "range") {
      const anchor = _selectionAnchor.value;
      if (!anchor || !visibleOrderedPaths || visibleOrderedPaths.length === 0) {
        selectedPaths.value = new Set([path]);
        _selectionAnchor.value = path;
        return;
      }
      const ai = visibleOrderedPaths.indexOf(anchor);
      const bi = visibleOrderedPaths.indexOf(path);
      if (ai === -1 || bi === -1) {
        selectedPaths.value = new Set([path]);
        _selectionAnchor.value = path;
        return;
      }
      const [from, to] = ai <= bi ? [ai, bi] : [bi, ai];
      selectedPaths.value = new Set(visibleOrderedPaths.slice(from, to + 1));
      // Anchor stays put on range select — VS Code behaviour. So
      // chained shift-clicks always expand from the original anchor.
      return;
    }
    // single
    selectedPaths.value = new Set([path]);
    _selectionAnchor.value = path;
  }

  function clearSelection(): void {
    selectedPaths.value = new Set();
    _selectionAnchor.value = null;
  }

  /** Move every selected path under `targetDir` using N parallel
   *  /api/.../fs/move calls. We deliberately do them in parallel —
   *  the backend uses unique_dest() so collisions auto-rename, and
   *  N synchronous round-trips for 10 selected files would feel slow.
   *
   *  Returns the list of new paths reported by the backend.
   */
  async function moveSelectedTo(targetDir: string): Promise<string[]> {
    const sources = Array.from(selectedPaths.value);
    if (sources.length === 0) return [];
    const tgt = _wsRel(targetDir);
    const wsid = _wsid();
    // Don't drop a folder into itself or its own descendant — both
    // crash the backend and leave the tree in a bad state.
    const filtered = sources.filter((src) => {
      if (src === tgt) return false;
      if (tgt.startsWith(src + "/")) return false;
      return true;
    });
    if (filtered.length === 0) return [];

    const results = await Promise.allSettled(
      filtered.map((src) =>
        fsApi.movePath(
          wsid,
          _wsRel(src),
          tgt ? `${tgt}/${src.split("/").pop()}` : src.split("/").pop()!,
        ),
      ),
    );
    clearSelection();
    void refreshTree();
    const newPaths: string[] = [];
    for (const r of results) {
      if (r.status === "fulfilled") newPaths.push(r.value.path);
      else console.warn("[files] move failed:", r.reason);
    }
    return newPaths;
  }

  // Helper: pull the active wsid or throw — every operation requires one.
  function _wsid(): string {
    const id = workspace.activeId;
    if (!id) throw new Error("no active workspace");
    return id;
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

  function _ensureTab(path: string, kind: FileKind): void {
    const existing = openTabs.value.find((t) => t.path === path);
    if (existing) {
      existing.kind = kind;
    } else {
      openTabs.value = [...openTabs.value, { path, kind, dirty: false }];
    }
    activeTabPath.value = path;
    _saveTabs();
  }

  // ── tree ────────────────────────────────────────────────────────────────
  async function refreshTree(): Promise<void> {
    if (!workspace.activeId) return;
    try {
      const data = await fsApi.listFiles(workspace.activeId);
      fileEntries.value = data.items;
    } catch (exc) {
      console.warn("[files] tree refresh failed", exc);
    }
  }

  // ── open ────────────────────────────────────────────────────────────────
  async function openFile(rawPath: string): Promise<void> {
    const path = normalizeWorkspacePath(rawPath);
    currentFile.value = { source: "static", path, content: "", status: "loading" };
    try {
      const data = await fsApi.readFile(_wsid(), path);
      currentFile.value = {
        source: "static",
        path: data.path,
        content: data.content,
        status: "loaded",
        binary: data.binary,
        reason: data.reason,
        kind: data.kind,
      };
      _ensureTab(data.path, data.kind);
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

  // ── live write streaming (called from chat store) ──────────────────────
  /**
   * Mirror a streaming `write` tool call into `currentFile`. The chat
   * store calls this on every WS message that mutates a write tool call.
   */
  function applyLiveWrite(call: {
    id: string;
    args: { path?: unknown; content?: unknown } | undefined;
    status: "running" | "success" | "error" | "pending" | "streaming";
    result?: { text?: string };
  }): void {
    const args = call.args;
    const path = typeof args?.path === "string" ? normalizeWorkspacePath(args.path) : "";
    const content = typeof args?.content === "string" ? args.content : "";
    const status: CurrentFile["status"] =
      call.status === "running"
        ? "writing"
        : call.status === "success"
        ? "done"
        : call.status === "error"
        ? "error"
        : "streaming";

    const cur = currentFile.value;
    // Don't yank a static view the user opened unless we're editing that file.
    if (cur && cur.source === "static" && cur.path !== path) return;

    if (!cur || cur.toolCallId !== call.id) {
      currentFile.value = {
        source: "live",
        toolCallId: call.id,
        path,
        content,
        status,
        resultText: call.result?.text,
        isNew: call.result ? !(call.result.text ?? "").toLowerCase().includes("overwr") : undefined,
      };
      return;
    }
    if (path) cur.path = path;
    cur.content = content;
    cur.status = status;
    if (call.result) {
      cur.resultText = call.result.text;
      cur.isNew = !(call.result.text ?? "").toLowerCase().includes("overwr");
    }
  }

  /**
   * Manual focus from a chat tool card click. Always moves to live view
   * for the given write call.
   */
  function focusLiveWriteCall(call: {
    id: string;
    name: string;
    args: { path?: unknown; content?: unknown } | undefined;
    status: "running" | "success" | "error" | "pending" | "streaming";
    result?: { text?: string };
  }): void {
    if (call.name !== "write") return;
    const args = call.args;
    currentFile.value = {
      source: "live",
      toolCallId: call.id,
      path: typeof args?.path === "string" ? normalizeWorkspacePath(args.path) : "",
      content: typeof args?.content === "string" ? args.content : "",
      status:
        call.status === "running"
          ? "writing"
          : call.status === "success"
          ? "done"
          : call.status === "error"
          ? "error"
          : "streaming",
      resultText: call.result?.text,
    };
  }

  // ── fs_change ingestion ────────────────────────────────────────────────
  function applyFsChange(events: FsChangeEvent[]): void {
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
            idx.set(ev.path, { path: ev.path, is_dir: ev.is_dir, size: 0, mtime: Date.now() / 1000 });
          }
          break;
        case "modified": {
          const e = idx.get(ev.path);
          if (e) e.mtime = Date.now() / 1000;
          else idx.set(ev.path, { path: ev.path, is_dir: ev.is_dir, size: 0, mtime: Date.now() / 1000 });
          break;
        }
        case "moved":
          needFullReload = true;
          break;
      }
    }
    if (needFullReload) {
      void refreshTree();
      return;
    }
    fileEntries.value = Array.from(idx.values()).sort((a, b) => a.path.localeCompare(b.path));

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

  // ── mutations ──────────────────────────────────────────────────────────
  async function createFile(path: string, content = ""): Promise<void> {
    try {
      await fsApi.createFile(_wsid(), _wsRel(path), content);
      cancelCreate();
      await refreshTree();
      void openFile(path);
    } catch (exc) {
      ui.toastError("Could not create file", exc);
    }
  }

  async function createFolder(path: string): Promise<void> {
    try {
      await fsApi.createFolder(_wsid(), _wsRel(path));
      cancelCreate();
      await refreshTree();
    } catch (exc) {
      ui.toastError("Could not create folder", exc);
    }
  }

  async function deletePath(path: string): Promise<void> {
    try {
      await fsApi.deletePath(_wsid(), _wsRel(path));
      if (currentFile.value?.path === path) currentFile.value = null;
      await refreshTree();
    } catch (exc) {
      ui.toastError("Could not delete", exc);
    }
  }

  async function renamePath(path: string, newName: string): Promise<void> {
    const segs = path.split("/").filter(Boolean);
    if (segs.length === 0) return;
    segs[segs.length - 1] = newName;
    const newPath = segs.join("/");
    if (newPath === path) {
      cancelRename();
      return;
    }
    try {
      await fsApi.renamePath(_wsid(), _wsRel(path), _wsRel(newPath));
      cancelRename();
      await refreshTree();
      if (currentFile.value?.path === path) void openFile(newPath);
    } catch (exc) {
      ui.toastError("Could not rename", exc);
    }
  }

  async function saveFile(path: string, content: string): Promise<void> {
    await fsApi.writeFile(_wsid(), _wsRel(path), content, true);
  }

  // ── clipboard ──────────────────────────────────────────────────────────
  function clipboardCopy(path: string, isDir: boolean): void {
    fsClipboard.value = { op: "copy", path, isDir };
  }
  function clipboardCut(path: string, isDir: boolean): void {
    fsClipboard.value = { op: "cut", path, isDir };
  }
  function clipboardClear(): void {
    fsClipboard.value = null;
  }
  async function clipboardPaste(targetDir: string): Promise<void> {
    const c = fsClipboard.value;
    if (!c) return;
    try {
      if (c.op === "cut") {
        await fsApi.movePath(_wsid(), _wsRel(c.path), _wsRel(targetDir));
        fsClipboard.value = null;
      } else {
        await fsApi.copyPath(_wsid(), _wsRel(c.path), _wsRel(targetDir));
      }
      await refreshTree();
    } catch (exc) {
      ui.toastError("Could not paste", exc);
    }
  }
  async function duplicatePath(path: string): Promise<void> {
    try {
      await fsApi.copyPath(_wsid(), _wsRel(path));
      await refreshTree();
    } catch (exc) {
      ui.toastError("Could not duplicate", exc);
    }
  }

  // ── tree UI state ──────────────────────────────────────────────────────
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
      treeUiState.value = { ...treeUiState.value, creatingUnderPath: null, creatingKind: null };
    }
  }
  function expandAll(): void {
    treeUiState.value = { ...treeUiState.value, expandAllNonce: treeUiState.value.expandAllNonce + 1 };
  }
  function collapseAll(): void {
    treeUiState.value = { ...treeUiState.value, collapseAllNonce: treeUiState.value.collapseAllNonce + 1 };
  }

  // ── tabs ───────────────────────────────────────────────────────────────
  function setTabDirty(path: string, dirty: boolean): void {
    const t = openTabs.value.find((x) => x.path === path);
    if (!t || t.dirty === dirty) return;
    t.dirty = dirty;
    _saveTabs();
  }

  async function closeTab(path: string): Promise<boolean> {
    const tab = openTabs.value.find((t) => t.path === path);
    if (!tab) return true;
    if (tab.dirty) {
      const ok = await ui.confirm({
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

  function closeCurrentFile(): void {
    const p = currentFile.value?.path;
    if (p) {
      void closeTab(p);
    } else {
      currentFile.value = null;
      activeTabPath.value = null;
    }
  }

  // ── reset (called by chat store on connect/disconnect) ─────────────────
  /**
   * Tabs are workspace-scoped — paths from a different sandbox would 404
   * immediately. Clear in-memory + persisted state on every (re)connect;
   * the user's tab state will rebuild as they open files.
   */
  function resetForNewSession(): void {
    fileEntries.value = [];
    currentFile.value = null;
    openTabs.value = [];
    activeTabPath.value = null;
    _saveTabs();
  }

  return {
    fileEntries,
    currentFile,
    openTabs,
    activeTabPath,
    treeUiState,
    fsClipboard,
    selectedPaths,
    refreshTree,
    openFile,
    applyLiveWrite,
    focusLiveWriteCall,
    applyFsChange,
    createFile,
    createFolder,
    deletePath,
    renamePath,
    saveFile,
    setTabDirty,
    closeTab,
    closeOtherTabs,
    closeAllTabs,
    closeCurrentFile,
    clipboardCopy,
    clipboardCut,
    clipboardClear,
    clipboardPaste,
    duplicatePath,
    startRename,
    cancelRename,
    startCreate,
    cancelCreate,
    expandAll,
    collapseAll,
    resetForNewSession,
    normalizeWorkspacePath,
    selectPath,
    clearSelection,
    isSelected,
    moveSelectedTo,
  };
});
