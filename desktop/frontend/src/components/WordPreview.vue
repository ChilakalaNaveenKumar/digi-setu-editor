<!--
  WordPreview — visual DOCX viewer.

  Uses the `docx-preview` library to parse a DOCX file in-browser and
  render it as styled HTML inside a container div. The output preserves
  fonts, paragraph styles, headings, lists, tables, and inline images.
  Same fidelity as Word's web preview.

  We don't try to support legacy `.doc` here — that format is binary and
  poorly supported in JS. Files with .doc / .odt / .rtf still fall
  through to the markitdown text view via the legacy `office` kind.
-->

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { Icon } from "@iconify/vue";
import { renderAsync } from "docx-preview";

import { downloadFile, rawFileBytes } from "../api/files";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

const props = defineProps<{
  path: string;
}>();

const workspace = useWorkspaceStore();
const ui = useUiStore();

const loading = ref(false);
const error = ref<string | null>(null);
const container = ref<HTMLDivElement | null>(null);

async function _load(): Promise<void> {
  if (!workspace.activeId) return;
  loading.value = true;
  error.value = null;
  await nextTick();
  if (!container.value) {
    loading.value = false;
    return;
  }
  // Wipe any prior render so a fast subsequent file switch can't leave
  // stale content visible behind the loading spinner.
  container.value.innerHTML = "";
  try {
    const buf = await rawFileBytes(workspace.activeId, props.path);
    const blob = new Blob([buf], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    await renderAsync(blob, container.value, undefined, {
      // Preserve the original page layout (margins, page size). Without
      // this docx-preview falls back to a plain flow which loses the
      // "looks like Word" feel.
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
      ignoreFonts: false,
      breakPages: true,
      experimental: false,
      trimXmlDeclaration: true,
      // Class prefix lets us target the rendered nodes from our scoped
      // CSS without leaking styles to the rest of the app.
      className: "docx-rendered",
    });
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

watch(() => props.path, _load, { immediate: true });

const downloading = ref(false);
async function _download(): Promise<void> {
  if (!workspace.activeId) return;
  downloading.value = true;
  try {
    await downloadFile(workspace.activeId, props.path);
  } catch (exc) {
    ui.toastError("Download", exc instanceof Error ? exc : new Error(String(exc)));
  } finally {
    downloading.value = false;
  }
}

onBeforeUnmount(() => {
  if (container.value) container.value.innerHTML = "";
});
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col bg-editor">
    <div
      class="flex items-center justify-between border-b border-border bg-card/40 px-3 py-1 text-body text-muted-foreground"
    >
      <div class="flex items-center gap-2 font-mono">
        <Icon icon="material-icon-theme:word" class="h-[14px] w-[14px]" />
        <span>Word document preview</span>
      </div>
      <button
        type="button"
        class="flex items-center gap-1 rounded border border-border bg-background px-2 py-0.5 text-caption font-medium hover:border-primary/40 hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="downloading"
        title="Download the original DOCX"
        @click="_download"
      >
        <Icon
          :icon="downloading ? 'codicon:loading' : 'codicon:cloud-download'"
          :class="downloading && 'animate-spin'"
          class="h-3.5 w-3.5"
        />
        Download
      </button>
    </div>

    <div class="relative flex min-h-0 flex-1 overflow-auto bg-[color-mix(in_oklab,var(--background)_80%,#000)]">
      <div
        v-if="loading"
        class="flex flex-1 flex-col items-center justify-center gap-2 text-body text-muted-foreground"
      >
        <Icon icon="codicon:loading" class="h-5 w-5 animate-spin" />
        <span>Rendering document…</span>
      </div>
      <div
        v-else-if="error"
        class="m-6 max-w-prose rounded-md border border-destructive/30 bg-destructive/5 p-4 text-body text-destructive"
      >
        <p class="mb-2 font-semibold">Couldn't render this Word document</p>
        <p class="font-mono text-caption">{{ error }}</p>
        <p class="mt-2 text-muted-foreground">
          You can still <button class="underline" @click="_download">download the original</button>
          and open it in Word.
        </p>
      </div>
      <div ref="container" class="docx-host w-full"></div>
    </div>
  </div>
</template>

<style scoped>
/* docx-preview renders a single .docx-wrapper ancestor that we centre
   on a dark page background — matches Word's "page on grey desk" UX. */
.docx-host :deep(.docx-wrapper) {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  gap: 1rem;
  background: transparent;
}
.docx-host :deep(.docx) {
  background: white;
  color: #111;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
}
</style>
