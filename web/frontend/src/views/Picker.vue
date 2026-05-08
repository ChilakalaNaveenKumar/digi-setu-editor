<!--
  Picker — landing view (web mode flat list of sessions, desktop mode
  workspace-then-session drilldown).

  Layout:
    BrandHeader      (logo + nav)
    hero             (tagline + primary CTA)
    recent strip     (search + 5 most recent + "view all" toggle)
    "built on pi"    (small footer credit, deliberately understated)
    site footer      (copyright)

  Branches on `useConfigStore().mode` so the same SPA bundle ships to
  both Tauri (desktop) and Cloud Run (web).
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { Icon } from "@iconify/vue";

import BrandHeader from "../components/BrandHeader.vue";
import { pickFolder } from "../lib/native-bridge";
import { useChatSessionStore } from "../stores/chat-session";
import { useConfigStore } from "../stores/config";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import type { SessionRecord, WorkspaceRecord } from "../api/types";

const router = useRouter();
const cfg = useConfigStore();
const ws = useWorkspaceStore();
const sess = useChatSessionStore();
const ui = useUiStore();

const { mode } = storeToRefs(cfg);
const { workspaces } = storeToRefs(ws);

const busy = ref(false);
const webSessions = ref<Array<SessionRecord & { workspace_id: string }>>([]);

// User-controlled view state. We keep the picker compact by default
// (5 most recent) and let the user expand or filter. Persisting these
// to localStorage isn't worth the complexity — every visit starts
// from the same predictable view.
const search = ref("");
const showAll = ref(false);
/** How many items the compact view shows before "View all" kicks in. */
const COMPACT_LIMIT = 5;

async function refresh(): Promise<void> {
  await ws.refresh();
  if (cfg.mode === "web") {
    const all: Array<SessionRecord & { workspace_id: string }> = [];
    for (const w of ws.workspaces) {
      await sess.refresh(w.id);
      for (const s of sess.sessions) all.push({ ...s, workspace_id: w.id });
    }
    webSessions.value = all.sort((a, b) =>
      (b.last_used || "").localeCompare(a.last_used || ""),
    );
  }
}

onMounted(refresh);

// ── derived lists ──────────────────────────────────────────────────
//
// `filtered*` apply the search filter (case-insensitive substring on
// title; falls back to "Untitled chat" when blank). `visible*` then
// trim to COMPACT_LIMIT unless the user has expanded "view all" or is
// actively searching (where collapsing hides matches).

function _matches(haystack: string | undefined, q: string): boolean {
  if (!q) return true;
  return (haystack || "Untitled chat").toLowerCase().includes(q);
}

const filteredSessions = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return webSessions.value;
  return webSessions.value.filter((s) => _matches(s.title, q));
});

const visibleSessions = computed(() => {
  if (showAll.value || search.value.trim()) return filteredSessions.value;
  return filteredSessions.value.slice(0, COMPACT_LIMIT);
});

const filteredWorkspaces = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return workspaces.value;
  return workspaces.value.filter(
    (w) =>
      _matches(w.name, q) ||
      (w.path || "").toLowerCase().includes(q),
  );
});

const visibleWorkspaces = computed(() => {
  if (showAll.value || search.value.trim()) return filteredWorkspaces.value;
  return filteredWorkspaces.value.slice(0, COMPACT_LIMIT);
});

const totalCount = computed(() =>
  mode.value === "web" ? webSessions.value.length : workspaces.value.length,
);
const hiddenCount = computed(() =>
  mode.value === "web"
    ? Math.max(0, filteredSessions.value.length - visibleSessions.value.length)
    : Math.max(0, filteredWorkspaces.value.length - visibleWorkspaces.value.length),
);

// ── actions ────────────────────────────────────────────────────────

async function startNewWebSession(): Promise<void> {
  busy.value = true;
  try {
    const { workspace, session } = await sess.createWebPair();
    router.push({ name: "chat", params: { sid: session.id }, query: { wsid: workspace.id } });
  } catch (exc) {
    ui.toastError("Could not create chat", exc);
  } finally {
    busy.value = false;
  }
}

function resumeWebSession(s: { id: string; workspace_id: string }): void {
  router.push({ name: "chat", params: { sid: s.id }, query: { wsid: s.workspace_id } });
}

async function deleteWebSession(s: { id: string; workspace_id: string }): Promise<void> {
  const ok = await ui.confirm({
    title: "Delete this chat AND its sandbox?",
    description: "All files in the workspace will be deleted. This cannot be undone.",
    confirmLabel: "Delete",
    cancelLabel: "Keep",
    variant: "destructive",
  });
  if (!ok) return;
  try {
    await ws.remove(s.workspace_id);
    await refresh();
  } catch (exc) {
    ui.toastError("Could not delete", exc);
  }
}

/**
 * Land the user inside a workspace's chat view with the right session
 * preselected. Shared by the "pick a folder" CTA and the "click a recent
 * folder card" path so they never diverge: both trust the registry's
 * dedup (same canonical path → same wsid → same chat history) and only
 * mint a fresh chat when the folder genuinely has no sessions yet.
 */
async function _enterDesktopWorkspace(w: WorkspaceRecord): Promise<void> {
  await sess.refresh(w.id);
  const recent = sess.sessions[0];
  const target = recent ?? (await sess.create(w.id));
  router.push({ name: "chat", params: { sid: target.id }, query: { wsid: w.id } });
}

async function pickDesktopWorkspace(): Promise<void> {
  // Tauri shell → native OS folder dialog. Web build → window.prompt
  // fallback. The same call site works in both deployments because
  // `pickFolder()` runtime-detects.
  const path = await pickFolder();
  if (!path) return;
  busy.value = true;
  try {
    // Backend `register_desktop_workspace` is now idempotent on
    // (owner, canonical_path), so picking a folder we've already
    // registered returns the existing wsid (with chats intact). We
    // only auto-create a fresh chat when this is genuinely a new
    // workspace — `_enterDesktopWorkspace` does that distinction.
    const w = await ws.create({ path });
    await _enterDesktopWorkspace(w);
  } catch (exc) {
    // 404 from the backend means the user picked a folder that no
    // longer exists on disk (deleted or unmounted between dialog and
    // submit). Promote that to a friendlier message; everything else
    // falls through to the generic toast.
    const status = (exc as { status?: number } | null)?.status;
    if (status === 404) {
      ui.toastError(
        "Folder not found — was it moved or deleted? Pick another.",
        exc,
      );
    } else {
      ui.toastError("Could not open folder", exc);
    }
  } finally {
    busy.value = false;
  }
}

async function openDesktopWorkspace(w: WorkspaceRecord): Promise<void> {
  // Re-opening a folder card on the home page: jump to its most-recent
  // chat if one exists, otherwise auto-create a new one.
  busy.value = true;
  try {
    await _enterDesktopWorkspace(w);
  } catch (exc) {
    ui.toastError("Could not open folder", exc);
  } finally {
    busy.value = false;
  }
}

async function renameWorkspace(w: WorkspaceRecord): Promise<void> {
  const next = window.prompt("Rename workspace:", w.name);
  if (!next) return;
  try {
    await ws.rename(w.id, next);
  } catch (exc) {
    ui.toastError("Could not rename", exc);
  }
}

async function deleteDesktopWorkspace(w: WorkspaceRecord): Promise<void> {
  const ok = await ui.confirm({
    title: `Remove "${w.name}" from the picker?`,
    description: "The folder on disk is left untouched.",
    confirmLabel: "Remove",
    cancelLabel: "Cancel",
    variant: "destructive",
  });
  if (!ok) return;
  try {
    await ws.remove(w.id);
  } catch (exc) {
    ui.toastError("Could not remove", exc);
  }
}

async function renameSessionPrompt(s: SessionRecord): Promise<void> {
  const next = window.prompt("Rename chat:", s.title || "Untitled chat");
  if (!next) return;
  try {
    await sess.rename(s.id, next);
    await refresh();
  } catch (exc) {
    ui.toastError("Could not rename", exc);
  }
}

function timeShort(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.valueOf())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const isReady = computed(() => cfg.ready);
</script>

<template>
  <div class="flex min-h-screen w-full flex-col bg-background text-foreground">
    <BrandHeader :home-link="false" />

    <main class="mx-auto flex w-full max-w-5xl flex-1 flex-col px-6 py-10 md:py-16">
      <!-- HERO -->
      <div class="text-center">
        <h1 class="text-3xl font-semibold tracking-tight md:text-4xl">
          What do you want to build today?
        </h1>
        <p class="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
          <template v-if="mode === 'web'">
            Each chat runs in its own sandboxed workspace. Digi Setu writes
            Typst documents, code, and PDFs for you — start a new one or
            jump back into a recent thread.
          </template>
          <template v-else>
            Pick a folder on this machine. Each folder hosts as many chats
            as you like — files, terminals, and snapshots stay local.
          </template>
        </p>
      </div>

      <!-- PRIMARY CTA -->
      <div class="mx-auto mt-8 w-full max-w-md">
        <button
          v-if="isReady && mode === 'web'"
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-md transition-opacity hover:opacity-90 disabled:opacity-60"
          :disabled="busy"
          @click="startNewWebSession"
        >
          <Icon icon="codicon:add" class="h-4 w-4" />
          {{ busy ? "Creating sandbox…" : "New chat" }}
        </button>

        <button
          v-else-if="isReady && mode === 'desktop'"
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-md transition-opacity hover:opacity-90 disabled:opacity-60"
          :disabled="busy"
          @click="pickDesktopWorkspace"
        >
          <Icon icon="codicon:folder-opened" class="h-4 w-4" />
          {{ busy ? "Opening…" : "Open folder…" }}
        </button>

        <div
          v-else
          class="flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-5 py-3 text-sm text-muted-foreground"
        >
          <Icon icon="codicon:loading" class="h-4 w-4 animate-spin" />
          Loading…
        </div>
      </div>

      <!-- ── RECENT STRIP ─────────────────────────────────────────────
           Header row: section title · search input · "view all" toggle.
           The grid below renders the latest 5 by default and expands
           to all when the user clicks "View all". Searching always
           shows every match (no point hiding what they typed for). -->
      <section
        v-if="isReady && totalCount > 0"
        class="mt-12"
      >
        <header class="mb-3 flex flex-wrap items-center gap-3">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {{ mode === "web" ? "Recent chats" : "Recent folders" }}
          </h2>
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ totalCount }} total
          </span>

          <!-- Search input. Magnifier icon inline-left, clear-X right
               when there's a query. Compact and always visible — most
               users hit it before scrolling. -->
          <div
            class="relative ml-auto flex w-full max-w-xs items-center"
          >
            <Icon
              icon="codicon:search"
              class="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-muted-foreground"
            />
            <input
              v-model="search"
              type="search"
              :placeholder="
                mode === 'web' ? 'Search your chats…' : 'Search folders…'
              "
              class="w-full rounded-md border border-border bg-card py-1.5 pl-8 pr-7 text-xs text-foreground outline-none placeholder:text-muted-foreground focus:border-primary/50"
            />
            <button
              v-if="search"
              type="button"
              class="absolute right-1.5 rounded p-0.5 text-muted-foreground hover:text-foreground"
              title="Clear"
              @click="search = ''"
            >
              <Icon icon="codicon:close" class="h-3 w-3" />
            </button>
          </div>

          <button
            v-if="!showAll && hiddenCount > 0 && !search"
            type="button"
            class="rounded-md border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-foreground hover:border-primary/40"
            :title="`Show all ${totalCount} ${mode === 'web' ? 'chats' : 'folders'}`"
            @click="showAll = true"
          >
            View all ({{ hiddenCount }} more)
          </button>
          <button
            v-else-if="showAll && totalCount > COMPACT_LIMIT && !search"
            type="button"
            class="rounded-md border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
            title="Show only the most recent 5"
            @click="showAll = false"
          >
            Show recent 5
          </button>
        </header>

        <!-- WEB MODE GRID -->
        <div
          v-if="mode === 'web'"
          class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          <article
            v-for="s in visibleSessions"
            :key="s.id"
            class="group flex cursor-pointer flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/30"
            @click="resumeWebSession(s)"
          >
            <header class="flex items-start gap-2">
              <Icon
                icon="codicon:comment-discussion"
                class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
              />
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium text-foreground">
                  {{ s.title || "Untitled chat" }}
                </div>
                <div class="font-mono text-[10px] text-muted-foreground">
                  {{ timeShort(s.last_used) }}
                </div>
              </div>
            </header>
            <footer class="mt-auto flex items-center justify-end gap-1 pt-1 opacity-0 transition-opacity group-hover:opacity-100">
              <button
                type="button"
                class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Rename"
                @click.stop="renameSessionPrompt(s)"
              >
                <Icon icon="codicon:edit" class="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                class="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="Delete chat (and its sandbox)"
                @click.stop="deleteWebSession(s)"
              >
                <Icon icon="codicon:trash" class="h-3.5 w-3.5" />
              </button>
            </footer>
          </article>
        </div>

        <!-- DESKTOP MODE GRID -->
        <div
          v-else
          class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          <article
            v-for="w in visibleWorkspaces"
            :key="w.id"
            class="group flex cursor-pointer flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/30"
            @click="openDesktopWorkspace(w)"
          >
            <header class="flex items-start gap-2">
              <Icon
                icon="codicon:folder"
                class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
              />
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium text-foreground">
                  {{ w.name }}
                </div>
                <div class="truncate font-mono text-[10px] text-muted-foreground">
                  {{ w.path }}
                </div>
              </div>
            </header>
            <footer class="mt-auto flex items-center justify-end gap-1 pt-1 opacity-0 transition-opacity group-hover:opacity-100">
              <button
                type="button"
                class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Rename"
                @click.stop="renameWorkspace(w)"
              >
                <Icon icon="codicon:edit" class="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                class="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="Remove from list"
                @click.stop="deleteDesktopWorkspace(w)"
              >
                <Icon icon="codicon:trash" class="h-3.5 w-3.5" />
              </button>
            </footer>
          </article>
        </div>

        <!-- Empty-search hint. Doesn't show on initial state — only
             when the user has typed something that filters everything
             out. -->
        <p
          v-if="search && (mode === 'web' ? filteredSessions.length === 0 : filteredWorkspaces.length === 0)"
          class="mt-4 text-center text-xs text-muted-foreground"
        >
          No matches for "{{ search }}".
        </p>
      </section>

      <!-- Empty state for first-time users. -->
      <p
        v-else-if="isReady"
        class="mt-12 text-center text-xs text-muted-foreground"
      >
        No {{ mode === "web" ? "chats" : "folders" }} yet — start your first one above.
      </p>

      <!--
        "Built on top of pi" — small, deliberate credit line. Pi is the
        underlying agent runtime; we shout the brand (DIGI SETU) and
        keep this sub-credit understated so it reads like a tech badge,
        not a competing brand.
      -->
      <p class="mx-auto mt-16 max-w-md text-center text-[11px] leading-relaxed text-muted-foreground">
        <Icon icon="codicon:circuit-board" class="mr-1 inline h-3 w-3 align-text-bottom" />
        Built on top of
        <a
          href="https://github.com/coding-agent/pi"
          target="_blank"
          rel="noopener noreferrer"
          class="font-mono font-semibold text-foreground/80 hover:text-primary hover:underline"
        >pi</a>
        — an open-source coding agent. Digi Setu adds the sandbox, the
        UI, and the production-grade Typst pipeline.
      </p>
    </main>

    <footer
      class="border-t border-border bg-card/40 px-6 py-4 text-center text-[11px] text-muted-foreground"
    >
      © {{ new Date().getFullYear() }} Digi Setu — built for writers,
      coders &amp; everyone in between.
    </footer>
  </div>
</template>
