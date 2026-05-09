/**
 * UI primitives used app-wide: toast notifications + confirm dialog.
 *
 * No deps on other stores. Components mount Toast.vue / ConfirmModal.vue
 * once in App.vue and consume the state from here.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import { i18n } from "../i18n";
import { categorizeProviderError } from "../lib/event-router";

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

  /**
   * Show a user-facing error toast WITHOUT leaking raw exception
   * text. The raw exception is logged to the console so we can still
   * diagnose issues; the toast only ever shows:
   *
   *   <prefix> — <localised friendly sentence>
   *
   * `prefix` is the operation context the caller already provides as
   * a human sentence (e.g. "Failed to delete file"). The friendly
   * second half is derived by classifying the exception against the
   * same provider-error catalog the chat uses, so a fetch 503 becomes
   * "The service is overloaded right now…" and a stack trace becomes
   * "Something went wrong. Please try again."
   *
   * NEVER use `${prefix}: ${exc.message}` — random callers can pass
   * us anything (DOM exceptions, fetch errors, HTTP status blobs)
   * and we don't want them rendered to end users.
   */
  function toastError(prefix: string, exc: unknown): void {
    const raw = exc instanceof Error ? exc.message : String(exc ?? "");
    if (raw) {
      // eslint-disable-next-line no-console
      console.warn(`[ui.toastError] ${prefix} (raw, suppressed in UI):`, exc);
    }
    const { code } = categorizeProviderError(raw);
    const key = `errors.${code}`;
    const friendly = i18n.global.te(key)
      ? (i18n.global.t(key) as string)
      : (i18n.global.t("errors.internal") as string);
    toast({ message: `${prefix} — ${friendly}`, kind: "error" });
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
