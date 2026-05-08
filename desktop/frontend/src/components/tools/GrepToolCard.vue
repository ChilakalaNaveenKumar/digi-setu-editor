<!--
  GrepToolCard — compact chip for the `grep` built-in tool.
        ▸ Grepped /pattern/ in src/foo.ts                   [⧉]
-->
<script setup lang="ts">
import { computed } from "vue";
import type { ToolCall } from "../../types/rpc";
import CompactToolChip from "./CompactToolChip.vue";

const props = defineProps<{ call: ToolCall }>();

interface GrepArgs {
  pattern?: unknown;
  path?: unknown;
  glob?: unknown;
  ignoreCase?: unknown;
  literal?: unknown;
}

const args = computed<GrepArgs>(() => (props.call.args ?? {}) as GrepArgs);

const pattern = computed<string>(() =>
  typeof args.value.pattern === "string" ? args.value.pattern : "",
);

const scope = computed<string>(() => {
  const a = args.value;
  const p = typeof a.path === "string" && a.path ? a.path : ".";
  const g = typeof a.glob === "string" && a.glob ? ` (${a.glob})` : "";
  return `${p}${g}`;
});

const main = computed(() => {
  const trimmed = pattern.value.length > 50
    ? pattern.value.slice(0, 47) + "…"
    : pattern.value;
  return `/${trimmed}/ in ${scope.value}`;
});
</script>

<template>
  <CompactToolChip
    :call="call"
    verb="Grepped"
    :main="main"
    :tooltip="`pattern: ${pattern}\nscope: ${scope}`"
    :copy-value="pattern"
  />
</template>
