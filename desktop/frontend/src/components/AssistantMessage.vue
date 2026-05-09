<!--
  AssistantMessage — body of an assistant turn.

  Renders the message's `parts[]` IN ORDER so a multi-step turn shows up
  the way the agent actually emitted it: thinking → tool → thinking → text →
  tool → ... — instead of pre-grouping all thinking on top.

  The router segments thinking: each "burst" between non-thinking events is
  its own collapsible "Thought for Xs" block. That makes long agentic turns
  far more legible.
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUpdated, ref } from "vue";
import { renderMarkdown } from "../lib/markdown";
import { enhanceCodeBlocks } from "../lib/code-block-enhance";
import type { AssistantMessage } from "../types/rpc";
import ThinkingBlock from "./ThinkingBlock.vue";
import ToolCardDispatch from "./tools/ToolCardDispatch.vue";

const props = defineProps<{ message: AssistantMessage }>();

const root = ref<HTMLElement | null>(null);

/**
 * If the very last part is `text` and the message is still streaming,
 * we want a pulsing caret on it. Cheap to compute per render.
 */
const lastPart = computed(() => {
  const p = props.message.parts;
  return p.length > 0 ? p[p.length - 1] : null;
});

function htmlOf(text: string): string {
  return text.trim() ? renderMarkdown(text) : "";
}

// Wire copy buttons onto every fenced code block on first paint AND on
// every streamed update. enhanceCodeBlocks() is idempotent (uses a
// data-attr marker) so calling it on every `onUpdated` is cheap.
onMounted(() => {
  void nextTick(() => enhanceCodeBlocks(root.value));
});
onUpdated(() => {
  void nextTick(() => enhanceCodeBlocks(root.value));
});
</script>

<template>
  <div ref="root" class="my-5 px-1">
    <template v-for="part in message.parts" :key="part.id">
      <ThinkingBlock
        v-if="part.kind === 'thinking'"
        :text="part.text"
        :started-at="part.startedAt"
        :ended-at="part.endedAt"
        :streaming="!message.done"
      />

      <div
        v-else-if="part.kind === 'text'"
        class="pi-markdown leading-relaxed text-foreground"
        v-html="htmlOf(part.text)"
      >
      </div>

      <ToolCardDispatch
        v-else-if="part.kind === 'tool'"
        :call="part.call"
      />
    </template>

    <span
      v-if="!message.done && lastPart?.kind === 'text' && lastPart.text.length > 0"
      class="ml-0.5 inline-block h-4 w-2 align-text-bottom bg-foreground animate-pulse"
    />

    <div
      v-if="message.error"
      class="mt-2 rounded border border-destructive/40 bg-destructive/10 px-2 py-1 font-mono text-body text-destructive"
    >
      {{ message.error }}
    </div>
  </div>
</template>
