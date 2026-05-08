<!--
  ReadToolCard — compact chip for the `read` built-in tool.

  Matches the inline style used by Claude Code / Cursor:
        ▸ Read APPEND_SYSTEM.md L1-93                    [⧉]

  Click the chip → if the path lives inside our workspace, open it in the
  editor pane. Otherwise (system files, /etc/hosts, ~/anything) it's still
  hoverable + copyable but not openable (we don't expose arbitrary disk
  reads from the file API).
-->
<script setup lang="ts">
import { computed } from "vue";
import { useFilesStore } from "../../stores/files";
import type { ToolCall } from "../../types/rpc";
import CompactToolChip from "./CompactToolChip.vue";

const props = defineProps<{ call: ToolCall }>();
const files = useFilesStore();

interface ReadArgs {
  path?: unknown;
  file_path?: unknown;
  offset?: unknown;
  limit?: unknown;
}

const args = computed<ReadArgs>(() => (props.call.args ?? {}) as ReadArgs);

const fullPath = computed<string>(() => {
  const a = args.value;
  const p = typeof a.path === "string" ? a.path : typeof a.file_path === "string" ? a.file_path : "";
  return p;
});

/**
 * Is this path inside our exposed workspace? Workspace paths are either
 * `workspace/foo.txt` (agent's view) or just `foo.txt` (backend's view).
 * Anything absolute or pointing outside is treated as out-of-workspace.
 */
const inWorkspace = computed<boolean>(() => {
  const p = fullPath.value;
  if (!p) return false;
  if (p.startsWith("/")) return false;
  if (p.startsWith("..")) return false;
  if (p.startsWith("~")) return false;
  return true;
});

const lineRange = computed<string>(() => {
  const a = args.value;
  const off = typeof a.offset === "number" ? a.offset : undefined;
  const lim = typeof a.limit === "number" ? a.limit : undefined;
  if (off === undefined && lim === undefined) return "";
  const start = off ?? 1;
  if (lim === undefined) return ` L${start}-`;
  return ` L${start}-${start + lim - 1}`;
});

/** Shorten very long paths for the chip; keep full path in the tooltip. */
const displayPath = computed<string>(() => {
  const p = fullPath.value;
  if (!p) return "(no path)";
  if (p.length <= 60) return p;
  // Keep last segment + parent for context, ellide the middle.
  const parts = p.split("/");
  const tail = parts.slice(-2).join("/");
  return `…/${tail}`;
});

const main = computed(() => `${displayPath.value}${lineRange.value}`);

function open(): void {
  if (!inWorkspace.value) return;
  void files.openFile(fullPath.value);
}
</script>

<template>
  <CompactToolChip
    :call="call"
    verb="Read"
    :main="main"
    :tooltip="`${fullPath}${lineRange ? ` (lines ${lineRange.trim().slice(1)})` : ''}` + (inWorkspace ? ' · click to open' : ' · outside workspace (read-only)')"
    :copy-value="fullPath"
    :selectable="inWorkspace"
    @select="open"
  />
</template>
