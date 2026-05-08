<!--
  FilePreview — non-text file viewer used by EditorPane when the open file
  is an image, PDF, SVG, audio or video.

  Image / SVG → wrapped in a `panzoom` instance (anvaka/panzoom):
                  · Trackpad pinch-zoom (Mac touchpad gestures)
                  · Mouse wheel + Ctrl/⌘ wheel zoom (zoom-to-cursor)
                  · Click-and-drag to pan
                  · Toolbar buttons + keyboard shortcuts
                       +  zoom in
                       -  zoom out
                       0  100%
                       F  fit to pane
                  Battle-tested library (used by D3, Observable, etc.).
  PDF        → <iframe> using the browser's built-in PDF.js viewer. Native
                pinch-to-zoom and Ctrl/⌘+wheel zoom inside the iframe work
                via the browser's PDF UI — no custom code can do better.
  Audio      → <audio controls>
  Video      → <video controls>

  All previews fetch via /api/workspaces/{wsid}/files/raw which streams with
  the right Content-Type — nothing is read into JS memory. The store builds
  the URL via `rawFileUrl()` so the active workspace id stays implicit.
-->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Icon } from "@iconify/vue";
import panzoom, { type PanZoom } from "panzoom";

import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

import AnnotateOverlay from "./AnnotateOverlay.vue";

const props = defineProps<{
  path: string;
  kind: "image" | "pdf" | "svg" | "audio" | "video";
  /** For SVG: when true we're showing source code, not the image. */
  showAsCode?: boolean;
}>();

const emit = defineEmits<{
  (e: "toggle-svg-mode", showAsCode: boolean): void;
}>();

const workspace = useWorkspaceStore();
const ui = useUiStore();

// Cache-buster: when the file path changes (or e.g. after a save) we want
// the browser to refetch the bytes instead of using a stale cached copy.
const bust = ref(Date.now());
watch(
  () => props.path,
  () => (bust.value = Date.now()),
);
const rawUrl = computed(() => `${workspace.rawFileUrl(props.path)}&t=${bust.value}`);

// PDF viewer URL fragment.
//   navpanes=0    → collapse the thumbnail sidebar by default.
//   toolbar=1     → keep the built-in zoom / page / search toolbar visible
//                   (it natively supports Ctrl/⌘+scroll zoom inside the
//                   iframe — no custom code can match it).
//   zoom=page-width → fit the PDF to the pane WIDTH on open. Without this
//                   Chrome's default of "auto" often shows the page small
//                   and centred when the pane is narrow, leaving big black
//                   margins on either side.
//   statusbar/messages off → declutter.
// All four are RFC 8118-ish hash params; Chrome/Edge/Firefox honour them.
const pdfUrl = computed(
  () => `${rawUrl.value}#zoom=page-width&navpanes=0&toolbar=1&statusbar=0&messages=0`,
);

// ── panzoom for image / SVG ────────────────────────────────────────────
const stage = ref<HTMLDivElement | null>(null); // viewport (clips)
const subject = ref<HTMLImageElement | null>(null); // the <img> being transformed
let pz: PanZoom | null = null;
const zoomPct = ref(100); // displayed in toolbar

/** True when the panzoom instance exists for the current view (image/svg). */
const isPannable = computed(
  () => props.kind === "image" || (props.kind === "svg" && !props.showAsCode),
);

function fitSubjectToStage(animate = false): void {
  if (!pz || !stage.value || !subject.value) return;
  const s = stage.value.getBoundingClientRect();
  // Use natural size for raster images; for SVGs without a natural size, fall
  // back to the rendered size (panzoom will measure it after layout).
  const w = subject.value.naturalWidth || subject.value.clientWidth || 1;
  const h = subject.value.naturalHeight || subject.value.clientHeight || 1;
  if (s.width <= 0 || s.height <= 0) return;
  const scale = Math.min(s.width / w, s.height / h);
  // Center: translate so the scaled image sits in the middle of the stage.
  const tx = (s.width - w * scale) / 2;
  const ty = (s.height - h * scale) / 2;
  if (animate) {
    pz.smoothZoomAbs(0, 0, scale);
    pz.moveTo(tx, ty);
  } else {
    pz.zoomAbs(0, 0, scale);
    pz.moveTo(tx, ty);
  }
  zoomPct.value = Math.round(scale * 100);
}

function zoomBy(factor: number): void {
  if (!pz || !stage.value) return;
  const s = stage.value.getBoundingClientRect();
  pz.smoothZoom(s.width / 2, s.height / 2, factor);
}

function zoomToActual(): void {
  if (!pz || !stage.value || !subject.value) return;
  // Centre the natural-size image in the viewport.
  const s = stage.value.getBoundingClientRect();
  const w = subject.value.naturalWidth || subject.value.clientWidth || 1;
  const h = subject.value.naturalHeight || subject.value.clientHeight || 1;
  pz.zoomAbs(0, 0, 1);
  pz.moveTo((s.width - w) / 2, (s.height - h) / 2);
  zoomPct.value = 100;
}

function destroyPanzoom(): void {
  if (pz) {
    pz.dispose();
    pz = null;
  }
}

async function setupPanzoom(): Promise<void> {
  destroyPanzoom();
  await nextTick();
  if (!isPannable.value || !subject.value) return;

  pz = panzoom(subject.value, {
    // Sensible bounds — beyond these the image is either invisible or 50× the viewport.
    minZoom: 0.05,
    maxZoom: 50,
    // Wheel/trackpad zoom sensitivity. The library default of 0.065
    // and our previous 0.08 felt sluggish — many wheel ticks needed for
    // any visible change. 0.2 gives roughly macOS Preview-level
    // responsiveness: a single wheel notch ≈ 10–15% zoom change, a
    // two-finger pinch swipe takes the image from "fit" to ~3× quickly.
    zoomSpeed: 0.2,
    // Pinch on touchscreens (separate code path from trackpad pinch,
    // which fires synthetic wheel events). Default 1 is fine.
    pinchSpeed: 1,
    // Avoid inertia-after-release: causes the image to drift after the user
    // stops dragging, which feels wrong for a code editor preview.
    smoothScroll: false,
    // Allow text selection in SVG/HTML subjects to be disabled on drag.
    enableTextSelection: false,
  });

  // Track the displayed zoom percentage live so the toolbar % updates.
  pz.on("zoom", () => {
    if (pz) zoomPct.value = Math.round(pz.getTransform().scale * 100);
  });

  // Wait for the image to actually be loaded so we can fit-to-stage with
  // the right intrinsic dimensions.
  if (subject.value.complete) {
    fitSubjectToStage(false);
  } else {
    subject.value.addEventListener("load", () => fitSubjectToStage(false), {
      once: true,
    });
  }
}

onMounted(setupPanzoom);
onBeforeUnmount(destroyPanzoom);

// Whenever the file changes OR we toggle SVG code/image mode, rebuild
// the panzoom instance against the new <img> element.
watch(
  () => [props.path, props.kind, props.showAsCode] as const,
  () => {
    setupPanzoom();
  },
);

// Re-fit when the host pane is resized (the user dragged the splitter).
const ro = new ResizeObserver(() => {
  // Only auto-refit when we're at the previously-fit zoom; if the user
  // has zoomed in manually we must NOT yank them back.
  // Heuristic: if zoom is within 2% of the current "fit" scale, refit.
  if (!pz || !stage.value || !subject.value) return;
  const s = stage.value.getBoundingClientRect();
  const w = subject.value.naturalWidth || 1;
  const h = subject.value.naturalHeight || 1;
  const fitScale = Math.min(s.width / w, s.height / h);
  const cur = pz.getTransform().scale;
  if (Math.abs(cur - fitScale) / fitScale < 0.02) {
    fitSubjectToStage(false);
  }
});
onMounted(() => {
  if (stage.value) ro.observe(stage.value);
});
onBeforeUnmount(() => ro.disconnect());

// ── Keyboard shortcuts ─────────────────────────────────────────────────
function onKeydown(ev: KeyboardEvent): void {
  if (!isPannable.value) return;
  // Only react when the preview is visually focused-ish: skip if user is
  // typing in an input/textarea anywhere.
  const t = ev.target as HTMLElement | null;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
    return;
  }
  if (ev.key === "+" || ev.key === "=") {
    ev.preventDefault();
    zoomBy(1.25);
  } else if (ev.key === "-" || ev.key === "_") {
    ev.preventDefault();
    zoomBy(0.8);
  } else if (ev.key === "0") {
    ev.preventDefault();
    zoomToActual();
  } else if (ev.key === "f" || ev.key === "F") {
    ev.preventDefault();
    fitSubjectToStage(true);
  }
}
onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

function toggleSvgMode(): void {
  emit("toggle-svg-mode", !props.showAsCode);
}

// ── Annotate / send-feedback ────────────────────────────────────────────
//
// Clicking "Annotate" opens a full-screen modal where the user drags one
// rectangle around what they want feedback on. A sticky-note pops up
// next to the box for the comment + extra attachments (paperclip, paste,
// drop). Hitting Send inside the modal does everything: composites the
// screenshot, uploads it (and any extras) into workspace/uploads/, drops
// the agent paths into the composer's pendingAttachments, and fires the
// comment as a chat message (or queues it if pi is busy). All this
// component does is wire the open/close lifecycle.
const annotateOpen = ref(false);
const annotateImageUrl = ref<string | null>(null);
const annotatePdfUrl = ref<string | null>(null);
const annotateSubtitle = ref<string | undefined>(undefined);
const annotateDefaultName = ref<string>("annotation.png");

const canAnnotate = computed(
  () =>
    props.kind === "image" ||
    (props.kind === "svg" && !props.showAsCode) ||
    props.kind === "pdf",
);

function _baseName(p: string): string {
  const last = p.split("/").pop() || "annotation";
  return last.replace(/\.[^.]+$/, "").replace(/\s+/g, "_");
}

function startAnnotate(): void {
  if (!workspace.activeId) {
    ui.toastError("Annotate", new Error("no active workspace"));
    return;
  }
  const base = _baseName(props.path);
  if (props.kind === "pdf") {
    annotatePdfUrl.value = rawUrl.value;
    annotateImageUrl.value = null;
    annotateSubtitle.value = "PDF";
  } else {
    annotateImageUrl.value = rawUrl.value;
    annotatePdfUrl.value = null;
    annotateSubtitle.value = props.kind;
  }
  annotateDefaultName.value = `${base}.annot`;
  annotateOpen.value = true;
}

function onAnnotateSent(): void {
  annotateOpen.value = false;
}

function onAnnotateCancel(): void {
  annotateOpen.value = false;
}
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col bg-editor">
    <!-- PDF info bar — the actual zoom controls live INSIDE the PDF.js
         viewer (browser-native), but users don't always realise that.
         Surface the keyboard shortcut up here so they don't keep trying
         to scroll-zoom an iframe that only zooms with Ctrl/⌘. -->
    <div
      v-if="kind === 'pdf'"
      class="flex items-center justify-between border-b border-border bg-card/40 px-3 py-1 text-xs text-muted-foreground"
    >
      <div class="flex items-center gap-2 font-mono">
        <Icon icon="material-icon-theme:pdf" class="h-[14px] w-[14px]" />
        <span>PDF preview</span>
        <span class="text-[10px] opacity-60">· toolbar inside viewer · Ctrl/⌘ + scroll to zoom</span>
      </div>
      <button
        type="button"
        class="flex items-center gap-1 rounded border border-border bg-background px-2 py-0.5 text-[11px] font-medium hover:border-warning/40 hover:bg-warning/10 hover:text-warning"
        title="Mark up any page of this PDF and attach to your next message"
        @click="startAnnotate"
      >
        <Icon icon="codicon:edit" class="h-3.5 w-3.5" />
        Annotate
      </button>
    </div>

    <!-- Toolbar (zoom + svg toggle for images / svg) -->
    <div
      v-if="kind === 'image' || kind === 'svg'"
      class="flex items-center justify-between border-b border-border bg-card/40 px-3 py-1 text-xs text-muted-foreground"
    >
      <div class="flex items-center gap-2 font-mono">
        <Icon
          :icon="kind === 'svg' ? 'material-icon-theme:svg' : 'material-icon-theme:image'"
          class="h-[14px] w-[14px]"
        />
        <span>{{ kind === "svg" ? "SVG preview" : "image preview" }}</span>
        <span class="text-[10px] opacity-60">· scroll = zoom · drag = pan · 0/F = reset</span>
      </div>
      <div class="flex items-center gap-0.5">
        <button
          v-if="canAnnotate"
          type="button"
          class="mr-2 flex items-center gap-1 rounded-sm border border-border bg-background px-1.5 py-0.5 text-[11px] font-medium hover:border-warning/40 hover:bg-warning/10 hover:text-warning"
          title="Mark up this file and attach to your next message"
          @click="startAnnotate"
        >
          <Icon icon="codicon:edit" class="h-3 w-3" />
          Annotate
        </button>
        <button
          v-if="kind === 'svg'"
          type="button"
          :class="[
            'mr-2 rounded-sm border px-1.5 py-0.5 font-mono text-[10px] transition-colors',
            showAsCode
              ? 'border-primary/50 bg-primary/10 text-primary'
              : 'border-border bg-background text-muted-foreground hover:bg-accent',
          ]"
          :title="showAsCode ? 'Currently showing source code. Click to view rendered.' : 'Currently showing rendered SVG. Click to view source code.'"
          @click="toggleSvgMode"
        >{{ showAsCode ? "code" : "</> code" }}</button>
        <button
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-sm hover:bg-accent hover:text-foreground"
          title="Zoom out (-)"
          @click="zoomBy(0.8)"
        >
          <Icon icon="codicon:zoom-out" class="h-[14px] w-[14px]" />
        </button>
        <button
          type="button"
          class="flex min-w-[3.5rem] items-center justify-center rounded-sm px-1 font-mono text-[11px] tabular-nums hover:bg-accent hover:text-foreground"
          title="Click to reset to 100% (0)"
          @click="zoomToActual"
        >{{ zoomPct }}%</button>
        <button
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-sm hover:bg-accent hover:text-foreground"
          title="Zoom in (+)"
          @click="zoomBy(1.25)"
        >
          <Icon icon="codicon:zoom-in" class="h-[14px] w-[14px]" />
        </button>
        <button
          type="button"
          class="ml-1 flex h-6 w-6 items-center justify-center rounded-sm hover:bg-accent hover:text-foreground"
          title="Fit to pane (F)"
          @click="fitSubjectToStage(true)"
        >
          <Icon icon="codicon:screen-normal" class="h-[14px] w-[14px]" />
        </button>
      </div>
    </div>

    <!-- BODY -->
    <div
      ref="stage"
      class="preview-stage relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-[color-mix(in_oklab,var(--editor-bg)_90%,#000)]"
      :class="{ 'is-pannable': isPannable }"
    >
      <!-- Image (also SVG when not showing as code).
           panzoom transforms the <img> inside the absolutely-positioned
           wrapper; using `position:absolute` on the img lets the library
           freely translate without flex layout fighting it. -->
      <img
        v-if="kind === 'image' || (kind === 'svg' && !showAsCode)"
        ref="subject"
        :src="rawUrl"
        :alt="path"
        draggable="false"
        class="preview-img"
      />

      <!-- PDF — browser's built-in PDF viewer.
           Native trackpad pinch and Ctrl/⌘+wheel zoom work inside the iframe. -->
      <iframe
        v-else-if="kind === 'pdf'"
        :src="pdfUrl"
        class="h-full w-full border-0"
        :title="path"
      ></iframe>

      <!-- Audio -->
      <audio
        v-else-if="kind === 'audio'"
        :src="rawUrl"
        controls
        class="w-full max-w-2xl"
      ></audio>

      <!-- Video -->
      <video
        v-else-if="kind === 'video'"
        :src="rawUrl"
        controls
        class="max-h-full max-w-full"
      ></video>
    </div>

    <!-- Annotation overlay (modal). Only rendered when active so the
         heavy canvas + pdfjs runtime aren't paid for on every preview. -->
    <AnnotateOverlay
      v-if="annotateOpen"
      :image-url="annotateImageUrl ?? undefined"
      :pdf-url="annotatePdfUrl ?? undefined"
      :default-name="annotateDefaultName"
      :subtitle="annotateSubtitle"
      @sent="onAnnotateSent"
      @cancel="onAnnotateCancel"
    />
  </div>
</template>

<style scoped>
.preview-stage {
  /* panzoom drags by mousedown; show the right cursor so it's discoverable. */
  cursor: default;
}
.preview-stage.is-pannable {
  cursor: grab;
}
.preview-stage.is-pannable:active {
  cursor: grabbing;
}

/* The image must be free-floating so panzoom's translate3d() works without
   being snapped to flex centering on every transform. We size it to its
   natural dimensions; fit-to-stage applies a transform to scale it down. */
.preview-img {
  position: absolute;
  top: 0;
  left: 0;
  user-select: none;
  /* The library applies will-change/transform-origin itself. */
  max-width: none;
  max-height: none;
}
</style>
