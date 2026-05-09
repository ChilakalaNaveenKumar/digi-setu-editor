<!--
  ThinkingBlock — one collapsible "Thought for Xs" segment.

  We render ONE block per thinking segment (the router opens a new segment
  whenever a non-thinking event interrupts the current one), so a multi-
  step turn shows up as e.g.
      ▸ Thought for 4s
      Read foo.ts
      ▸ Thought for 8s
      Grepped /pattern/ in foo.ts
      "Here's what I found…"
  instead of one giant pre-tool-call thought blob.

  Collapsed by default. The duration ticker keeps counting up while the
  segment is still open (no endedAt), then freezes when it closes — so the
  user can see a current, in-progress thought clearly.
-->
<script setup lang="ts">
import { computed, ref } from "vue";
import { renderMarkdown } from "../lib/markdown";
import { nowTick, useGlobalClock } from "../lib/global-clock";

const props = defineProps<{
  text: string;
  startedAt: number;
  endedAt?: number;
  /** True while the agent is still mid-turn (the WHOLE assistant message). */
  streaming?: boolean;
}>();

const expanded = ref(false);

const html = computed(() => renderMarkdown(props.text || ""));

// Reuse a single shared 250ms tick across every ThinkingBlock instance.
// (Used to be `setInterval` per-instance — a long chat could end up with
// 50+ timers firing for collapsed blocks the user wasn't even looking at.)
useGlobalClock();

const isOpen = computed(() => props.endedAt === undefined);

const durationLabel = computed(() => {
  const end = props.endedAt ?? nowTick.value;
  const ms = Math.max(0, end - props.startedAt);
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.floor(s % 60)}s`;
});

const verb = computed(() => (isOpen.value && props.streaming ? "Thinking" : "Thought"));
</script>

<template>
  <div class="my-1.5 px-1">
    <button
      type="button"
      class="inline-flex items-center gap-1.5 text-caption uppercase tracking-wide text-muted-foreground transition-colors hover:text-foreground"
      :class="{ 'animate-shimmer': isOpen && streaming }"
      @click="expanded = !expanded"
    >
      <span class="select-none">{{ expanded ? "▾" : "▸" }}</span>
      <span>{{ verb }} for {{ durationLabel }}</span>
    </button>
    <div
      v-if="expanded"
      class="pi-markdown mt-1 italic leading-relaxed text-muted-foreground"
      v-html="html"
    />
  </div>
</template>
