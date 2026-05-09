/**
 * UI primitives used app-wide: toast notifications + confirm dialog.
 *
 * No deps on other stores. Components mount Toast.vue / ConfirmModal.vue
 * once in App.vue and consume the state from here.
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import { i18n } from "../i18n";
import { ApiError } from "../api/client";

export type ToastKind = "info" | "success" | "error";

export interface ToastEntry {
  id: string;
  message: string;
  kind: ToastKind;
}

/**
 * Translate an HTTP-layer failure into a user-friendly message.
 *
 * Plain `${prefix}: ${exc.message}` leaks the FastAPI `detail` string
 * straight to the UI ("not signed in", "permission denied", "503
 * Service Unavailable"). Worse, we used to also feed those strings
 * through the AI-provider error classifier, which would then label a
 * 503 from the local sidecar as "The AI service is overloaded right
 * now" — flat-out wrong.
 *
 * This helper centralises the mapping. Callers like
 * ``stores/workspace.ts`` get ONE consistent translation so 401/403/
 * 5xx surfaces the same in every screen, and the raw detail string
 * is preserved as a fallback for unknown statuses.
 */
function _httpErrorMessage(exc: unknown): string {
  const t = i18n.global.t.bind(i18n.global);
  if (exc instanceof ApiError) {
    if (exc.status === 401) return t("toast.notSignedIn");
    if (exc.status === 403) return t("toast.permissionDenied");
    if (exc.status === 404) return t("toast.notFound");
    if (exc.status === 408 || exc.status === 504) return t("toast.timeout");
    if (exc.status === 429) return t("toast.tooManyRequests");
    // 5xx from our own sidecar / cloud — never call this an "AI
    // provider overload" because it isn't necessarily about an LLM.
    if (exc.status >= 500 && exc.status < 600) return t("toast.serverError");
    if (exc.message) return exc.message;
    return t("toast.requestFailed");
  }
  if (exc instanceof Error && exc.message) return exc.message;
  return String(exc) || t("toast.requestFailed");
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
    const msg = _httpErrorMessage(exc);
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
