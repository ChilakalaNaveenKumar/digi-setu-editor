<!--
  ConfirmModal — single global confirm dialog. Mounted once at the root
  of AppShell; opened/closed via store.confirm(...).

  Returns a Promise<boolean> so callers can do:

    if (!(await store.confirm({ ... }))) return;

  Renders as a centered overlay with a backdrop click-to-cancel,
  Esc-to-cancel, and Enter to commit. Variant `destructive` paints the
  primary action red.
-->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useUiStore } from "../stores/ui";

const ui = useUiStore();
const { confirmDialog } = storeToRefs(ui);

const open = computed(() => confirmDialog.value !== null);
const confirmBtn = ref<HTMLButtonElement | null>(null);

// Auto-focus the primary button so Enter commits and Esc cancels naturally.
watch(open, async (yes) => {
  if (yes) {
    await nextTick();
    confirmBtn.value?.focus();
  }
});

function onConfirm(): void {
  ui.resolveConfirm(true);
}
function onCancel(): void {
  ui.resolveConfirm(false);
}
function onBackdropClick(): void {
  // Backdrop click cancels (matches macOS / VS Code behaviour).
  onCancel();
}
function onKeydown(e: KeyboardEvent): void {
  if (!open.value) return;
  if (e.key === "Escape") {
    e.preventDefault();
    onCancel();
  } else if (e.key === "Enter") {
    e.preventDefault();
    onConfirm();
  }
}
onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

const variant = computed(() => confirmDialog.value?.variant ?? "default");
const confirmClass = computed(() => {
  if (variant.value === "destructive") {
    return "bg-destructive text-destructive-foreground hover:bg-destructive/90";
  }
  return "bg-primary text-primary-foreground hover:bg-primary/90";
});
</script>

<template>
  <Transition
    enter-active-class="transition-opacity duration-100 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-75 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open && confirmDialog"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-[2px]"
      @click.self="onBackdropClick"
    >
      <div
        class="w-[420px] max-w-[90vw] overflow-hidden rounded-md border border-border bg-card text-foreground shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div class="px-4 pt-4 pb-2">
          <h3 class="text-lead font-semibold">{{ confirmDialog.title }}</h3>
          <p
            v-if="confirmDialog.description"
            class="mt-1 whitespace-pre-line text-[12.5px] leading-relaxed text-muted-foreground"
          >
            {{ confirmDialog.description }}
          </p>
        </div>
        <div class="flex items-center justify-end gap-2 border-t border-border bg-card/40 px-3 py-2">
          <button
            type="button"
            class="rounded-sm border border-border bg-background px-3 py-1 text-body text-foreground hover:bg-accent"
            @click="onCancel"
          >{{ confirmDialog.cancelLabel ?? "Cancel" }}</button>
          <button
            ref="confirmBtn"
            type="button"
            :class="['rounded-sm px-3 py-1 text-body font-medium transition-colors', confirmClass]"
            @click="onConfirm"
          >{{ confirmDialog.confirmLabel ?? "Confirm" }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>
