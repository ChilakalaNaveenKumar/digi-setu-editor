/**
 * UI primitives used app-wide: toast notifications + confirm dialog.
 *
 * No deps on other stores. Components mount Toast.vue / ConfirmModal.vue
 * once in App.vue and consume the state from here.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

export type ToastKind = "info" | "success" | "error";

export interface ToastEntry {
  id: string;
  message: string;
  kind: ToastKind;
}

export interface ConfirmSpec {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
}

export const useUiStore = defineStore("ui", () => {
  const toasts = ref<ToastEntry[]>([]);
  const confirmDialog = ref<ConfirmSpec | null>(null);
  let confirmResolver: ((value: boolean) => void) | null = null;

  function toast(opts: { message: string; kind?: ToastKind; ttl?: number }): void {
    const id = `t_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const entry: ToastEntry = { id, message: opts.message, kind: opts.kind ?? "info" };
    toasts.value.push(entry);
    const ttl = opts.ttl ?? (entry.kind === "error" ? 6000 : 4000);
    window.setTimeout(() => dismissToast(id), ttl);
  }

  function dismissToast(id: string): void {
    const idx = toasts.value.findIndex((t) => t.id === id);
    if (idx >= 0) toasts.value.splice(idx, 1);
  }

  function toastError(prefix: string, exc: unknown): void {
    const msg = exc instanceof Error ? exc.message : String(exc);
    toast({ message: `${prefix}: ${msg}`, kind: "error" });
  }

  function confirm(spec: ConfirmSpec): Promise<boolean> {
    if (confirmResolver) confirmResolver(false);
    confirmDialog.value = spec;
    return new Promise<boolean>((resolve) => {
      confirmResolver = resolve;
    });
  }

  function resolveConfirm(value: boolean): void {
    if (confirmResolver) {
      confirmResolver(value);
      confirmResolver = null;
    }
    confirmDialog.value = null;
  }

  return {
    toasts,
    toast,
    dismissToast,
    toastError,
    confirmDialog,
    confirm,
    resolveConfirm,
  };
});
