<!--
  MessageList — vertical chat column.

  We tried virtualizing this with `vue-virtual-scroller`'s DynamicScroller
  but it caused real layout bugs: late-arriving message footers (e.g. the
  prior UsageChip, error banners, tool cards that hydrate post-stream)
  ended up scrolled below the visible area because the scroller's
  measurement raced with our scroll-to-bottom call.
  Reverted to a simple `v-for` list — same approach the reference codebase
  (pi-mono-main `MessageList`) uses with great results. We can re-add
  virtualization when we actually have thousands of messages and have
  thoroughly tested measurement against streaming + late-arriving chips.

  Auto-scroll: stay pinned to the bottom unless the user scrolled up
  themselves (TUI / Cursor convention).
-->
<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import type { ChatMessage } from "../types/rpc";
import AssistantMessage from "./AssistantMessage.vue";
import UserMessage from "./UserMessage.vue";

const props = defineProps<{ messages: ChatMessage[] }>();

const scroller = ref<HTMLDivElement | null>(null);
const stickToBottom = ref(true);

function onScroll(): void {
  const el = scroller.value;
  if (!el) return;
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
  stickToBottom.value = distanceFromBottom < 80;
}

function scrollToBottom(): void {
  const el = scroller.value;
  if (el) el.scrollTop = el.scrollHeight;
}

// New message → re-pin to bottom.
watch(
  () => props.messages.length,
  async () => {
    if (!stickToBottom.value) return;
    await nextTick();
    scrollToBottom();
  },
);

// Streaming growth on the LAST message → keep pinning.
// We hash whatever can grow: text length, thinking length, parts count,
// and crucially `usage.cost` so the chip arriving AFTER text completion
// doesn't end up scrolled out of view.
watch(
  () => {
    const last = props.messages[props.messages.length - 1];
    if (!last || last.kind !== "assistant") return 0;
    return (
      last.text.length +
      last.thinking.length +
      last.toolCalls.length * 1000 +
      (last.parts?.length ?? 0) * 10 +
      (last.usage?.cost ?? 0) * 1_000_000
    );
  },
  async () => {
    if (!stickToBottom.value) return;
    await nextTick();
    scrollToBottom();
  },
);

onMounted(() => {
  // Start at the bottom so users see the most recent activity, not the
  // top of a (potentially long) restored history.
  nextTick(scrollToBottom);
});
</script>

<template>
  <div class="relative flex h-full min-h-0 w-full flex-col">
    <div
      ref="scroller"
      class="flex-1 overflow-y-auto px-5 pb-6 pt-3"
      @scroll="onScroll"
    >
      <div
        v-if="messages.length === 0"
        class="mt-12 text-center text-sm text-muted-foreground"
      >
        <p class="mb-2">No messages yet.</p>
        <p class="text-xs">Type below to start the conversation.</p>
      </div>

      <template v-for="m in messages" :key="m.id">
        <UserMessage v-if="m.kind === 'user'" :id="m.id" :text="m.text" />
        <AssistantMessage v-else :message="m" />
      </template>
    </div>

    <!-- "Jump to latest" affordance when user has scrolled up. -->
    <button
      v-if="!stickToBottom && messages.length > 0"
      type="button"
      class="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full border border-border bg-card/95 px-3 py-1 text-[11px] text-muted-foreground shadow-md backdrop-blur transition-colors hover:bg-accent hover:text-foreground"
      title="Scroll to latest message"
      @click="stickToBottom = true; scrollToBottom()"
    >↓ jump to latest</button>
  </div>
</template>
