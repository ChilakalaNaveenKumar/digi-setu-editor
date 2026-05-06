<!--
  EditorTabs — VS Code-style tab strip. One tab per open file, the active
  tab gets a tinted background, and a × button appears on hover (and is
  always visible for dirty tabs as a ● dot that doubles as the close
  control). Right-click a tab → close-others / close-all menu.
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";
import { useSessionStore } from "../stores/session";
import { iconForPath } from "../lib/file-icons";

const store = useSessionStore();
const { openTabs, activeTabPath } = storeToRefs(store);

function basename(p: string): string {
  const i = p.lastIndexOf("/");
  return i === -1 ? p : p.slice(i + 1);
}

// ── Horizontal scroll: chevron arrows + active-tab auto-scroll ────────
const scroller = ref<HTMLDivElement | null>(null);
const canScrollLeft = ref(false);
const canScrollRight = ref(false);
const isOverflowing = ref(false);

function updateScrollState(): void {
  const el = scroller.value;
  if (!el) return;
  const max = el.scrollWidth - el.clientWidth;
  isOverflowing.value = max > 1;
  canScrollLeft.value = el.scrollLeft > 1;
  canScrollRight.value = el.scrollLeft < max - 1;
}

function scrollBy(delta: number): void {
  scroller.value?.scrollBy({ left: delta, behavior: "smooth" });
}

function onWheel(e: WheelEvent): void {
  // Map vertical wheel into horizontal scroll so trackpad swipes work.
  if (!scroller.value) return;
  if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
    e.preventDefault();
    scroller.value.scrollLeft += e.deltaY;
  }
}

// When the active tab changes, scroll it into view so it's never hidden
// behind the right chevron.
watch(activeTabPath, async () => {
  await nextTick();
  if (!scroller.value) return;
  const active = scroller.value.querySelector<HTMLElement>(".tab-active");
  active?.scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" });
  updateScrollState();
});

watch(openTabs, () => nextTick().then(updateScrollState), { deep: true });

let resizeObs: ResizeObserver | null = null;
onMounted(() => {
  updateScrollState();
  if (scroller.value && typeof ResizeObserver !== "undefined") {
    resizeObs = new ResizeObserver(updateScrollState);
    resizeObs.observe(scroller.value);
  }
});
onUnmounted(() => {
  resizeObs?.disconnect();
  resizeObs = null;
});

function activate(path: string): void {
  // Re-open if (a) it's a different tab, OR (b) currentFile didn't make
  // it (e.g. after a refresh: tabs restore from localStorage but file
  // content + kind don't, so the editor body would otherwise be blank).
  const cur = store.currentFile;
  if (path === activeTabPath.value && cur && cur.path === path) return;
  void store.openFile(path);
}

async function close(path: string, e: MouseEvent): Promise<void> {
  e.stopPropagation();
  await store.closeTab(path);
}

// ── Right-click: simple inline menu (close others / close all) ────────
const menu = ref<{
  open: boolean;
  x: number;
  y: number;
  path: string | null;
  /** When true, show the overflow list (all open tabs) instead of the
   *  per-tab "Close / Close Others / Close All" menu. */
  overflow: boolean;
}>({
  open: false,
  x: 0,
  y: 0,
  path: null,
  overflow: false,
});

function openOverflowMenu(e: MouseEvent): void {
  e.preventDefault();
  e.stopPropagation();
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  // Anchor under the button, right-aligned.
  menu.value = {
    open: true,
    x: rect.right - 240,
    y: rect.bottom + 2,
    path: null,
    overflow: true,
  };
}

function pickFromOverflow(path: string): void {
  closeMenu();
  void store.openFile(path);
}

function openMenu(e: MouseEvent, path: string): void {
  e.preventDefault();
  e.stopPropagation();
  menu.value = { open: true, x: e.clientX, y: e.clientY, path, overflow: false };
}

function closeMenu(): void {
  if (menu.value.open) menu.value = { open: false, x: 0, y: 0, path: null, overflow: false };
}

function ctxClose(): void {
  const p = menu.value.path;
  closeMenu();
  if (p) void store.closeTab(p);
}
function ctxCloseOthers(): void {
  const p = menu.value.path;
  closeMenu();
  if (p) void store.closeOtherTabs(p);
}
function ctxCloseAll(): void {
  closeMenu();
  void store.closeAllTabs();
}

const hasTabs = computed(() => openTabs.value.length > 0);
</script>

<template>
  <!--
    `min-w-0` is required so the inner scroller can detect overflow.
    Without it the tab strip would just expand to its content and the
    parent pane would absorb the growth (= no chevrons ever appear).
  -->
  <div
    v-if="hasTabs"
    class="editor-tabs flex w-full min-w-0 shrink-0 items-stretch border-b border-border bg-card"
    @click="closeMenu"
    @contextmenu="closeMenu"
  >
    <!-- ◀ scroll left -->
    <button
      v-if="isOverflowing"
      type="button"
      :disabled="!canScrollLeft"
      class="flex w-6 shrink-0 items-center justify-center border-r border-border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
      title="Scroll tabs left"
      @click="scrollBy(-200)"
    >
      <Icon icon="codicon:chevron-left" class="h-[14px] w-[14px]" />
    </button>

    <!-- Scrollable tab list -->
    <div
      ref="scroller"
      class="tab-scroller flex min-w-0 flex-1 items-stretch overflow-x-auto"
      @scroll="updateScrollState"
      @wheel="onWheel"
    >
      <div
        v-for="tab in openTabs"
        :key="tab.path"
        :class="[
          'group/tab relative flex max-w-[240px] min-w-[100px] shrink-0 cursor-pointer items-center gap-1.5 border-r border-border px-3 py-1.5 text-[12px] transition-colors',
          tab.path === activeTabPath
            ? 'tab-active bg-editor text-foreground'
            : 'bg-card text-foreground/70 hover:bg-accent/40',
        ]"
        :title="tab.path"
        @click="activate(tab.path)"
        @contextmenu="(e) => openMenu(e, tab.path)"
      >
        <Icon
          :icon="iconForPath(basename(tab.path), false)"
          class="h-[14px] w-[14px] shrink-0"
        />
        <span class="min-w-0 flex-1 truncate font-mono">{{ basename(tab.path) }}</span>
        <!-- Close button: hidden by default. When dirty, ● is shown
             always; on hover the ● turns into ×. -->
        <button
          type="button"
          :class="[
            'flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
            tab.dirty
              ? 'opacity-100'
              : 'opacity-0 group-hover/tab:opacity-100',
          ]"
          :title="tab.dirty ? 'Unsaved changes — click to close' : 'Close tab'"
          @click="(e) => close(tab.path, e)"
        >
          <span v-if="tab.dirty" class="dirty-dot inline-block h-1.5 w-1.5 rounded-full bg-warning"></span>
          <Icon v-else icon="codicon:close" class="h-[12px] w-[12px]" />
        </button>
      </div>
    </div>

    <!-- ▶ scroll right -->
    <button
      v-if="isOverflowing"
      type="button"
      :disabled="!canScrollRight"
      class="flex w-6 shrink-0 items-center justify-center border-l border-border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
      title="Scroll tabs right"
      @click="scrollBy(200)"
    >
      <Icon icon="codicon:chevron-right" class="h-[14px] w-[14px]" />
    </button>

    <!-- Overflow menu (▾ — list of all open tabs) -->
    <button
      v-if="isOverflowing"
      type="button"
      class="flex w-7 shrink-0 items-center justify-center border-l border-border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      title="Show all open tabs"
      @click="(e) => openOverflowMenu(e)"
    >
      <Icon icon="codicon:list-flat" class="h-[14px] w-[14px]" />
    </button>

    <!-- Right-click menu / overflow menu -->
    <Teleport to="body">
      <div
        v-if="menu.open"
        class="fixed z-[60] min-w-[200px] max-w-[320px] overflow-hidden rounded-md border border-border bg-card shadow-lg"
        :style="{ left: `${Math.max(menu.x, 8)}px`, top: `${menu.y}px` }"
        @click.stop
        @contextmenu.prevent
      >
        <!-- Per-tab right-click menu -->
        <template v-if="!menu.overflow">
          <button
            type="button"
            class="block w-full px-3 py-1.5 text-left text-[12px] hover:bg-accent"
            @click="ctxClose"
          >Close</button>
          <button
            type="button"
            class="block w-full px-3 py-1.5 text-left text-[12px] hover:bg-accent"
            @click="ctxCloseOthers"
          >Close Others</button>
          <button
            type="button"
            class="block w-full px-3 py-1.5 text-left text-[12px] hover:bg-accent"
            @click="ctxCloseAll"
          >Close All</button>
        </template>
        <!-- Overflow menu — list of every open tab -->
        <template v-else>
          <div class="max-h-[60vh] overflow-y-auto">
            <button
              v-for="t in openTabs"
              :key="t.path"
              type="button"
              :class="[
                'flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-[12px] hover:bg-accent',
                t.path === activeTabPath ? 'bg-primary/10 text-primary' : '',
              ]"
              :title="t.path"
              @click="pickFromOverflow(t.path)"
            >
              <Icon
                :icon="iconForPath(basename(t.path), false)"
                class="h-[14px] w-[14px] shrink-0"
              />
              <span class="min-w-0 flex-1 truncate font-mono">{{ basename(t.path) }}</span>
              <span
                v-if="t.dirty"
                class="ml-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-warning"
                title="Unsaved changes"
              ></span>
            </button>
          </div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.dirty-dot {
  /* Make the dot visibly pulse while editing to draw attention. */
  animation: pulse-dot 1.6s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
.group\/tab:hover .dirty-dot {
  /* Suppress the dot while the close X takes its place on hover. */
  display: none;
}
/* Hide the chunky default scrollbar — chevrons + trackpad swipe replace it. */
.tab-scroller {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.tab-scroller::-webkit-scrollbar {
  display: none;
}
</style>
