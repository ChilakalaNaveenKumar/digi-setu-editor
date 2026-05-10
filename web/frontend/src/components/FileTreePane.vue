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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";
import { useChatStore } from "../stores/chat";
import { useFilesStore } from "../stores/files";
import { useUiStore } from "../stores/ui";
import { buildTree, type TreeNode } from "../lib/file-tree";
import TreeNodeRow from "./TreeNodeRow.vue";

import { useWorkspaceStore } from "../stores/workspace";
import { uploadAttachments } from "../api/attachments";

const router = useRouter();
const chat = useChatStore();
const files = useFilesStore();
const ui = useUiStore();
const workspace = useWorkspaceStore();
const { session } = storeToRefs(chat);
const { fileEntries, treeUiState } = storeToRefs(files);

// Root-level drag-drop: drop directly into the workspace root, not on
// any specific folder row. Same dragenter/leave counter pattern as the
// composer + tree rows so the highlight survives child mouseovers.
const rootDragOver = ref(false);
const rootDragCounter = ref(0);
const rootUploading = ref(false);

function _rootDragHasFiles(e: DragEvent): boolean {
  const types = e.dataTransfer?.types;
  if (!types) return false;
  return Array.from(types).includes("Files");
}

function onRootDragEnter(e: DragEvent): void {
  if (!_rootDragHasFiles(e)) return;
  e.preventDefault();
  rootDragCounter.value += 1;
  rootDragOver.value = true;
}
function onRootDragLeave(e: DragEvent): void {
  if (!_rootDragHasFiles(e)) return;
  rootDragCounter.value = Math.max(0, rootDragCounter.value - 1);
  if (rootDragCounter.value === 0) rootDragOver.value = false;
}
function onRootDragOver(e: DragEvent): void {
  if (!_rootDragHasFiles(e)) return;
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
}
async function onRootDrop(e: DragEvent): Promise<void> {
  if (!_rootDragHasFiles(e)) return;
  e.preventDefault();
  rootDragCounter.value = 0;
  rootDragOver.value = false;
  const list = e.dataTransfer?.files;
  if (!list || list.length === 0) return;
  if (!workspace.activeId) return;
  rootUploading.value = true;
  try {
    // Empty target_dir → backend's default ("uploads"). User can move
    // them out from there if they want a different home.
    const result = await uploadAttachments(workspace.activeId, Array.from(list));
    chat.addPendingAttachments(
      result.saved.map((s) => ({
        localId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: s.name,
        size: s.size,
        mime: s.mime,
        path: s.path,
        agentPath: s.agent_path,
      })),
    );
    void files.refreshTree();
  } catch (exc) {
    ui.toastError("Upload failed", exc);
  } finally {
    rootUploading.value = false;
  }
}

// Click on empty tree body clears the multi-selection — same as
// clicking empty space in VS Code's Explorer.
function onRootClick(e: MouseEvent): void {
  const target = e.target as HTMLElement | null;
  if (!target) return;
  // Only when click landed directly on the scroll body; child rows
  // stop propagation via their own handlers.
  if (target.dataset.role !== "tree-body") return;
  files.clearSelection();
}

onMounted(() => {
  void files.refreshTree();
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
  chat.disconnect();
  router.push({ name: "sessions" });
}

// ── Toolbar actions ────────────────────────────────────────────────────
/** Where new files/folders should land if the user hits the toolbar
 *  button. We don't track an explicit "selected folder" yet, so fall
 *  back to the root (`""`) — the inline input row at the top of the
 *  body handles that case so it works even on an empty workspace. */
const toolbarTargetFolder = computed(() => {
  const cf = files.currentFile;
  if (!cf?.path) return ""; // root
  const segs = cf.path.split("/").filter(Boolean);
  segs.pop();
  return segs.join("/");
});

function toolbarNewFile(): void {
  files.startCreate(toolbarTargetFolder.value, "file");
}
function toolbarNewFolder(): void {
  files.startCreate(toolbarTargetFolder.value, "folder");
}
function toolbarRefresh(): void {
  void files.refreshTree();
}
function toolbarCollapseAll(): void {
  files.collapseAll();
}

// ── Root-level inline create ──────────────────────────────────────────
// The recursive TreeNodeRow only renders the "new name" input under an
// EXISTING folder node. If the user clicks New File on an empty
// workspace (no nodes to attach to) the input would never appear. This
// dedicated row covers the root case (`creatingUnderPath === ""`).
const rootCreating = computed(() =>
  treeUiState.value.creatingUnderPath === "" ? treeUiState.value.creatingKind : null,
);
const rootNewName = ref("");
const rootNewInput = ref<HTMLInputElement | null>(null);

watch(rootCreating, async (kind) => {
  if (kind) {
    rootNewName.value = "";
    await nextTick();
    rootNewInput.value?.focus();
  }
});

function commitRootCreate(): void {
  const name = rootNewName.value.trim();
  if (!name) {
    files.cancelCreate();
    return;
  }
  if (rootCreating.value === "file") {
    void files.createFile(name);
  } else if (rootCreating.value === "folder") {
    void files.createFolder(name);
  }
}

function cancelRootCreate(): void {
  files.cancelCreate();
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
  //
  // Item count (max — file with non-empty clipboard):
  //   Open, New File…, New Folder…, ─, Cut, Copy, Paste, Duplicate,
  //   ─, Rename, Copy Path, Copy Relative Path, ─, Delete
  // = 11 buttons (~30 px) + 3 separators (~1 px) + ~16 px padding
  // ≈ 350 px. Bumped to 440 to leave headroom for higher-DPI fonts
  // and the lower 8 px viewport gutter. The container also gets a
  // CSS max-h + overflow-y-auto safety net for very small windows.
  const menuW = 220;
  const menuH = 440;
  const x = Math.max(8, Math.min(payload.x, window.innerWidth - menuW - 8));
  const y = Math.max(8, Math.min(payload.y, window.innerHeight - menuH - 8));
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
  if (!n.isDir) void files.openFile(n.path);
}

function ctxRename(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  files.startRename(n.path);
}

async function ctxDelete(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  const label = n.isDir ? "folder" : "file";
  const ok = await ui.confirm({
    title: `Delete ${label}?`,
    description:
      `"${n.path}" will be deleted from the workspace.` +
      (n.isDir ? " All contents inside will be removed too." : "") +
      " This cannot be undone.",
    confirmLabel: "Delete",
    variant: "destructive",
  });
  if (!ok) return;
  await files.deletePath(n.path);
}

// VS Code parity:
//   "Copy Path"           → ABSOLUTE path on disk (cwd + relative).
//                            Most useful for shell tools, IDE search,
//                            paste-into-Finder.
//   "Copy Relative Path"  → workspace-relative (matches what the AI's
//                            tools and our own routes accept).
async function ctxCopyAbsolutePath(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  // Resolution order for the workspace root:
  //   1. workspace.active.path  ← always set when the file tree is
  //      rendered (the route guard for /workspaces/:id sets activeId
  //      before this view mounts), so this is the preferred source.
  //   2. session.value.cwd      ← chat-session's cwd. Only populated
  //      AFTER the chat WS finishes its session handshake. On web
  //      this almost always wins anyway because the WS handshake is
  //      fast, but right-clicking during the initial reconnect
  //      window would otherwise silently fall back to relative.
  // The web workspace.active.path is the SERVER's absolute path
  // (e.g. /srv/pi/workspaces/<wsid>) — same value chat_ws emits in
  // its session event, so users who relied on session.cwd see no
  // behaviour change here, just better availability.
  const root = (
    workspace.active?.path ??
    session.value?.cwd ??
    ""
  ).replace(/\/+$/, "");
  const text = root ? `${root}/${n.path}` : n.path;
  try {
    await navigator.clipboard.writeText(text);
    ui.toast({ message: "Path copied to clipboard", kind: "success", ttl: 1500 });
  } catch {
    /* ignore */
  }
}

async function ctxCopyRelativePath(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  try {
    await navigator.clipboard.writeText(n.path);
    ui.toast({ message: "Relative path copied", kind: "success", ttl: 1500 });
  } catch {
    /* ignore */
  }
}

function ctxNewFile(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  const parent = n.isDir ? n.path : n.path.split("/").slice(0, -1).join("/");
  files.startCreate(parent, "file");
}

function ctxNewFolder(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  const parent = n.isDir ? n.path : n.path.split("/").slice(0, -1).join("/");
  files.startCreate(parent, "folder");
}

// ── Cut / Copy / Paste / Duplicate ────────────────────────────────────
const { fsClipboard } = storeToRefs(files);

function ctxCut(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  files.clipboardCut(n.path, n.isDir);
}
function ctxCopy(): void {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  files.clipboardCopy(n.path, n.isDir);
}
async function ctxPaste(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n || !fsClipboard.value) return;
  const target = n.isDir ? n.path : n.path.split("/").slice(0, -1).join("/");
  await files.clipboardPaste(target);
}
async function ctxDuplicate(): Promise<void> {
  const n = menu.value.node;
  closeContextMenu();
  if (!n) return;
  await files.duplicatePath(n.path);
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
        class="inline-flex items-center gap-1 text-caption text-muted-foreground transition-colors hover:text-foreground"
        @click="back"
      >
        <Icon icon="codicon:arrow-left" class="h-3 w-3" />
        {{ $t("nav.sessions") }}
      </button>
      <!-- Session ID stays in mono — it's a literal token the user may
           need to copy/paste (e.g. for support tickets). -->
      <div class="mt-1 truncate font-mono text-body-lg text-foreground">
        {{ session?.id ?? "—" }}
      </div>
      <div
        v-if="cwdShort"
        class="mt-0.5 truncate font-mono text-caption text-muted-foreground"
        :title="session?.cwd"
      >
        {{ cwdShort }}
      </div>
    </header>

    <!-- ── Toolbar row: workspace label + 4 action icons ──────────────── -->
    <div
      class="flex items-center justify-between border-b border-sidebar-border px-3 py-1.5 text-caption uppercase tracking-wide text-muted-foreground"
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
    <div
      data-role="tree-body"
      class="relative flex-1 overflow-y-auto py-1 text-lead"
      :class="rootDragOver && 'ring-2 ring-primary ring-inset'"
      @click="onRootClick"
      @dragenter="onRootDragEnter"
      @dragleave="onRootDragLeave"
      @dragover="onRootDragOver"
      @drop="onRootDrop"
    >
      <!-- Drop overlay shown while user is dragging OS files over the
           tree body but not over any specific folder row. -->
      <div
        v-if="rootDragOver"
        class="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-primary/10 backdrop-blur-[1px]"
      >
        <div
          class="flex items-center gap-2 rounded-md border border-primary bg-card px-3 py-2 text-lead font-medium text-foreground shadow"
        >
          <Icon
            :icon="rootUploading ? 'codicon:loading' : 'codicon:cloud-upload'"
            :class="rootUploading && 'animate-spin'"
            class="h-4 w-4 text-primary"
          />
          {{
            rootUploading
              ? "Uploading…"
              : "Drop to upload to workspace/uploads/"
          }}
        </div>
      </div>
      <!-- Root-level inline create input. Renders only when the toolbar
           "New File / New Folder" was clicked with no folder context (or
           the workspace is still empty). The TreeNodeRow input only fires
           inside an existing folder, so this row is what makes the toolbar
           buttons functional on a brand-new workspace. -->
      <div
        v-if="rootCreating"
        class="flex items-center gap-1 px-1 py-[3px]"
      >
        <span class="inline-block h-4 w-3 shrink-0"></span>
        <Icon
          :icon="
            rootCreating === 'folder'
              ? 'material-icon-theme:folder'
              : 'material-icon-theme:file'
          "
          class="h-[16px] w-[16px] shrink-0 opacity-70"
        />
        <input
          ref="rootNewInput"
          v-model="rootNewName"
          type="text"
          :placeholder="rootCreating === 'folder' ? 'new folder name' : 'new file name'"
          class="min-w-0 flex-1 rounded-sm border border-primary/50 bg-background px-1 py-[1px] font-mono text-body text-foreground outline-none focus:ring-1 focus:ring-primary"
          @keydown.enter.prevent="commitRootCreate"
          @keydown.esc.prevent="cancelRootCreate"
          @blur="commitRootCreate"
        />
      </div>

      <div
        v-if="!tree.length && !rootCreating"
        class="px-3 py-3 text-body text-muted-foreground"
      >
        Empty. Files appear here as the agent creates them — or use the
        <Icon icon="codicon:new-file" class="inline-block h-3 w-3" /> /
        <Icon icon="codicon:new-folder" class="inline-block h-3 w-3" />
        buttons above to create one yourself.
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
    <!--
         max-h + overflow-y-auto guarantees that on tiny windows (the
         11" laptop case where the user hit this bug first) the menu
         stays clickable even if our positional clamp wasn't enough —
         worst case the user scrolls inside the menu instead of seeing
         items disappear off the bottom of the viewport.
    -->
    <div
      v-if="menu.open && menu.node"
      class="fixed z-50 min-w-[220px] max-h-[calc(100vh-16px)] overflow-y-auto overflow-x-hidden rounded-md border border-border bg-card shadow-lg"
      :style="{ left: `${menu.x}px`, top: `${menu.y}px` }"
      @click.stop
      @contextmenu.prevent
    >
      <button
        v-if="!menu.node.isDir"
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        @click="ctxOpen"
      >
        <Icon icon="codicon:go-to-file" class="h-[14px] w-[14px] text-muted-foreground" />
        Open
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        @click="ctxNewFile"
      >
        <Icon icon="codicon:new-file" class="h-[14px] w-[14px] text-muted-foreground" />
        New File…
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
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
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        @click="ctxCut"
      >
        <Icon icon="codicon:list-selection" class="h-[14px] w-[14px] text-muted-foreground" />
        Cut
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        @click="ctxCopy"
      >
        <Icon icon="codicon:files" class="h-[14px] w-[14px] text-muted-foreground" />
        Copy
      </button>
      <button
        type="button"
        :disabled="!canPaste"
        :class="[
          'flex w-full items-center gap-2 px-3 py-1.5 text-left text-body',
          canPaste ? 'hover:bg-accent' : 'cursor-not-allowed text-muted-foreground/60',
        ]"
        :title="canPaste ? `Paste ${fsClipboard?.path}` : 'Clipboard is empty'"
        @click="ctxPaste"
      >
        <Icon icon="codicon:clippy" class="h-[14px] w-[14px] text-muted-foreground" />
        Paste<span v-if="canPaste" class="ml-auto text-caption text-muted-foreground">{{ fsClipboard?.op }}</span>
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        @click="ctxDuplicate"
      >
        <Icon icon="codicon:diff-added" class="h-[14px] w-[14px] text-muted-foreground" />
        Duplicate
      </button>
      <div class="border-t border-border"></div>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        @click="ctxRename"
      >
        <Icon icon="codicon:edit" class="h-[14px] w-[14px] text-muted-foreground" />
        Rename
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        title="Copy the absolute filesystem path (good for terminal, Finder, external editors)"
        @click="ctxCopyAbsolutePath"
      >
        <Icon icon="codicon:copy" class="h-[14px] w-[14px] text-muted-foreground" />
        Copy Path
        <span class="ml-auto font-mono text-caption text-muted-foreground">⌥⌘C</span>
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body hover:bg-accent"
        title="Copy the path relative to this workspace (good for AI prompts and our APIs)"
        @click="ctxCopyRelativePath"
      >
        <Icon icon="codicon:references" class="h-[14px] w-[14px] text-muted-foreground" />
        Copy Relative Path
        <span class="ml-auto font-mono text-caption text-muted-foreground">⌥⇧⌘C</span>
      </button>
      <div class="border-t border-border"></div>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-body text-destructive hover:bg-destructive/15"
        @click="ctxDelete"
      >
        <Icon icon="codicon:trash" class="h-[14px] w-[14px]" />
        Delete
      </button>
    </div>
  </aside>
</template>
