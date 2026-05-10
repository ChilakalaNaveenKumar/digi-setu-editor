<!--
  SqlitePreview — visual SQLite database browser.

  Opens a `.db` / `.sqlite` / `.sqlite3` file in the browser using
  sql.js (SQLite compiled to WebAssembly), lists every user table /
  view in the schema, and renders the first N rows of the selected
  table as a sortable HTML grid. A free-form SQL editor at the bottom
  lets the user run read-only SELECTs.

  We intentionally do NOT support writes from this preview pane: the
  file lives inside a workspace + the AI tool surface is the proper
  way to mutate it. Any user query that doesn't start with a SELECT
  / WITH / EXPLAIN / PRAGMA gets rejected client-side.

  WASM lifecycle: sql.js needs the `.wasm` blob alongside the JS. We
  let Vite resolve `sql-wasm.wasm?url` so the asset is hashed and
  served as a static file — works in dev (`vite serve`), prod build
  (`vite build`), and the Tauri-packaged frontend.
-->

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { Icon } from "@iconify/vue";

import { downloadFile, rawFileBytes } from "../api/files";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";

// Vite resolves the wasm to a hashed asset URL the SPA can fetch from
// its own origin — no CDN dependency, works offline in the desktop
// shell.
import sqlWasmUrl from "sql.js/dist/sql-wasm.wasm?url";

// Lazy import keeps the ~200 KB sql.js JS off the initial bundle when
// the user never opens a .db file. We reach into the namespace type
// (instead of `typeof import("sql.js")`) because the package's default
// export is a function that returns a `SqlJsStatic` — the namespace
// also re-exports the `Database` class type for callers like us.
import type initSqlJs from "sql.js";
type Database = InstanceType<initSqlJs.SqlJsStatic["Database"]>;

const props = defineProps<{
  path: string;
}>();

const workspace = useWorkspaceStore();
const ui = useUiStore();

const loading = ref(false);
const error = ref<string | null>(null);
const tables = ref<string[]>([]);
const activeTable = ref<string | null>(null);
const headers = ref<string[]>([]);
const rows = ref<unknown[][]>([]);
const totalRows = ref<number>(0);
const queryText = ref<string>("");
const queryError = ref<string | null>(null);

let _db: Database | null = null;

const PREVIEW_ROW_CAP = 200;

async function _load(): Promise<void> {
  if (!workspace.activeId) return;
  loading.value = true;
  error.value = null;
  tables.value = [];
  activeTable.value = null;
  headers.value = [];
  rows.value = [];
  totalRows.value = 0;
  queryError.value = null;

  try {
    const [{ default: initSqlJs }, buf] = await Promise.all([
      import("sql.js"),
      rawFileBytes(workspace.activeId, props.path),
    ]);
    const SQL = await initSqlJs({ locateFile: () => sqlWasmUrl });
    if (_db) {
      try { _db.close(); } catch { /* ignore */ }
      _db = null;
    }
    _db = new SQL.Database(new Uint8Array(buf));

    // List user tables + views, skipping sqlite_*-prefixed bookkeeping.
    const stmt = _db.prepare(
      "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
    );
    const names: string[] = [];
    while (stmt.step()) {
      const r = stmt.getAsObject();
      if (typeof r.name === "string") names.push(r.name);
    }
    stmt.free();
    tables.value = names;
    if (names.length > 0) selectTable(names[0]);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function _quoteIdent(name: string): string {
  // Defensive: SQLite identifiers can contain quotes. Escape ".
  return `"${name.replace(/"/g, '""')}"`;
}

function selectTable(name: string): void {
  if (!_db) return;
  activeTable.value = name;
  queryError.value = null;
  try {
    // Total row count first (cheap on indexed tables, slow on huge
    // unindexed ones — acceptable for a preview pane).
    const cstmt = _db.prepare(`SELECT COUNT(*) AS n FROM ${_quoteIdent(name)}`);
    cstmt.step();
    const cobj = cstmt.getAsObject() as { n?: number };
    totalRows.value = typeof cobj.n === "number" ? cobj.n : 0;
    cstmt.free();

    const stmt = _db.prepare(`SELECT * FROM ${_quoteIdent(name)} LIMIT ${PREVIEW_ROW_CAP}`);
    const cols: string[] = [];
    const data: unknown[][] = [];
    let firstRow = true;
    while (stmt.step()) {
      if (firstRow) {
        cols.push(...stmt.getColumnNames());
        firstRow = false;
      }
      data.push(stmt.get());
    }
    if (firstRow) {
      // Empty table — still want column headers via PRAGMA.
      const pstmt = _db.prepare(`PRAGMA table_info(${_quoteIdent(name)})`);
      while (pstmt.step()) {
        const obj = pstmt.getAsObject() as { name?: string };
        if (typeof obj.name === "string") cols.push(obj.name);
      }
      pstmt.free();
    }
    stmt.free();
    headers.value = cols;
    rows.value = data;
    queryText.value = `SELECT * FROM ${_quoteIdent(name)} LIMIT 100;`;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}

function runQuery(): void {
  if (!_db) return;
  const q = queryText.value.trim();
  queryError.value = null;
  if (!q) return;
  // Read-only guard: only allow statements that can't mutate state.
  const head = q.split(/\s+/, 1)[0]?.toUpperCase() ?? "";
  if (!["SELECT", "WITH", "EXPLAIN", "PRAGMA"].includes(head)) {
    queryError.value = "Only SELECT / WITH / EXPLAIN / PRAGMA queries are allowed in the preview pane.";
    return;
  }
  try {
    const stmt = _db.prepare(q);
    const cols: string[] = [];
    const data: unknown[][] = [];
    let firstRow = true;
    while (stmt.step()) {
      if (firstRow) {
        cols.push(...stmt.getColumnNames());
        firstRow = false;
      }
      data.push(stmt.get());
    }
    if (firstRow) {
      // No rows — still try to grab column names for PRAGMA / EXPLAIN.
      cols.push(...stmt.getColumnNames());
    }
    stmt.free();
    headers.value = cols;
    rows.value = data;
    activeTable.value = null;
    totalRows.value = data.length;
  } catch (exc) {
    queryError.value = exc instanceof Error ? exc.message : String(exc);
  }
}

function fmtCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (v instanceof Uint8Array) return `<BLOB ${v.length} bytes>`;
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

const fmtRows = (n: number) => n.toLocaleString();

watch(() => props.path, _load, { immediate: true });

onBeforeUnmount(() => {
  if (_db) {
    try { _db.close(); } catch { /* ignore */ }
    _db = null;
  }
});

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
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col bg-editor">
    <!-- Toolbar -->
    <div
      class="flex items-center justify-between border-b border-border bg-card/40 px-3 py-1 text-body text-muted-foreground"
    >
      <div class="flex items-center gap-2 font-mono">
        <Icon icon="material-icon-theme:database" class="h-[14px] w-[14px]" />
        <span>SQLite database</span>
        <span v-if="activeTable && totalRows" class="text-caption opacity-60">
          · {{ activeTable }} · {{ fmtRows(totalRows) }} row{{ totalRows === 1 ? "" : "s" }}
          <span v-if="totalRows > rows.length" class="ml-1 rounded bg-warning/10 px-1 text-warning">
            showing first {{ fmtRows(rows.length) }}
          </span>
        </span>
      </div>
      <button
        type="button"
        class="flex items-center gap-1 rounded border border-border bg-background px-2 py-0.5 text-caption font-medium hover:border-primary/40 hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="downloading"
        title="Download the .db file"
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

    <!-- Table tabs -->
    <div
      v-if="tables.length > 0"
      class="flex items-center gap-1 overflow-x-auto border-b border-border bg-card/20 px-2 py-1 text-caption"
    >
      <button
        v-for="name in tables"
        :key="name"
        type="button"
        :class="[
          'whitespace-nowrap rounded-sm border px-2 py-0.5 font-mono transition-colors',
          activeTable === name
            ? 'border-primary/50 bg-primary/10 text-primary'
            : 'border-border bg-background text-muted-foreground hover:bg-accent',
        ]"
        @click="selectTable(name)"
      >
        {{ name }}
      </button>
    </div>

    <!-- Body: results grid + SQL editor -->
    <div class="flex min-h-0 flex-1 flex-col">
      <!-- Loading / error -->
      <div
        v-if="loading"
        class="flex flex-1 flex-col items-center justify-center gap-2 text-body text-muted-foreground"
      >
        <Icon icon="codicon:loading" class="h-5 w-5 animate-spin" />
        <span>Opening database…</span>
      </div>
      <div
        v-else-if="error"
        class="m-6 max-w-prose rounded-md border border-destructive/30 bg-destructive/5 p-4 text-body text-destructive"
      >
        <p class="mb-2 font-semibold">Couldn't open this database</p>
        <p class="font-mono text-caption">{{ error }}</p>
        <p class="mt-2 text-muted-foreground">
          You can still <button class="underline" @click="_download">download the file</button>
          and open it in DB Browser for SQLite.
        </p>
      </div>
      <template v-else>
        <!-- Grid -->
        <div class="min-h-0 flex-1 overflow-auto bg-background">
          <div v-if="tables.length === 0" class="p-6 text-body text-muted-foreground">
            This database has no user tables or views.
          </div>
          <table v-else class="sqlite-grid">
            <thead>
              <tr>
                <th v-for="h in headers" :key="h">{{ h }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in rows" :key="idx">
                <td v-for="(cell, ci) in row" :key="ci">{{ fmtCell(cell) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- SQL editor (read-only queries) -->
        <div class="border-t border-border bg-card/30 p-2">
          <div class="mb-1 flex items-center justify-between text-caption text-muted-foreground">
            <span class="font-mono">SQL preview · SELECT / WITH / EXPLAIN / PRAGMA only</span>
            <button
              type="button"
              class="rounded border border-primary/40 bg-primary/10 px-2 py-0.5 font-mono text-caption text-primary hover:bg-primary/20"
              @click="runQuery"
            >Run</button>
          </div>
          <textarea
            v-model="queryText"
            class="h-20 w-full resize-none rounded border border-border bg-background px-2 py-1 font-mono text-caption text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            spellcheck="false"
            @keydown.ctrl.enter.prevent="runQuery"
            @keydown.meta.enter.prevent="runQuery"
          ></textarea>
          <p
            v-if="queryError"
            class="mt-1 font-mono text-caption text-destructive"
          >{{ queryError }}</p>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.sqlite-grid {
  border-collapse: collapse;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8125rem;
  width: max-content;
  min-width: 100%;
}
.sqlite-grid th,
.sqlite-grid td {
  border: 1px solid color-mix(in oklab, currentColor 18%, transparent);
  padding: 4px 8px;
  vertical-align: top;
  white-space: nowrap;
  text-align: left;
  background: var(--background);
}
.sqlite-grid thead th {
  background: color-mix(in oklab, var(--background) 90%, currentColor 10%);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}
.sqlite-grid tbody tr:nth-child(even) td {
  background: color-mix(in oklab, var(--background) 96%, currentColor 4%);
}
</style>
