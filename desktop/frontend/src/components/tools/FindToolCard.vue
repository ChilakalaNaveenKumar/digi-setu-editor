<!--
  FindToolCard — compact chip for the `find` built-in tool.
        ▸ Found *.ts in src/                                 [⧉]
-->
<script setup lang="ts">
import { computed } from "vue";
import type { ToolCall } from "../../types/rpc";
import CompactToolChip from "./CompactToolChip.vue";

const props = defineProps<{ call: ToolCall }>();

interface FindArgs {
  pattern?: unknown;
  path?: unknown;
}

const args = computed<FindArgs>(() => (props.call.args ?? {}) as FindArgs);

const pattern = computed<string>(() =>
  typeof args.value.pattern === "string" ? args.value.pattern : "",
);

const scope = computed<string>(() => {
  const a = args.value;
  return typeof a.path === "string" && a.path ? a.path : ".";
});

const main = computed(() => `${pattern.value} in ${scope.value}`);
</script>

<template>
  <CompactToolChip
    :call="call"
    verb="Found"
    :main="main"
    :tooltip="`pattern: ${pattern}\nscope: ${scope}`"
    :copy-value="pattern"
  />
</template>
