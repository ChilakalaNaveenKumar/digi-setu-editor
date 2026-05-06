<!--
  TreeNodeRow — recursive renderer for one TreeNode (dir or file).

  Folders : click to expand/collapse; icon flips between closed/open.
  Files   : click to open in EditorPane via store.openFile().
  Active  : selected file gets a teal left rail + bg.

  Inline edit modes (managed by FileTreePane via the store):
    • renaming        — this row shows an inline <input> instead of name
    • newFileUnder    — folder shows an extra child row with "+ filename" input
    • newFolderUnder  — same, but for folder

  Right-click anywhere on the row opens the shared context menu in
  FileTreePane (we only emit an `open-context-menu` event with screen
  coords + path).
-->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";
import { useSessionStore } from "../stores/session";
import { shortSize, type TreeNode } from "../lib/file-tree";
import { iconForPath } from "../lib/file-icons";

const props = defineProps<{
  node: TreeNode;
  depth: number;
  /** When true (top-level call), default-expand. Lower depth = more open. */
  defaultExpanded?: boolean;
}>();

const emit = defineEmits<{
  (e: "open-context-menu", payload: { x: number; y: number; node: TreeNode }): void;
}>();

const store = useSessionStore();
const { currentFile, treeUiState } = storeToRefs(store);

const expanded = ref(props.defaultExpanded ?? props.depth < 2);

// Apply Collapse All / Expand All from the toolbar.
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
    store.cancelRename();
    return;
  }
  void store.renamePath(props.node.path, next);
}

function cancelRename(): void {
  store.cancelRename();
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
    store.cancelCreate();
    return;
  }
  const fullPath = props.node.path ? `${props.node.path}/${n}` : n;
  if (creatingHere.value === "file") {
    void store.createFile(fullPath);
  } else if (creatingHere.value === "folder") {
    void store.createFolder(fullPath);
  }
}

function cancelCreate(): void {
  store.cancelCreate();
}

// ── click + context-menu ─────────────────────────────────────────────
function onClick(): void {
  if (renaming.value) return;
  if (props.node.isDir) {
    expanded.value = !expanded.value;
  } else {
    void store.openFile(props.node.path);
  }
}

function onContextMenu(e: MouseEvent): void {
  e.preventDefault();
  emit("open-context-menu", { x: e.clientX, y: e.clientY, node: props.node });
}
</script>

<template>
  <div>
    <div
      :class="[
        'group/row flex w-full items-center gap-1 px-1 py-[3px] text-left font-sans text-[12.5px] hover:bg-accent',
        isActive
          ? 'border-l-2 border-l-primary bg-accent text-foreground'
          : 'border-l-2 border-l-transparent text-foreground/85 hover:text-foreground',
        renaming ? 'bg-accent/40' : '',
      ]"
      :style="{ paddingLeft: `${indentPx}px` }"
      @click="onClick"
      @contextmenu="onContextMenu"
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

      <!-- file/folder icon -->
      <Icon :icon="iconName" class="h-[16px] w-[16px] shrink-0" />

      <!-- name OR rename input -->
      <input
        v-if="renaming"
        ref="renameInput"
        v-model="renameValue"
        type="text"
        class="min-w-0 flex-1 rounded-sm border border-primary/50 bg-background px-1 py-[1px] font-mono text-[12px] text-foreground outline-none focus:ring-1 focus:ring-primary"
        @click.stop
        @keydown.enter.prevent="commitRename"
        @keydown.esc.prevent="cancelRename"
        @blur="commitRename"
      />
      <span v-else class="min-w-0 flex-1 truncate" :title="node.path">
        {{ node.name }}
      </span>

      <span
        v-if="!node.isDir && node.size > 0 && !renaming"
        class="text-[10px] tabular-nums text-muted-foreground/50 group-hover/row:text-muted-foreground"
      >
        {{ shortSize(node.size) }}
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
        class="min-w-0 flex-1 rounded-sm border border-primary/50 bg-background px-1 py-[1px] font-mono text-[12px] text-foreground outline-none focus:ring-1 focus:ring-primary"
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
