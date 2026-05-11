<!--
  AppShell — Cursor / VS Code style layout with full-resize panels.

  Layout (all gutters draggable, all sizes persisted):
    ┌────────────┬─────────────────────────────────────┬────────────┐
    │ FileTree   │  EditorPane                         │ ChatPane   │
    │ (resize)   │  ───────────────────────────────    │ (resize)   │
    │            │  TerminalPane (vertical split)      │            │
    └────────────┴─────────────────────────────────────┴────────────┘

  TerminalPane can be fully collapsed via its own header toggle. When
  collapsed we drop the bottom Pane entirely and let the editor take the
  full vertical space, then restore the user's last terminal height when
  re-expanded.

  Sizes are stored as percentages and persisted to localStorage so the
  layout survives reloads.
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Splitpanes, Pane } from "splitpanes";
import "splitpanes/dist/splitpanes.css";

import ChatPane from "./ChatPane.vue";
import EditorPane from "./EditorPane.vue";
import FileTreePane from "./FileTreePane.vue";
import TerminalPane from "./TerminalPane.vue";
import { useFilesStore } from "../stores/files";
import { useTerminalsStore } from "../stores/terminals";

const files = useFilesStore();
const terminals = useTerminalsStore();

// ── Persisted sizes ──────────────────────────────────────────────────
const LS_HORIZ = "ui.layout.horizontal";
const LS_VERT = "ui.layout.editor-terminal";

interface HorizSizes {
  tree: number;
  middle: number;
  chat: number;
}
interface VertSizes {
  editor: number;
  terminal: number;
}

function loadHoriz(): HorizSizes {
  if (typeof window === "undefined") return { tree: 18, middle: 52, chat: 30 };
  try {
    const raw = window.localStorage.getItem(LS_HORIZ);
    if (raw) {
      const v = JSON.parse(raw);
      if (
        typeof v?.tree === "number" &&
        typeof v?.middle === "number" &&
        typeof v?.chat === "number"
      ) {
        return v;
      }
    }
  } catch {
    /* ignore */
  }
  return { tree: 18, middle: 52, chat: 30 };
}

function loadVert(): VertSizes {
  if (typeof window === "undefined") return { editor: 65, terminal: 35 };
  try {
    const raw = window.localStorage.getItem(LS_VERT);
    if (raw) {
      const v = JSON.parse(raw);
      if (typeof v?.editor === "number" && typeof v?.terminal === "number") {
        return v;
      }
    }
  } catch {
    /* ignore */
  }
  return { editor: 65, terminal: 35 };
}

const horiz = ref<HorizSizes>(loadHoriz());
const vert = ref<VertSizes>(loadVert());

function saveHoriz(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_HORIZ, JSON.stringify(horiz.value));
  } catch {
    /* ignore */
  }
}
function saveVert(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_VERT, JSON.stringify(vert.value));
  } catch {
    /* ignore */
  }
}

interface PaneSize {
  size: number;
}

/**
 * Read a numeric `.size` from a pane entry. The splitpanes library
 * occasionally fires `resize` with array slots that are momentarily
 * undefined / mid-update — typically while the inner Splitpanes is
 * being torn down by the terminal-collapse v-if swap. Guarding here
 * keeps Vue from logging an "Unhandled error during execution of
 * component event handler" on every drag.
 */
function safeSize(p: PaneSize | undefined | null): number | null {
  if (!p) return null;
  const v = (p as PaneSize).size;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function onHorizResize(panes: PaneSize[]): void {
  try {
    if (!Array.isArray(panes) || panes.length < 3) return;
    const t = safeSize(panes[0]);
    const m = safeSize(panes[1]);
    const c = safeSize(panes[2]);
    if (t === null || m === null || c === null) return;
    horiz.value = { tree: t, middle: m, chat: c };
    saveHoriz();
  } catch (exc) {
    console.warn("[appshell] horiz resize handler swallowed", exc);
  }
}

function onVertResize(panes: PaneSize[]): void {
  try {
    if (!Array.isArray(panes) || panes.length < 2) return;
    const e = safeSize(panes[0]);
    const t = safeSize(panes[1]);
    if (e === null || t === null) return;
    vert.value = { editor: e, terminal: t };
    saveVert();
  } catch (exc) {
    console.warn("[appshell] vert resize handler swallowed", exc);
  }
}

// Terminal collapse state lives in the store so the toggle inside
// TerminalPane stays in sync with the splitpanes layout here.
const terminalShown = computed(() => terminals.expanded);

// When terminal becomes hidden, remember the current vertical sizes so
// we can restore them on re-show.
const stashedVert = ref<VertSizes | null>(null);
watch(terminalShown, (shown) => {
  if (!shown) {
    stashedVert.value = { ...vert.value };
  } else if (stashedVert.value) {
    vert.value = stashedVert.value;
    saveVert();
  }
});

onMounted(() => {
  // Defensive: re-apply stored sizes after mount in case Splitpanes
  // initialized with default values before reading our refs.
  saveHoriz();
  saveVert();
  // Restore the previously active tab so the editor body isn't blank
  // on refresh. Tabs are persisted to localStorage but currentFile
  // (the actual content / kind) is not — fetch it now.
  if (files.activeTabPath && !files.currentFile) {
    void files.openFile(files.activeTabPath);
  }
});
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background text-foreground overflow-hidden">
    <Splitpanes
      class="ide-splitpanes flex-1"
      :dbl-click-splitter="false"
      @resize="onHorizResize"
    >
      <!-- ── LEFT: file tree ──────────────────────────────────────── -->
      <Pane :size="horiz.tree" :min-size="10" :max-size="40">
        <FileTreePane />
      </Pane>

      <!-- ── MIDDLE: editor + (optional) terminal vertical split ────
           When terminal is expanded → vertical Splitpanes split.
           When terminal is collapsed → Editor takes ALL the height
           and TerminalPane is rendered as a 1-row header at the
           bottom (height: auto), so it doesn't eat half the screen. -->
      <Pane :size="horiz.middle" :min-size="20">
        <div class="flex h-full min-h-0 w-full flex-col">
          <template v-if="terminalShown">
            <Splitpanes
              class="ide-splitpanes vertical"
              horizontal
              :dbl-click-splitter="false"
              @resize="onVertResize"
            >
              <Pane :size="vert.editor" :min-size="20">
                <EditorPane />
              </Pane>
              <Pane :size="vert.terminal" :min-size="8">
                <TerminalPane />
              </Pane>
            </Splitpanes>
          </template>

          <template v-else>
            <!-- Editor flexes to fill, terminal is just its header bar -->
            <div class="flex min-h-0 flex-1">
              <EditorPane />
            </div>
            <TerminalPane />
          </template>
        </div>
      </Pane>

      <!-- ── RIGHT: chat ──────────────────────────────────────────── -->
      <Pane :size="horiz.chat" :min-size="15" :max-size="60">
        <ChatPane />
      </Pane>
    </Splitpanes>
  </div>
</template>

<style>
/*
  Splitpanes content containment.

  Without `overflow: hidden` + `min-width: 0` on every pane, children with
  intrinsic min-content widths (long code lines, wide tab strips, fitted
  PDF viewers) push their parent pane WIDER than the percentage Splitpanes
  set. The visible result: the chat pane gets squeezed off-screen as you
  open more tabs / open a PDF. The fix is purely CSS — keep panes clipped
  and force min-width:0 so flex children can scroll instead of expanding.
*/
.ide-splitpanes > .splitpanes__pane {
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}

/* Splitpanes — themed for our Notion-teal dark UI. The default theme is
   light/blue; we override gutters to be subtle dark dividers that brighten
   on hover so users can find the drag handles. */
.ide-splitpanes.splitpanes--vertical > .splitpanes__splitter {
  background: var(--border, #2a2a2e);
  width: 4px;
  margin-left: -1px;
  margin-right: -1px;
  cursor: col-resize;
  transition: background 0.12s;
  border: none;
  position: relative;
}
.ide-splitpanes.splitpanes--horizontal > .splitpanes__splitter {
  background: var(--border, #2a2a2e);
  height: 4px;
  margin-top: -1px;
  margin-bottom: -1px;
  cursor: row-resize;
  transition: background 0.12s;
  border: none;
  position: relative;
}
.ide-splitpanes > .splitpanes__splitter:hover,
.ide-splitpanes > .splitpanes__splitter.splitpanes__splitter--dragging {
  background: var(--primary, #00b8a9);
}
/* Hit target a little wider than the visible bar for easier grabbing. */
.ide-splitpanes.splitpanes--vertical > .splitpanes__splitter::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: -3px;
  right: -3px;
}
.ide-splitpanes.splitpanes--horizontal > .splitpanes__splitter::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: -3px;
  bottom: -3px;
}
.ide-splitpanes > .splitpanes__pane {
  background: transparent;
  display: flex;
  min-height: 0;
  min-width: 0;
}
</style>
