<!--
  AnnotateOverlay — sticky-note feedback flow modeled after the
  typst-agent reference (digi-setu's pattern).

  Flow (single source of truth — no tool/color/size picker noise):

    1. User opens this modal on an image / SVG / PDF.
    2. (PDFs only) prev / next page navigation in the title bar.
    3. User drags a rectangle around the part they want feedback on.
       That single dark box IS the marker. We don't ship pencil /
       arrow / text tools — the rectangle is enough and matches the
       digi-setu UX.
    4. The MOMENT the rectangle lifts, a neutral sticky-note widget
       pops next to it with:
            - a 3-row editable textarea (placeholder: "What should
              I change?")
            - paperclip → file picker
            - paste / drag-drop → add more files
            - chip strip showing additional attachments
            - Send (primary) + Discard (X) buttons
    5. Send composites (page bitmap + rectangle) into a PNG, uploads
       it alongside any extra files into workspace/uploads/, drops
       all paths into the chat composer's pendingAttachments, and
       *fires the comment as a chat message* via the same path the
       composer uses (so it queues if pi is busy). Modal closes.

  Why no tool / color / size pickers?
    User feedback: "and most importantly we have dark box that is
    enough it doesn't have to be accurate". Drawing a rectangle and
    typing a comment is the entire job; everything else was visual
    noise that confused the flow.

  The sticky-note widget itself is inline (not Teleport) so it
  positions cleanly relative to the canvas — flipping pages while
  the sticky is open dismisses it (the marker is bound to a page).
-->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Icon } from "@iconify/vue";

import { uploadAttachments } from "../api/attachments";
import { useChatStore } from "../stores/chat";
import { useFilesStore } from "../stores/files";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

interface RectStroke {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface ExtraAttachment {
  localId: string;
  file: File;
  name: string;
  size: number;
  mime: string;
  /** Object URL for thumbnail preview when this is an image. */
  preview?: string;
}

const props = defineProps<{
  /** Direct image URL (image / SVG). Mutually exclusive with pdfUrl. */
  imageUrl?: string;
  /** PDF URL — overlay rasterizes pages internally. */
  pdfUrl?: string;
  /** Filename suggested for the saved annotation (without .png is OK). */
  defaultName: string;
  /** Optional badge text shown in the title bar. */
  subtitle?: string;
}>();

const emit = defineEmits<{
  /** Fired after Send completes; lets parent close the modal. */
  (e: "sent"): void;
  (e: "cancel"): void;
}>();

const chat = useChatStore();
const ws = useWorkspaceStore();
const files = useFilesStore();
const ui = useUiStore();

// Page state.
const currentPage = ref(1);
const pageCount = ref(1);
const isPdf = computed(() => Boolean(props.pdfUrl));
const sourceUrl = ref<string>("");
const pageDataUrls = new Map<number, string>();
const pageLoading = ref(false);

// The single in-flight rectangle. We only support ONE marker per
// annotate session; drawing a new rect replaces the previous one.
// This matches the typst-agent flow where each annotate session
// ships exactly one feedback message.
const stroke = ref<RectStroke | null>(null);
const drafting = ref<RectStroke | null>(null);

// Sticky-note state. `stickyOpen` is bound to whether `stroke` exists
// AND the user hasn't dismissed it; we don't auto-reopen when the
// user closes the sticky and then redraws (their explicit dismiss
// wins for that session).
const stickyOpen = ref(false);
const stickyPos = ref<{ x: number; y: number } | null>(null);
const comment = ref("");
const extraAttachments = ref<ExtraAttachment[]>([]);
const sending = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const stickyTextarea = ref<HTMLTextAreaElement | null>(null);

// Image / canvas refs for the source bitmap and overlay.
const canvas = ref<HTMLCanvasElement | null>(null);
const img = ref<HTMLImageElement | null>(null);
const stage = ref<HTMLDivElement | null>(null);
const filename = ref(props.defaultName);

// Image natural pixel dimensions for the current page. Used as the
// canvas internal size so the exported PNG has full resolution.
const imgNaturalW = ref(0);
const imgNaturalH = ref(0);

// ── source bootstrap (image vs pdf) ────────────────────────────────

async function loadInitial(): Promise<void> {
  if (props.imageUrl) {
    sourceUrl.value = props.imageUrl;
    pageCount.value = 1;
    return;
  }
  if (props.pdfUrl) {
    pageLoading.value = true;
    try {
      const { rasterizePdfPage } = await import("../lib/pdf-rasterize");
      const result = await rasterizePdfPage(props.pdfUrl, { page: 1, scale: 2 });
      pageCount.value = result.pageCount;
      pageDataUrls.set(1, result.dataUrl);
      sourceUrl.value = result.dataUrl;
    } finally {
      pageLoading.value = false;
    }
  }
}

async function gotoPage(target: number): Promise<void> {
  const next = Math.max(1, Math.min(target, pageCount.value));
  if (next === currentPage.value) return;
  // Page change drops the active marker — sticky is bound to the
  // page where the rectangle was drawn.
  dismissSticky();
  stroke.value = null;
  drafting.value = null;
  currentPage.value = next;

  if (!isPdf.value || !props.pdfUrl) return;

  const cached = pageDataUrls.get(next);
  if (cached) {
    sourceUrl.value = cached;
    return;
  }
  pageLoading.value = true;
  try {
    const { rasterizePdfPage } = await import("../lib/pdf-rasterize");
    const result = await rasterizePdfPage(props.pdfUrl, { page: next, scale: 2 });
    pageDataUrls.set(next, result.dataUrl);
    sourceUrl.value = result.dataUrl;
  } finally {
    pageLoading.value = false;
  }
}

// ── canvas plumbing ────────────────────────────────────────────────

function onImgLoad(): void {
  if (!img.value) return;
  imgNaturalW.value = img.value.naturalWidth || img.value.clientWidth || 800;
  imgNaturalH.value = img.value.naturalHeight || img.value.clientHeight || 600;
  void nextTick(() => {
    if (canvas.value) {
      canvas.value.width = imgNaturalW.value;
      canvas.value.height = imgNaturalH.value;
    }
    redraw();
    repositionSticky();
  });
}

function getCtx(): CanvasRenderingContext2D | null {
  return canvas.value?.getContext("2d") ?? null;
}

function clientToImage(e: PointerEvent): { x: number; y: number } {
  const rect = (canvas.value as HTMLCanvasElement).getBoundingClientRect();
  const sx = imgNaturalW.value / rect.width;
  const sy = imgNaturalH.value / rect.height;
  return {
    x: (e.clientX - rect.left) * sx,
    y: (e.clientY - rect.top) * sy,
  };
}

function imageToClient(p: { x: number; y: number }): { x: number; y: number } {
  const rect = (canvas.value as HTMLCanvasElement).getBoundingClientRect();
  const stageRect = (stage.value as HTMLDivElement).getBoundingClientRect();
  // Sticky widget positions itself within `stage` (offset parent), so
  // translate canvas-local CSS px into stage-local CSS px.
  const sx = rect.width / imgNaturalW.value;
  const sy = rect.height / imgNaturalH.value;
  return {
    x: rect.left - stageRect.left + p.x * sx,
    y: rect.top - stageRect.top + p.y * sy,
  };
}

function onPointerDown(e: PointerEvent): void {
  if (!canvas.value) return;
  (e.target as Element).setPointerCapture?.(e.pointerId);
  const p = clientToImage(e);
  drafting.value = { x1: p.x, y1: p.y, x2: p.x, y2: p.y };
  // Drawing a new rect dismisses any open sticky from a previous
  // attempt — the user is starting over.
  dismissSticky();
  redraw();
}

function onPointerMove(e: PointerEvent): void {
  if (!drafting.value) return;
  const p = clientToImage(e);
  drafting.value.x2 = p.x;
  drafting.value.y2 = p.y;
  redraw();
}

function onPointerUp(): void {
  if (!drafting.value) return;
  const r = drafting.value;
  drafting.value = null;
  if (Math.hypot(r.x2 - r.x1, r.y2 - r.y1) < 4) {
    redraw();
    return; // stray click
  }
  stroke.value = { ...r };
  redraw();
  // Open the sticky note next to the bbox right edge.
  void nextTick(() => {
    repositionSticky();
    stickyOpen.value = true;
    void nextTick(() => stickyTextarea.value?.focus());
  });
}

function repositionSticky(): void {
  if (!stroke.value || !canvas.value) {
    stickyPos.value = null;
    return;
  }
  const r = stroke.value;
  // Anchor at the right edge, slightly above the bbox center, so
  // the user can still see what they marked.
  const anchor = {
    x: Math.max(r.x1, r.x2) + 8,
    y: Math.min(r.y1, r.y2) + 4,
  };
  const css = imageToClient(anchor);
  // Clamp inside the stage rect so the sticky doesn't fall off-screen
  // when the user marks the right edge of the page.
  const stageRect = (stage.value as HTMLDivElement).getBoundingClientRect();
  const noteW = 320;
  const noteH = 220;
  const maxX = stageRect.width - noteW - 12;
  const maxY = stageRect.height - noteH - 12;
  stickyPos.value = {
    x: Math.max(8, Math.min(css.x, maxX)),
    y: Math.max(8, Math.min(css.y, maxY)),
  };
}

function dismissSticky(): void {
  stickyOpen.value = false;
  comment.value = "";
  // Drop extra attachments — they were tied to this in-flight feedback.
  for (const a of extraAttachments.value) {
    if (a.preview) URL.revokeObjectURL(a.preview);
  }
  extraAttachments.value = [];
}

function discardMarker(): void {
  dismissSticky();
  stroke.value = null;
  redraw();
}

function redraw(): void {
  const ctx = getCtx();
  if (!ctx || !canvas.value) return;
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);
  const r = drafting.value || stroke.value;
  if (!r) return;
  // Dark, slightly translucent fill + a sharp dark border. Reads as
  // "highlighted region" without obscuring what's underneath.
  const x = Math.min(r.x1, r.x2);
  const y = Math.min(r.y1, r.y2);
  const w = Math.abs(r.x2 - r.x1);
  const h = Math.abs(r.y2 - r.y1);
  ctx.save();
  ctx.fillStyle = "rgba(15, 23, 42, 0.18)"; // slate-900 @ 18%
  ctx.fillRect(x, y, w, h);
  ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(15, 23, 42, 0.95)";
  ctx.strokeRect(x, y, w, h);
  ctx.restore();
}

// ── extra attachments inside the sticky ────────────────────────────

function _registerExtras(filesArr: File[]): void {
  for (const f of filesArr) {
    const isImage = f.type.startsWith("image/");
    extraAttachments.value.push({
      localId: `xa-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      file: f,
      name: f.name,
      size: f.size,
      mime: f.type || "application/octet-stream",
      preview: isImage ? URL.createObjectURL(f) : undefined,
    });
  }
}

function openFilePicker(): void {
  fileInput.value?.click();
}

function onFilePicked(e: Event): void {
  const t = e.target as HTMLInputElement;
  const list = t.files;
  if (!list || list.length === 0) return;
  _registerExtras(Array.from(list));
  t.value = "";
}

function removeExtra(localId: string): void {
  const idx = extraAttachments.value.findIndex((a) => a.localId === localId);
  if (idx < 0) return;
  const a = extraAttachments.value[idx];
  if (a.preview) URL.revokeObjectURL(a.preview);
  extraAttachments.value.splice(idx, 1);
}

function onStickyPaste(e: ClipboardEvent): void {
  const items = e.clipboardData?.files;
  if (!items || items.length === 0) return;
  e.preventDefault();
  _registerExtras(Array.from(items));
}

function onStickyDrop(e: DragEvent): void {
  if (!e.dataTransfer || e.dataTransfer.files.length === 0) return;
  e.preventDefault();
  _registerExtras(Array.from(e.dataTransfer.files));
}

function onStickyDragOver(e: DragEvent): void {
  if (!e.dataTransfer) return;
  if (Array.from(e.dataTransfer.types).includes("Files")) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }
}

// ── send ───────────────────────────────────────────────────────────

async function send(): Promise<void> {
  if (sending.value) return;
  if (!ws.activeId) {
    ui.toastError("Send feedback", new Error("no active workspace"));
    return;
  }
  if (!stroke.value && !comment.value.trim() && extraAttachments.value.length === 0) {
    ui.toast({ message: "Draw a box, type a comment, or attach a file first.", kind: "info" });
    return;
  }
  sending.value = true;
  try {
    const screenshotFile = await _renderScreenshot();
    const allFiles: File[] = [];
    if (screenshotFile) allFiles.push(screenshotFile);
    for (const a of extraAttachments.value) allFiles.push(a.file);

    let saved: { saved: { name: string; size: number; mime: string; path: string; agent_path: string }[] } = { saved: [] };
    if (allFiles.length > 0) {
      saved = await uploadAttachments(ws.activeId, allFiles);
      chat.addPendingAttachments(
        saved.saved.map((s) => ({
          localId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          name: s.name,
          size: s.size,
          mime: s.mime,
          path: s.path,
          agentPath: s.agent_path,
        })),
      );
      void files.refreshTree();
    }

    // Default comment if user didn't type anything but did mark a region.
    let text = comment.value.trim();
    if (!text) {
      if (screenshotFile) {
        text = isPdf.value
          ? `Please look at the marked region in the attached screenshot of page ${currentPage.value}.`
          : `Please look at the marked region in the attached screenshot.`;
      } else if (allFiles.length > 0) {
        text = "Please look at the attached files.";
      }
    }

    // Fire it through the same path the composer uses, so it queues
    // when pi is busy instead of dropping silently.
    if (chat.isStreaming) {
      chat.enqueueMessage(text);
    } else {
      chat.sendPrompt(text);
    }

    ui.toast({
      message:
        chat.isStreaming
          ? "Feedback queued — pi will see it after the current turn."
          : "Feedback sent.",
      kind: "success",
    });
    emit("sent");
  } catch (exc) {
    ui.toastError("Send feedback", exc);
  } finally {
    sending.value = false;
  }
}

async function _renderScreenshot(): Promise<File | null> {
  if (!img.value) return null;
  const out = document.createElement("canvas");
  out.width = imgNaturalW.value;
  out.height = imgNaturalH.value;
  const ctx = out.getContext("2d");
  if (!ctx) throw new Error("canvas 2d context unavailable");
  ctx.drawImage(img.value, 0, 0, imgNaturalW.value, imgNaturalH.value);
  if (canvas.value) ctx.drawImage(canvas.value, 0, 0);
  const blob: Blob = await new Promise((resolve, reject) => {
    out.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("toBlob returned null"))),
      "image/png",
    );
  });
  const baseNoExt = (filename.value.trim() || props.defaultName)
    .replace(/\.(png|jpg|jpeg)$/i, "") || "feedback";
  const name = isPdf.value && pageCount.value > 1
    ? `${baseNoExt}.p${currentPage.value}.png`
    : `${baseNoExt}.png`;
  return new File([blob], name, { type: "image/png" });
}

// ── keyboard ───────────────────────────────────────────────────────

function onKey(e: KeyboardEvent): void {
  const t = e.target as HTMLElement | null;
  const inField = !!t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);

  // Esc cancels regardless of field focus, but only when the sticky
  // is closed (otherwise Esc inside the textarea should drop the
  // sticky, not the whole modal).
  if (e.key === "Escape") {
    e.preventDefault();
    if (stickyOpen.value) {
      discardMarker();
    } else {
      emit("cancel");
    }
    return;
  }

  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    e.preventDefault();
    void send();
    return;
  }

  if (inField) return;

  if (
    isPdf.value &&
    (e.metaKey || e.ctrlKey) &&
    (e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "PageUp")
  ) {
    e.preventDefault();
    void gotoPage(currentPage.value - 1);
  } else if (
    isPdf.value &&
    (e.metaKey || e.ctrlKey) &&
    (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === "PageDown")
  ) {
    e.preventDefault();
    void gotoPage(currentPage.value + 1);
  }
}

onMounted(() => {
  void loadInitial();
  document.addEventListener("keydown", onKey);
});
onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKey);
  // Clean up any object URLs we created for thumbnails.
  for (const a of extraAttachments.value) {
    if (a.preview) URL.revokeObjectURL(a.preview);
  }
});

watch(
  () => [props.imageUrl, props.pdfUrl],
  () => {
    discardMarker();
    pageDataUrls.clear();
    currentPage.value = 1;
    pageCount.value = 1;
    sourceUrl.value = "";
    void loadInitial();
  },
);

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[80] flex flex-col bg-black/85 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Annotate file"
    >
      <!-- Top bar: title · page nav (PDFs) · cancel -->
      <div class="flex flex-wrap items-center gap-3 border-b border-border bg-popover/95 px-4 py-2 text-sm">
        <Icon icon="codicon:edit" class="h-4 w-4 text-muted-foreground" />
        <span class="font-semibold">Annotate</span>
        <span
          v-if="subtitle"
          class="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted-foreground"
        >{{ subtitle }}</span>

        <div
          v-if="isPdf && pageCount > 1"
          class="flex items-center gap-0.5 rounded border border-border bg-background px-1 py-0.5"
        >
          <button
            type="button"
            class="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
            :disabled="currentPage <= 1 || pageLoading"
            title="Previous page (⌘/Ctrl + ←)"
            @click="gotoPage(currentPage - 1)"
          >
            <Icon icon="codicon:chevron-left" class="h-4 w-4" />
          </button>
          <span class="px-1.5 font-mono text-[11px] tabular-nums">
            <span class="font-semibold">{{ currentPage }}</span>
            <span class="text-muted-foreground"> / {{ pageCount }}</span>
          </span>
          <button
            type="button"
            class="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
            :disabled="currentPage >= pageCount || pageLoading"
            title="Next page (⌘/Ctrl + →)"
            @click="gotoPage(currentPage + 1)"
          >
            <Icon icon="codicon:chevron-right" class="h-4 w-4" />
          </button>
        </div>

        <span class="ml-auto font-mono text-[10px] text-muted-foreground">
          drag a box around what you want feedback on
        </span>
        <button
          type="button"
          class="rounded border border-border bg-background px-2.5 py-1 text-xs font-medium hover:bg-muted"
          title="Cancel (esc)"
          @click="emit('cancel')"
        >Cancel</button>
      </div>

      <!-- Stage: image + overlay canvas + sticky note -->
      <div
        ref="stage"
        class="relative flex flex-1 items-center justify-center overflow-auto bg-[color-mix(in_oklab,var(--editor-bg)_85%,#000)] p-4"
      >
        <div
          v-if="pageLoading"
          class="absolute inset-0 z-20 flex items-center justify-center bg-black/40 text-sm text-muted-foreground"
        >
          <Icon icon="codicon:loading" class="mr-2 h-4 w-4 animate-spin" />
          Loading page {{ currentPage }}…
        </div>

        <div class="relative inline-block max-h-full max-w-full">
          <img
            v-if="sourceUrl"
            ref="img"
            :src="sourceUrl"
            alt="annotation source"
            class="block max-h-[78vh] max-w-[90vw] select-none"
            draggable="false"
            crossorigin="anonymous"
            @load="onImgLoad"
          />
          <canvas
            ref="canvas"
            class="absolute inset-0 h-full w-full touch-none cursor-crosshair"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointercancel="onPointerUp"
            @pointerleave="onPointerUp"
          />
        </div>

        <!-- Sticky-note feedback widget. Lives inside the stage so its
             absolute position is relative to the stage rect.

             Color discipline: the whole popover is monochrome (popover
             bg + border bg + muted-foreground labels) so only the one
             primary action — the green Send button — uses an accent.
             Earlier iterations layered yellow on top of green; the
             user (correctly) called that out as visual noise. -->
        <div
          v-if="stickyOpen && stickyPos"
          class="absolute z-30 w-80 overflow-hidden rounded-md border border-border bg-popover text-foreground shadow-xl"
          :style="{ left: stickyPos.x + 'px', top: stickyPos.y + 'px' }"
          @paste.stop="onStickyPaste"
          @dragover.stop="onStickyDragOver"
          @drop.stop="onStickyDrop"
        >
          <div class="flex items-center justify-between border-b border-border bg-muted/40 px-2.5 py-1.5">
            <span class="font-mono text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Feedback to AI
            </span>
            <button
              type="button"
              class="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              title="Discard (esc)"
              @click="discardMarker"
            >
              <Icon icon="codicon:close" class="h-3.5 w-3.5" />
            </button>
          </div>

          <textarea
            ref="stickyTextarea"
            v-model="comment"
            rows="3"
            placeholder="What should I change here?"
            class="w-full resize-none border-0 bg-transparent px-2.5 py-2 text-sm leading-snug outline-none placeholder:text-muted-foreground"
          />

          <!-- Extra attachment chips. Hidden when none. -->
          <div
            v-if="extraAttachments.length > 0"
            class="flex flex-wrap items-center gap-1 border-t border-border px-2 pb-2 pt-1.5"
          >
            <div
              v-for="a in extraAttachments"
              :key="a.localId"
              class="group inline-flex max-w-[12rem] items-center gap-1 rounded border border-border bg-muted/40 px-1.5 py-0.5 text-[10px]"
              :title="a.name"
            >
              <img
                v-if="a.preview"
                :src="a.preview"
                class="h-5 w-5 shrink-0 rounded-sm object-cover"
                alt=""
              />
              <Icon
                v-else
                :icon="a.mime === 'application/pdf' ? 'codicon:file-pdf' : 'codicon:file'"
                class="h-3.5 w-3.5 shrink-0 text-muted-foreground"
              />
              <span class="truncate text-foreground/80">{{ a.name }}</span>
              <span class="shrink-0 text-muted-foreground">{{ humanSize(a.size) }}</span>
              <button
                type="button"
                class="ml-0.5 rounded-sm p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                :title="`Remove ${a.name}`"
                @click="removeExtra(a.localId)"
              >
                <Icon icon="codicon:close" class="h-3 w-3" />
              </button>
            </div>
          </div>

          <div class="flex items-center gap-1.5 border-t border-border bg-muted/20 px-2 py-1.5">
            <!-- Attach: labelled neutral button (not just an icon)
                 sitting on a darker fill so the paperclip is always
                 visible even when foreground/background tokens are
                 close in some themes. Same area also handles paste +
                 drag-drop on the parent sticky <div>; surfaced as the
                 dim "or paste / drop" label next to it. -->
            <button
              type="button"
              class="flex items-center gap-1 rounded border border-border bg-muted px-1.5 py-1 text-[11px] font-medium text-foreground hover:bg-accent hover:text-accent-foreground"
              title="Click to attach a file. You can also paste images (⌘/Ctrl + V) or drag-drop them onto this note."
              @click="openFilePicker"
            >
              <!-- mdi:paperclip — `codicon:paperclip` doesn't exist in
                   the VS Code Codicons set (iconify renders an empty
                   SVG with no <path>, leaving the button looking
                   invisible). MDI's paperclip is universally
                   available and renders identically at this size. -->
              <Icon icon="mdi:paperclip" class="h-3.5 w-3.5" />
              Attach
            </button>
            <input
              ref="fileInput"
              type="file"
              multiple
              class="hidden"
              @change="onFilePicked"
            />
            <span
              class="hidden font-mono text-[9px] uppercase tracking-wide text-muted-foreground/80 sm:inline"
              title="You can also paste images with ⌘/Ctrl + V or drag-drop files onto this sticky note."
            >or paste / drop</span>
            <button
              type="button"
              :disabled="sending"
              class="ml-auto flex items-center gap-1 rounded bg-success px-3 py-1.5 text-xs font-semibold text-success-foreground hover:bg-success/90 disabled:opacity-50"
              :title="chat.isStreaming ? 'Pi is busy — this will queue (⌘/Ctrl + ↵)' : 'Send (⌘/Ctrl + ↵)'"
              @click="send"
            >
              <Icon
                :icon="sending ? 'codicon:loading' : 'codicon:send'"
                :class="sending && 'animate-spin'"
                class="h-3.5 w-3.5"
              />
              {{ chat.isStreaming ? "Queue" : "Send" }}
            </button>
          </div>
        </div>
      </div>

      <!-- Hint strip. Compact: only the keys that matter for this flow. -->
      <div class="border-t border-border bg-popover/95 px-4 py-1.5 font-mono text-[10px] text-muted-foreground">
        keys · drag = box · ⌘/Ctrl+↵ send · esc dismiss
        <span v-if="isPdf && pageCount > 1">· ⌘/Ctrl+← / → page</span>
      </div>
    </div>
  </Teleport>
</template>
