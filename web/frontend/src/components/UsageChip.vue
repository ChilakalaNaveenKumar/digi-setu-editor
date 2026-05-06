<!--
  UsageChip — per-message token + cost summary. Same compact form as the
  TUI footer (↑in ↓out Rcr Wcw $cost), rendered with muted-foreground.
-->
<script setup lang="ts">
import { computed } from "vue";
import { formatCost, formatTokens } from "../lib/format";

const props = defineProps<{
  usage?: {
    input: number;
    output: number;
    cacheRead: number;
    cacheWrite: number;
    cost: number;
  };
}>();

const parts = computed(() => {
  if (!props.usage) return [];
  const u = props.usage;
  const out: string[] = [];
  if (u.input) out.push(`↑${formatTokens(u.input)}`);
  if (u.output) out.push(`↓${formatTokens(u.output)}`);
  if (u.cacheRead) out.push(`R${formatTokens(u.cacheRead)}`);
  if (u.cacheWrite) out.push(`W${formatTokens(u.cacheWrite)}`);
  if (u.cost) out.push(formatCost(u.cost));
  return out;
});
</script>

<template>
  <div
    v-if="parts.length"
    class="mt-2 inline-flex items-center gap-2 font-mono text-[10px] text-muted-foreground"
  >
    <span v-for="(p, i) in parts" :key="i">{{ p }}</span>
  </div>
</template>
