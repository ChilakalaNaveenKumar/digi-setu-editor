<!--
  Toast — non-blocking error / info banner stack.

  Replaces window.alert() (which BLOCKS the entire page and forces the
  user to dismiss before doing anything else). Toasts auto-dismiss after
  4s, can be dismissed manually with ×, and stack from bottom-right.

  Triggered from anywhere via the store: `store.toast({ message, kind })`.
-->
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useUiStore } from "../stores/ui";

const ui = useUiStore();
const { toasts } = storeToRefs(ui);
</script>

<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed bottom-4 right-4 z-[10000] flex flex-col gap-2"
      role="region"
      aria-label="Notifications"
    >
      <transition-group name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          :class="[
            'pointer-events-auto flex max-w-md items-start gap-2 rounded-md border px-3 py-2 text-[12.5px] shadow-lg backdrop-blur',
            t.kind === 'error'
              ? 'border-destructive/40 bg-destructive/15 text-destructive-foreground'
              : t.kind === 'success'
                ? 'border-emerald-700/40 bg-emerald-950/40 text-emerald-100'
                : 'border-border bg-card/95 text-foreground',
          ]"
          role="status"
        >
          <span class="leading-snug">{{ t.message }}</span>
          <button
            type="button"
            class="ml-2 shrink-0 rounded-sm px-1 text-current opacity-60 transition-opacity hover:opacity-100"
            title="Dismiss"
            @click="ui.dismissToast(t.id)"
          >×</button>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 180ms, transform 180ms;
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
