<!--
  LsToolCard — compact chip for the `ls` built-in tool.
        ▸ Listed src/components/                            [⧉]
-->
<script setup lang="ts">
import { computed } from "vue";
import type { ToolCall } from "../../types/rpc";
import CompactToolChip from "./CompactToolChip.vue";

const props = defineProps<{ call: ToolCall }>();

interface LsArgs {
  path?: unknown;
  limit?: unknown;
}

const path = computed<string>(() => {
  const a = (props.call.args ?? {}) as LsArgs;
  return typeof a.path === "string" && a.path ? a.path : ".";
});
</script>

<template>
  <CompactToolChip
    :call="call"
    verb="Listed"
    :main="path"
    :tooltip="path"
    :copy-value="path"
  />
</template>
