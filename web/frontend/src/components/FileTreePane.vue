<!--
  FileTreePane — left column.

  Sections:
    Header   — back to sessions + session id + cwd.
    Toolbar  — VS Code-style action row: New File, New Folder, Refresh,
               Collapse All. All four target the "currently selected"
               folder context (or the root if nothing's selected).
    Body     — the recursive TreeNodeRow list. Right-click on any node
               opens the floating context menu rendered at the bottom
               of this component.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";
import { useSessionStore } from "../stores/session";
import { buildTree, type TreeNode } from "../lib/file-tree";
import TreeNodeRow from "./TreeNodeRow.vue";

const store = useSessionStore();
const { session, fileEntries } = storeToRefs(store);

onMounted(() => {
  void store.refreshFileTree();
});

const tree = computed(() => buildTree(fileEntries.value));

const fileCount = computed(
  () => fileEntries.value.filter((e) => !e.is_dir).length,
);

const cwdShort = computed(() => {
  const cwd = session.value?.cwd ?? "";
  if (!cwd) return "";
  const parts = cwd.split("/");
  return parts.slice(-2).join("/");
});

function back(): void {
  store.disconnect();
}

// ── Toolbar actions ────────────────────────────────────────────────────
/** Where new files/folders should land if the user hits the toolbar
 *  button. We don't track an explicit "selected folder" yet — for now
 *  use the parent of the open file, or the root. */
const toolbarTargetFolder = computed(() => {
  const cf = store.currentFile;
  if (!cf?.path) return "";
  const segs = cf.path.split("/").filter(Boolean);
  segs.pop();
  return segs.join("/");
});

function toolbarNewFile(): void {
  store.startCreate(toolbarTargetFolder.value, "file");
}
function toolbarNewFolder(): void {
  store.startCreate(toolbarTargetFolder.value, "folder");
}
function toolbarRefresh(): void {
  void store.refreshFileTree();
}
function toolbarCollapseAll(): void {
  store.collapseAll();
}

// ── Context menu (right-click on a node) ───────────────────────────────
const menu = ref<{
  open: boolean;
  x: number;
  y: number;
  node: TreeNode | null;
}>({ open: false, x: 0, y: 0, node: null });

function openContextMenu(payload: { x: number; y: number; node: TreeNode }): void {
  // Clamp menu inside the viewport so it never gets clipped.
  const menuW = 180;
  const menuH = 240;
  const x = Math.min(payload.x, window.innerWidth - menuW - 8);
  const y = Math.min(payload.y, window.innerHeight - menuH - 8);
  menu.value = { open: true, x, y, node: payload.node };
}

function closeContextMenu(): void {
  if (menu.value.open) {
    menu.value = { open: false, x: 0, y: 0, node: null };
  }
}

onMounted(() => {
  document.addEventListener("click", closeContextMenu);
  document.addEventListener("contextmenu", maybeCloseFromOutside);
  document.addEventListener("keydown", onEscClose);
});
onUnmounted(() => {
  document.removeEventListener("click", closeContextMenu);
  document.removeEventListener("contextmenu", maybeCloseFromOutside);
  document.removeEventListener("keydown", onEscClose);
});

function maybeCloseFromOutside(e: MouseEvent): void {
  // If the user right-clicks somewhere outside the tree, close. The new
  // contextmenu handler on a tree row re-opens it via openContextMenu.
  const target = e.target as HTMLElement | null;
  if (!target?.closest(".file-tree-pane")) closeContextMenu();
}

function onEscClose(e: KeyboardEvent): void {
  if (e.key === "Escape") closeContextMenu();
}

// ── Context-menu actions ───────────────────────────────────────────────
function ctxOpen(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  if (!n.isDir) void store.openFile(n.path);
}

function ctxRename(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  store.startRename(n.path);
}

async function ctxDelete(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  const label = n.isDir ? "folder" : "file";
  const ok = await store.confirm({
    title: `Delete ${label}?`,
    description:
      `"${n.path}" will be deleted from the workspace.` +
      (n.isDir ? " All contents inside will be removed too." : "") +
      " This cannot be undone.",
    confirmLabel: "Delete",
    variant: "destructive",
  });
  if (!ok) return;
  await store.deletePath(n.path);
}

async function ctxCopyPath(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  try {
    await navigator.clipboard.writeText(n.path);
  } catch {
    /* ignore */
  }
}

function ctxNewFile(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  const parent = n.isDir ? n.path : n.path.split("/").slice(0, -1).join("/");
  store.startCreate(parent, "file");
}

function ctxNewFolder(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  const parent = n.isDir ? n.path : n.path.split("/").slice(0, -1).join("/");
  store.startCreate(parent, "folder");
}

// ── Cut / Copy / Paste / Duplicate ────────────────────────────────────
const { fsClipboard } = storeToRefs(store);

function ctxCut(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  store.clipboardCut(n.path, n.isDir);
}
function ctxCopy(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  store.clipboardCopy(n.path, n.isDir);
}
async function ctxPaste(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n || !fsClipboard.value) return;
  // Paste INTO the node if it's a folder, otherwise into its parent.
  const target = n.isDir ? n.path : n.path.split("/").slice(0, -1).join("/");
  await store.clipboardPaste(target);
}
async function ctxDuplicate(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  await store.duplicatePath(n.path);
}
const canPaste = computed(() => fsClipboard.value !== null);
</script>

<template>
  <aside
    class="file-tree-pane flex h-full w-full min-w-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground"
  >
    <header class="border-b border-sidebar-border px-3 py-2">
      <button
        type="button"
        class="text-xs text-muted-foreground transition-colors hover:text-foreground"
        @click="back"
      >
        ← sessions
      </button>
      <div class="mt-1 truncate font-mono text-[13px] text-foreground">
        {{ session?.id ?? "—" }}
      </div>
      <div
        v-if="cwdShort"
        class="mt-0.5 truncate font-mono text-[11px] text-muted-foreground"
        :title="session?.cwd"
      >
        {{ cwdShort }}
      </div>
    </header>

    <!-- ── Toolbar row: workspace label + 4 action icons ──────────────── -->
    <div
      class="flex items-center justify-between border-b border-sidebar-border px-3 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground"
    >
      <span>workspace · {{ fileCount }}</span>
      <div class="flex items-center gap-0.5">
        <button
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          title="New File"
          @click="toolbarNewFile"
        >
          <Icon icon="codicon:new-file" class="h-[14px] w-[14px]" />
        </button>
        <button
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          title="New Folder"
          @click="toolbarNewFolder"
        >
          <Icon icon="codicon:new-folder" class="h-[14px] w-[14px]" />
        </button>
        <button
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          title="Refresh"
          @click="toolbarRefresh"
        >
          <Icon icon="codicon:refresh" class="h-[14px] w-[14px]" />
        </button>
        <button
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          title="Collapse All"
          @click="toolbarCollapseAll"
        >
          <Icon icon="codicon:collapse-all" class="h-[14px] w-[14px]" />
        </button>
      </div>
    </div>

    <!-- ── Body: recursive tree ──────────────────────────────────────── -->
    <div class="flex-1 overflow-y-auto py-1 text-sm">
      <div
        v-if="!tree.length"
        class="px-3 py-3 text-xs text-muted-foreground"
      >
        Empty. Files appear here as the agent creates them.
      </div>
      <TreeNodeRow
        v-for="node in tree"
        :key="node.path"
        :node="node"
        :depth="0"
        :default-expanded="true"
        @open-context-menu="openContextMenu"
      />
    </div>

    <!-- ── Floating context menu ─────────────────────────────────────── -->
    <div
      v-if="menu.open && menu.node"
      class="fixed z-50 min-w-[180px] overflow-hidden rounded-md border border-border bg-card shadow-lg"
      :style="{ left: `${menu.x}px`, top: `${menu.y}px` }"
      @click.stop
      @contextmenu.prevent
    >
      <button
        v-if="!menu.node.isDir"
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxOpen"
      >
        <Icon icon="codicon:go-to-file" class="h-[14px] w-[14px] text-muted-foreground" />
        Open
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxNewFile"
      >
        <Icon icon="codicon:new-file" class="h-[14px] w-[14px] text-muted-foreground" />
        New File…
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxNewFolder"
      >
        <Icon icon="codicon:new-folder" class="h-[14px] w-[14px] text-muted-foreground" />
        New Folder…
      </button>
      <div class="border-t border-border"></div>
      <!-- Cut / Copy / Paste / Duplicate — Finder-style file ops. Paste is
           greyed out when no clipboard entry, paste-into is implicit when
           the right-clicked node is a folder. -->
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxCut"
      >
        <Icon icon="codicon:list-selection" class="h-[14px] w-[14px] text-muted-foreground" />
        Cut
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxCopy"
      >
        <Icon icon="codicon:files" class="h-[14px] w-[14px] text-muted-foreground" />
        Copy
      </button>
      <button
        type="button"
        :disabled="!canPaste"
        :class="[
          'flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px]',
          canPaste ? 'hover:bg-accent' : 'cursor-not-allowed text-muted-foreground/60',
        ]"
        :title="canPaste ? `Paste ${fsClipboard?.path}` : 'Clipboard is empty'"
        @click="ctxPaste"
      >
        <Icon icon="codicon:clippy" class="h-[14px] w-[14px] text-muted-foreground" />
        Paste<span v-if="canPaste" class="ml-auto text-[10px] text-muted-foreground">{{ fsClipboard?.op }}</span>
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxDuplicate"
      >
        <Icon icon="codicon:diff-added" class="h-[14px] w-[14px] text-muted-foreground" />
        Duplicate
      </button>
      <div class="border-t border-border"></div>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxRename"
      >
        <Icon icon="codicon:edit" class="h-[14px] w-[14px] text-muted-foreground" />
        Rename
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-accent"
        @click="ctxCopyPath"
      >
        <Icon icon="codicon:copy" class="h-[14px] w-[14px] text-muted-foreground" />
        Copy Path
      </button>
      <div class="border-t border-border"></div>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] text-destructive hover:bg-destructive/15"
        @click="ctxDelete"
      >
        <Icon icon="codicon:trash" class="h-[14px] w-[14px]" />
        Delete
      </button>
    </div>
  </aside>
</template>
