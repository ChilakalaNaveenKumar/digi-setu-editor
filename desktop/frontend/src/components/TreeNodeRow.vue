<!--
  TreeNodeRow — recursive renderer for one TreeNode (dir or file).

  Folders : click toggles expand/collapse. Cmd/Ctrl+click toggles
            selection. Shift+click selects a range. Drag highlights as
            a drop target (move into / upload into).
  Files   : click selects + opens in EditorPane. Cmd/Ctrl+click toggles
            selection without opening. Shift+click selects a range.
            Multi-select drag carries the whole selection.

  Drag-drop matrix on a folder row:

    Source                         Action
    ──────────────────────────     ─────────────────────────────────
    OS files (Finder, etc.)        → upload to that folder via
                                     /api/.../attachments
    Tree paths (intra-tree drag)   → move all selected paths into
                                     that folder via /api/.../fs/move

    The two sources are distinguished by `dataTransfer.types`:
    OS-file drags include "Files"; intra-tree drags use a custom
    "application/x-pi-tree-paths" mime carrying a JSON array of paths.

  Inline edit modes (managed by FileTreePane via the store) are unchanged:
    • renaming, creatingUnderPath, etc.

  Right-click anywhere on the row opens the shared context menu in
  FileTreePane (we only emit `open-context-menu` with screen coords +
  path). Selection is preserved through right-click — same as VS Code.
-->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";
import { useChatStore } from "../stores/chat";
import { useFilesStore } from "../stores/files";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import { uploadAttachments } from "../api/attachments";
import type { TreeNode } from "../lib/file-tree";
import { iconForPath } from "../lib/file-icons";

const TREE_DRAG_MIME = "application/x-pi-tree-paths";

const props = defineProps<{
  node: TreeNode;
  depth: number;
  /** When true (top-level call), default-expand. Lower depth = more open. */
  defaultExpanded?: boolean;
}>();

const emit = defineEmits<{
  (e: "open-context-menu", payload: { x: number; y: number; node: TreeNode }): void;
}>();

const files = useFilesStore();
const chat = useChatStore();
const ui = useUiStore();
const workspace = useWorkspaceStore();
const { currentFile, treeUiState, selectedPaths, fileEntries } = storeToRefs(files);

const expanded = ref(props.defaultExpanded ?? props.depth < 2);

watch(
  () => treeUiState.value.expandAllNonce,
  () => (expanded.value = true),
);
watch(
  () => treeUiState.value.collapseAllNonce,
  () => {
    if (props.depth >= 0) expanded.value = false;
  },
);

const isActive = computed(
  () => currentFile.value?.path === props.node.path && !props.node.isDir,
);

const isSelected = computed(() => selectedPaths.value.has(props.node.path));

const indentPx = computed(() => 6 + props.depth * 12);

const iconName = computed(() =>
  iconForPath(props.node.name, props.node.isDir, expanded.value),
);

// ── inline rename ────────────────────────────────────────────────────
const renaming = computed(() => treeUiState.value.renamingPath === props.node.path);
const renameValue = ref("");
const renameInput = ref<HTMLInputElement | null>(null);

watch(renaming, async (yes) => {
  if (yes) {
    renameValue.value = props.node.name;
    await nextTick();
    renameInput.value?.focus();
    renameInput.value?.select();
  }
});

function commitRename(): void {
  const next = renameValue.value.trim();
  if (!next || next === props.node.name) {
    files.cancelRename();
    return;
  }
  void files.renamePath(props.node.path, next);
}

function cancelRename(): void {
  files.cancelRename();
}

// ── inline new-file / new-folder under this folder ───────────────────
const creatingHere = computed(() =>
  props.node.isDir &&
  treeUiState.value.creatingUnderPath === props.node.path
    ? treeUiState.value.creatingKind
    : null,
);
const newName = ref("");
const newInput = ref<HTMLInputElement | null>(null);

watch(creatingHere, async (kind) => {
  if (kind) {
    expanded.value = true;
    newName.value = "";
    await nextTick();
    newInput.value?.focus();
  }
});

function commitCreate(): void {
  const n = newName.value.trim();
  if (!n) {
    files.cancelCreate();
    return;
  }
  const fullPath = props.node.path ? `${props.node.path}/${n}` : n;
  if (creatingHere.value === "file") {
    void files.createFile(fullPath);
  } else if (creatingHere.value === "folder") {
    void files.createFolder(fullPath);
  }
}

function cancelCreate(): void {
  files.cancelCreate();
}

// ── click + selection model ──────────────────────────────────────────
function _orderedVisiblePaths(): string[] {
  // For range select we use the full sorted list of file entries the
  // backend returned. This matches how Finder / Explorer treat range
  // select (the universe is "everything in the workspace", not "only
  // expanded nodes"). It's also stable across renders, which an
  // expansion-aware order would not be.
  return fileEntries.value.map((e) => e.path);
}

function onClick(e: MouseEvent): void {
  if (renaming.value) return;
  // Selection modifiers always win — they shouldn't open files or
  // toggle folder expansion.
  if (e.shiftKey) {
    e.preventDefault();
    files.selectPath(props.node.path, "range", _orderedVisiblePaths());
    return;
  }
  if (e.metaKey || e.ctrlKey) {
    e.preventDefault();
    files.selectPath(props.node.path, "toggle");
    return;
  }
  files.selectPath(props.node.path, "single");
  if (props.node.isDir) {
    expanded.value = !expanded.value;
  } else {
    void files.openFile(props.node.path);
  }
}

function onContextMenu(e: MouseEvent): void {
  e.preventDefault();
  // Right-click on an unselected node makes it the sole selection
  // (matches VS Code / Finder); right-click on an already-selected
  // node preserves the multi-selection so the menu can apply to all.
  if (!isSelected.value) {
    files.selectPath(props.node.path, "single");
  }
  emit("open-context-menu", { x: e.clientX, y: e.clientY, node: props.node });
}

// ── drag (this node OUT) ─────────────────────────────────────────────
//
// Source semantics: dragging carries either
//   • the whole multi-selection if this node is part of it, OR
//   • just this one node if it isn't selected.
//
// Either way the data is shipped as JSON under our private MIME so the
// drop handler on a folder can tell intra-tree drags from OS file drops.
function onDragStart(e: DragEvent): void {
  if (!e.dataTransfer) return;
  const isInSel = selectedPaths.value.has(props.node.path);
  const paths = isInSel
    ? Array.from(selectedPaths.value)
    : [props.node.path];
  // If the node wasn't selected, also make it the new single selection
  // so the visual matches what's being dragged.
  if (!isInSel) files.selectPath(props.node.path, "single");
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData(TREE_DRAG_MIME, JSON.stringify(paths));
  // Set a plain-text fallback so dropping on an external app gets
  // something readable instead of nothing.
  e.dataTransfer.setData("text/plain", paths.join("\n"));
}

// ── drop (something falls ONTO this folder) ──────────────────────────
//
// We highlight on drag-enter/over and clear on leave. Counter pattern
// avoids flicker as the cursor crosses internal child elements.
const dragCounter = ref(0);
const dropOver = ref(false);
const isUploadingHere = ref(false);

function _supportedDrag(e: DragEvent): boolean {
  if (!props.node.isDir) return false;
  const types = e.dataTransfer?.types;
  if (!types) return false;
  return Array.from(types).includes("Files") ||
    Array.from(types).includes(TREE_DRAG_MIME);
}

function onDragEnter(e: DragEvent): void {
  if (!_supportedDrag(e)) return;
  e.preventDefault();
  e.stopPropagation();
  dragCounter.value += 1;
  dropOver.value = true;
  // Auto-expand folders on hover after a brief moment, like VS Code.
  // Implemented as a single timer per row that resets if the cursor
  // leaves before it fires.
  if (!expanded.value) {
    _scheduleAutoExpand();
  }
}

function onDragLeave(e: DragEvent): void {
  if (!_supportedDrag(e)) return;
  e.stopPropagation();
  dragCounter.value = Math.max(0, dragCounter.value - 1);
  if (dragCounter.value === 0) {
    dropOver.value = false;
    _cancelAutoExpand();
  }
}

function onDragOver(e: DragEvent): void {
  if (!_supportedDrag(e)) return;
  e.preventDefault();
  e.stopPropagation();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = Array.from(e.dataTransfer.types).includes("Files")
      ? "copy"
      : "move";
  }
}

let _autoExpandTimer: number | null = null;
function _scheduleAutoExpand(): void {
  _cancelAutoExpand();
  _autoExpandTimer = window.setTimeout(() => {
    expanded.value = true;
    _autoExpandTimer = null;
  }, 600);
}
function _cancelAutoExpand(): void {
  if (_autoExpandTimer != null) {
    clearTimeout(_autoExpandTimer);
    _autoExpandTimer = null;
  }
}

async function onDrop(e: DragEvent): Promise<void> {
  if (!_supportedDrag(e)) return;
  e.preventDefault();
  e.stopPropagation();
  dragCounter.value = 0;
  dropOver.value = false;
  _cancelAutoExpand();
  if (!props.node.isDir) return;

  const types = Array.from(e.dataTransfer?.types ?? []);

  // Intra-tree drag (move). Prefer this over Files when both are
  // somehow present.
  if (types.includes(TREE_DRAG_MIME)) {
    const raw = e.dataTransfer!.getData(TREE_DRAG_MIME);
    let payload: string[] = [];
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) payload = parsed.filter((p) => typeof p === "string");
    } catch {
      payload = [];
    }
    if (payload.length === 0) return;

    // Move every dragged path into this folder. We DO NOT use
    // `moveSelectedTo` because the dragged set may not equal the
    // current selection (the user could drag an unselected single).
    const targetDir = props.node.path;
    if (payload.includes(targetDir)) return; // no-op
    const wsid = workspace.activeId;
    if (!wsid) return;
    try {
      // Run moves in parallel; backend's unique_dest auto-renames on
      // collision so two files with the same basename land safely.
      await Promise.all(
        payload
          .filter((src) => src !== targetDir && !targetDir.startsWith(src + "/"))
          .map((src) => {
            const base = src.split("/").pop()!;
            const to = targetDir ? `${targetDir}/${base}` : base;
            // Lazily import to avoid a circular import with files store.
            return import("../api/files").then(({ movePath }) =>
              movePath(wsid, src, to),
            );
          }),
      );
    } catch (exc) {
      ui.toastError("Move failed", exc);
    } finally {
      files.clearSelection();
      void files.refreshTree();
    }
    return;
  }

  // OS-file drop → upload. Lands in the dropped folder, not the
  // workspace's `uploads/` (the user explicitly chose this folder
  // by where they dropped).
  if (types.includes("Files")) {
    const list = e.dataTransfer?.files;
    if (!list || list.length === 0) return;
    const wsid = workspace.activeId;
    if (!wsid) return;
    isUploadingHere.value = true;
    try {
      const result = await uploadAttachments(
        wsid,
        Array.from(list),
        props.node.path,
      );
      // Same chip semantics as composer-side uploads: each becomes a
      // pending attachment so the user's next chat message will
      // reference them. If they only wanted them stashed in a folder
      // (no chat reference), they can dismiss the chips one-by-one.
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
      // Auto-expand so the user can see what landed where.
      expanded.value = true;
    } catch (exc) {
      ui.toastError("Upload failed", exc);
    } finally {
      isUploadingHere.value = false;
    }
  }
}
</script>

<template>
  <div>
    <div
      :class="[
        'group/row flex w-full items-center gap-1 px-1 py-[3px] text-left font-sans text-[12.5px]',
        isActive
          ? 'border-l-2 border-l-primary bg-accent text-foreground'
          : 'border-l-2 border-l-transparent text-foreground/85 hover:bg-accent hover:text-foreground',
        isSelected && !isActive ? 'bg-primary/15 text-foreground' : '',
        dropOver ? 'ring-2 ring-primary ring-inset' : '',
        renaming ? 'bg-accent/40' : '',
      ]"
      :style="{ paddingLeft: `${indentPx}px` }"
      :draggable="!renaming"
      @click="onClick"
      @contextmenu="onContextMenu"
      @dragstart="onDragStart"
      @dragenter="onDragEnter"
      @dragleave="onDragLeave"
      @dragover="onDragOver"
      @drop="onDrop"
    >
      <!-- chevron column (folders only — files keep alignment with a spacer) -->
      <span
        v-if="node.isDir"
        class="inline-flex h-4 w-3 shrink-0 items-center justify-center text-muted-foreground transition-transform"
        :class="expanded ? 'rotate-90' : ''"
      >
        <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor" aria-hidden="true">
          <path d="M2 1l4 3-4 3z" />
        </svg>
      </span>
      <span v-else class="inline-block h-4 w-3 shrink-0"></span>

      <!-- file/folder icon (replaced by spinner during a drop-upload) -->
      <Icon
        v-if="!isUploadingHere"
        :icon="iconName"
        class="h-[16px] w-[16px] shrink-0"
      />
      <Icon
        v-else
        icon="codicon:loading"
        class="h-[16px] w-[16px] shrink-0 animate-spin text-primary"
      />

      <!-- name OR rename input -->
      <input
        v-if="renaming"
        ref="renameInput"
        v-model="renameValue"
        type="text"
        class="min-w-0 flex-1 rounded-sm border border-primary/50 bg-background px-1 py-[1px] font-mono text-body text-foreground outline-none focus:ring-1 focus:ring-primary"
        @click.stop
        @keydown.enter.prevent="commitRename"
        @keydown.esc.prevent="cancelRename"
        @blur="commitRename"
      />
      <span v-else class="min-w-0 flex-1 truncate" :title="node.path">
        {{ node.name }}
      </span>
    </div>

    <!-- inline new-file / new-folder input slot directly under this folder -->
    <div
      v-if="creatingHere"
      class="flex items-center gap-1 px-1 py-[3px]"
      :style="{ paddingLeft: `${indentPx + 12}px` }"
    >
      <span class="inline-block h-4 w-3 shrink-0"></span>
      <Icon
        :icon="
          creatingHere === 'folder'
            ? 'material-icon-theme:folder'
            : 'material-icon-theme:file'
        "
        class="h-[16px] w-[16px] shrink-0 opacity-70"
      />
      <input
        ref="newInput"
        v-model="newName"
        type="text"
        :placeholder="creatingHere === 'folder' ? 'new folder name' : 'new file name'"
        class="min-w-0 flex-1 rounded-sm border border-primary/50 bg-background px-1 py-[1px] font-mono text-body text-foreground outline-none focus:ring-1 focus:ring-primary"
        @keydown.enter.prevent="commitCreate"
        @keydown.esc.prevent="cancelCreate"
        @blur="commitCreate"
      />
    </div>

    <div v-if="node.isDir && expanded">
      <TreeNodeRow
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        @open-context-menu="(p) => emit('open-context-menu', p)"
      />
    </div>
  </div>
</template>
