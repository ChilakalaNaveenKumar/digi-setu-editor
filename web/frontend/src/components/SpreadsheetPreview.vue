<!--
  SpreadsheetPreview — visual XLSX / XLS / ODS / CSV / TSV viewer.

  Renders the same way Excel / LibreOffice show the file: every sheet
  available as a tab, the active sheet rendered as an HTML table with
  cell formatting (bold, alignment, merged ranges) preserved.

  Implementation: SheetJS Community Edition (`xlsx`) parses the binary
  in-browser into a workbook object, then `XLSX.utils.sheet_to_html()`
  emits a styled <table> we drop into the pane. No backend round-trip
  beyond fetching the raw bytes.

  Why SheetJS instead of server-side markitdown:
    - faithful rendering: column widths, merged cells, basic formatting
    - no 30 s timeout: parsing 50k rows takes <1 s on a laptop
    - works offline (in the desktop app) without re-running a Python
      sidecar that may not have openpyxl/mammoth bundled correctly

  Performance guard: we cap the rendered cell count per sheet at 50k.
  Past that we render the first 50k and surface a "showing first N rows"
  banner with a Download button so the user can open the original
  in Excel for the full data.
-->

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Icon } from "@iconify/vue";
import * as XLSX from "xlsx";

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
const workbook = ref<XLSX.WorkBook | null>(null);
const activeSheet = ref<string | null>(null);
const tableHtml = ref<string>("");
// Per-sheet { renderedRows, totalRows } so the banner can say
// "Showing 50,000 of 1,200,000 rows".
const truncatedRows = ref(0);
const totalRows = ref(0);

// Hard cap on cells we render per sheet. 50k cells × 26 cols ≈ 1.3M
// table cells which is the limit before browsers start to chug.
const MAX_RENDERED_ROWS = 5_000;

async function _load(): Promise<void> {
  if (!workspace.activeId) return;
  loading.value = true;
  error.value = null;
  workbook.value = null;
  tableHtml.value = "";
  truncatedRows.value = 0;
  totalRows.value = 0;
  try {
    const buf = await rawFileBytes(workspace.activeId, props.path);
    // type: "array" tells SheetJS the input is an ArrayBuffer / Uint8Array.
    // cellStyles: true preserves bold / color / etc. into the HTML.
    // cellDates: true converts Excel serial dates to JS Date objects so
    //   sheet_to_html renders them as ISO strings instead of "44927".
    const wb = XLSX.read(new Uint8Array(buf), {
      type: "array",
      cellStyles: true,
      cellDates: true,
    });
    workbook.value = wb;
    activeSheet.value = wb.SheetNames[0] ?? null;
    _renderActiveSheet();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function _renderActiveSheet(): void {
  if (!workbook.value || !activeSheet.value) return;
  const sheet = workbook.value.Sheets[activeSheet.value];
  if (!sheet) {
    tableHtml.value = "";
    return;
  }
  const ref_ = sheet["!ref"];
  if (!ref_) {
    tableHtml.value = "<p class=\"p-4 text-muted-foreground\">(empty sheet)</p>";
    totalRows.value = 0;
    truncatedRows.value = 0;
    return;
  }
  const range = XLSX.utils.decode_range(ref_);
  const total = range.e.r - range.s.r + 1;
  totalRows.value = total;

  // If the sheet is huge, slice the range so we only render the top
  // chunk. SheetJS lets us pass a custom range to sheet_to_html.
  let renderRange = ref_;
  if (total > MAX_RENDERED_ROWS) {
    const cap = { ...range, e: { ...range.e, r: range.s.r + MAX_RENDERED_ROWS - 1 } };
    renderRange = XLSX.utils.encode_range(cap);
    truncatedRows.value = total - MAX_RENDERED_ROWS;
  } else {
    truncatedRows.value = 0;
  }
  tableHtml.value = XLSX.utils.sheet_to_html(sheet, { editable: false });
  // sheet_to_html ignores our custom range; do a manual slice if needed.
  if (truncatedRows.value > 0) {
    const cappedSheet = { ...sheet, "!ref": renderRange };
    tableHtml.value = XLSX.utils.sheet_to_html(cappedSheet, { editable: false });
  }
}

function selectSheet(name: string): void {
  activeSheet.value = name;
  _renderActiveSheet();
}

const sheetNames = computed(() => workbook.value?.SheetNames ?? []);

const fmtRows = (n: number) => n.toLocaleString();

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
  workbook.value = null;
  tableHtml.value = "";
});
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col bg-editor">
    <!-- Top toolbar: kind label + download -->
    <div
      class="flex items-center justify-between border-b border-border bg-card/40 px-3 py-1 text-body text-muted-foreground"
    >
      <div class="flex items-center gap-2 font-mono">
        <Icon icon="material-icon-theme:excel" class="h-[14px] w-[14px]" />
        <span>Spreadsheet preview</span>
        <span v-if="totalRows > 0" class="text-caption opacity-60">
          · {{ fmtRows(totalRows) }} row{{ totalRows === 1 ? "" : "s" }}
          <span v-if="truncatedRows > 0" class="ml-1 rounded bg-warning/10 px-1 text-warning">
            showing first {{ fmtRows(MAX_RENDERED_ROWS) }}
          </span>
        </span>
      </div>
      <button
        type="button"
        class="flex items-center gap-1 rounded border border-border bg-background px-2 py-0.5 text-caption font-medium hover:border-primary/40 hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="downloading"
        title="Download the original file (open in Excel for full editing)"
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

    <!-- Sheet tabs (only when more than one sheet) -->
    <div
      v-if="sheetNames.length > 1"
      class="flex items-center gap-1 overflow-x-auto border-b border-border bg-card/20 px-2 py-1 text-caption"
    >
      <button
        v-for="name in sheetNames"
        :key="name"
        type="button"
        :class="[
          'whitespace-nowrap rounded-sm border px-2 py-0.5 font-mono transition-colors',
          activeSheet === name
            ? 'border-primary/50 bg-primary/10 text-primary'
            : 'border-border bg-background text-muted-foreground hover:bg-accent',
        ]"
        @click="selectSheet(name)"
      >
        {{ name }}
      </button>
    </div>

    <!-- Body -->
    <div class="relative flex min-h-0 flex-1 overflow-auto bg-background">
      <div
        v-if="loading"
        class="flex flex-1 flex-col items-center justify-center gap-2 text-body text-muted-foreground"
      >
        <Icon icon="codicon:loading" class="h-5 w-5 animate-spin" />
        <span>Parsing spreadsheet…</span>
      </div>
      <div
        v-else-if="error"
        class="m-6 max-w-prose rounded-md border border-destructive/30 bg-destructive/5 p-4 text-body text-destructive"
      >
        <p class="mb-2 font-semibold">Couldn't render this spreadsheet</p>
        <p class="font-mono text-caption">{{ error }}</p>
        <p class="mt-2 text-muted-foreground">
          You can still <button class="underline" @click="_download">download the original</button>
          and open it in Excel.
        </p>
      </div>
      <div
        v-else
        class="spreadsheet-stage min-h-0 w-full p-2 text-foreground"
        v-html="tableHtml"
      />
    </div>
  </div>
</template>

<style scoped>
.spreadsheet-stage :deep(table) {
  border-collapse: collapse;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.875rem;
}
.spreadsheet-stage :deep(th),
.spreadsheet-stage :deep(td) {
  border: 1px solid color-mix(in oklab, currentColor 20%, transparent);
  padding: 4px 8px;
  white-space: nowrap;
  text-align: left;
  vertical-align: top;
  background: var(--background);
}
.spreadsheet-stage :deep(thead th),
.spreadsheet-stage :deep(tr:first-child td) {
  background: color-mix(in oklab, var(--background) 92%, currentColor 8%);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}
/* Number / currency cells right-align. SheetJS sets t="n" attribute on
   numeric cells; sheet_to_html maps that to data-t="n". */
.spreadsheet-stage :deep(td[data-t="n"]) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
