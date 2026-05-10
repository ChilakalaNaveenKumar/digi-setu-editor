<!--
  StorageCleanupSection — multi-select per-category cleanup panel.

  Slots into the chat-settings gear popover (desktop) and into Settings
  (web). Renders one row per storage category the backend exposes
  (chats / audits / uploads / shadows on desktop; the web cycle banner
  is a separate component since the policy differs).

  Interaction:
    1. On mount, GET /api/workspaces/{wsid}/storage → summary.
    2. Render one checkbox row per category showing eligible-bytes.
       Disable the checkbox if the category has nothing to clean.
    3. Footer button "Clean selected (N MB)" POSTs the ticked names.
    4. On success, refresh the summary and emit `cleaned` so the parent
       can collapse / show a toast.

  Why a single component (not 4 buttons in the menu):
    The user explicitly asked for "select multiple" — a row of
    independent buttons would mean four discrete clicks for the
    common case ("clean everything I have"). A multi-select
    consolidates that to one tick + one confirm.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Icon } from "@iconify/vue";

import {
  cleanupWorkspaceStorage,
  eligibleBytesFor,
  getWorkspaceStorage,
  hasCleanableContent,
  type StorageCategoryStats,
  type WorkspaceStorageSummary,
} from "../api/sessions";

const props = defineProps<{
  wsid: string;
}>();
const emit = defineEmits<{
  cleaned: [{ freedBytes: number }];
}>();

const summary = ref<WorkspaceStorageSummary | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const selected = ref<Set<StorageCategoryStats["category"]>>(new Set());
const busy = ref(false);
const confirmShadows = ref(false);

async function refresh(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    summary.value = await getWorkspaceStorage(props.wsid);
    // Don't auto-tick on refresh — user always opts in explicitly.
    selected.value = new Set();
    confirmShadows.value = false;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "load failed";
  } finally {
    loading.value = false;
  }
}

onMounted(refresh);

function toggle(cat: StorageCategoryStats): void {
  if (!hasCleanableContent(cat)) return;
  if (selected.value.has(cat.category)) {
    selected.value.delete(cat.category);
  } else {
    selected.value.add(cat.category);
  }
  // Force reactivity (Set mutation isn't tracked by default).
  selected.value = new Set(selected.value);
}

function isSelected(cat: StorageCategoryStats): boolean {
  return selected.value.has(cat.category);
}

const totalSelectedBytes = computed(() => {
  if (!summary.value) return 0;
  let bytes = 0;
  for (const cat of summary.value.categories) {
    if (selected.value.has(cat.category)) {
      bytes += eligibleBytesFor(cat);
    }
  }
  return bytes;
});

const shadowsSelected = computed(() => selected.value.has("shadows"));
const ready = computed(
  () => selected.value.size > 0 && (!shadowsSelected.value || confirmShadows.value),
);

async function clean(): Promise<void> {
  if (!ready.value || busy.value) return;
  busy.value = true;
  const cats = Array.from(selected.value);
  const before = totalSelectedBytes.value;
  try {
    await cleanupWorkspaceStorage(props.wsid, cats);
    emit("cleaned", { freedBytes: before });
    await refresh();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "cleanup failed";
  } finally {
    busy.value = false;
  }
}

function fmtBytes(n: number): string {
  if (n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v >= 10 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}

function rowLabel(cat: StorageCategoryStats): string {
  switch (cat.category) {
    case "chats":
      return `Chats · keep newest ${cat.keep}`;
    case "audits":
      return `Audit log · ${cat.days_to_keep}-day retention`;
    case "uploads":
      return `Attachments · ${cat.days_to_keep}-day retention`;
    case "shadows":
      return "Revert history · destructive";
  }
}

function rowDetail(cat: StorageCategoryStats): string {
  switch (cat.category) {
    case "chats":
      return cat.eligible_chats > 0
        ? `${cat.eligible_chats} old chats · ${fmtBytes(cat.eligible_bytes)}`
        : `${cat.total_chats} chats kept`;
    case "audits":
      return cat.eligible_rows > 0
        ? `${cat.eligible_rows} old rows · ${fmtBytes(cat.eligible_bytes)}`
        : `${cat.total_rows} rows total · ${fmtBytes(cat.total_bytes)}`;
    case "uploads":
      return cat.eligible_files > 0
        ? `${cat.eligible_files} old files · ${fmtBytes(cat.eligible_bytes)}`
        : `${cat.total_files} files · ${fmtBytes(cat.total_bytes)}`;
    case "shadows":
      return cat.total_bytes > 0
        ? `Wipes ${fmtBytes(cat.total_bytes)} of AI revert snapshots`
        : "Nothing to purge";
  }
}
</script>

<template>
  <div class="border-b border-border px-3 py-2.5">
    <div class="mb-1.5 flex items-baseline justify-between">
      <span class="font-mono text-caption uppercase tracking-wide text-muted-foreground">
        storage
      </span>
      <button
        type="button"
        class="text-caption text-muted-foreground hover:text-foreground"
        :disabled="loading"
        title="Refresh"
        @click="refresh"
      >
        <Icon icon="codicon:refresh" class="h-3 w-3" />
      </button>
    </div>

    <div v-if="loading" class="text-caption text-muted-foreground">
      Loading…
    </div>

    <div v-else-if="error" class="text-caption text-rose-300">
      {{ error }}
    </div>

    <div v-else-if="summary" class="flex flex-col gap-1.5">
      <label
        v-for="cat in summary.categories"
        :key="cat.category"
        class="flex cursor-pointer items-start gap-2 rounded border border-border/60 bg-background/40 px-2 py-1.5 transition-colors"
        :class="[
          hasCleanableContent(cat)
            ? 'hover:border-border hover:bg-muted/40'
            : 'opacity-50 cursor-not-allowed',
          isSelected(cat) ? 'border-primary/60 bg-primary/5' : '',
        ]"
      >
        <input
          type="checkbox"
          class="mt-0.5 h-3 w-3 accent-primary"
          :checked="isSelected(cat)"
          :disabled="!hasCleanableContent(cat)"
          @change="toggle(cat)"
        />
        <div class="flex flex-1 flex-col">
          <div class="flex items-center justify-between gap-2">
            <span class="text-caption text-foreground">
              {{ rowLabel(cat) }}
            </span>
            <span
              v-if="cat.category === 'shadows'"
              class="rounded bg-rose-500/10 px-1.5 font-mono text-[10px] uppercase text-rose-300"
            >
              destructive
            </span>
          </div>
          <span class="text-caption leading-tight text-muted-foreground">
            {{ rowDetail(cat) }}
          </span>
        </div>
      </label>

      <!-- Shadows confirm. The user can tick the box but the button stays
           disabled until they ALSO tick this one. Two-step to make sure
           the destructive nature actually registers. -->
      <label
        v-if="shadowsSelected"
        class="mt-1 flex items-start gap-2 rounded border border-rose-500/30 bg-rose-500/5 px-2 py-1.5"
      >
        <input
          v-model="confirmShadows"
          type="checkbox"
          class="mt-0.5 h-3 w-3 accent-rose-500"
        />
        <span class="text-caption leading-tight text-rose-200">
          I understand revert history will be permanently deleted — I won't be
          able to undo AI edits made before this cleanup.
        </span>
      </label>

      <button
        type="button"
        class="mt-1.5 w-full rounded border border-border bg-background px-2 py-1.5 font-mono text-caption hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        :class="ready && !busy ? 'text-foreground' : 'text-muted-foreground'"
        :disabled="!ready || busy"
        @click="clean"
      >
        <span v-if="busy">Cleaning…</span>
        <span v-else-if="!ready && selected.size === 0">
          Pick what to clean
        </span>
        <span v-else-if="!ready && shadowsSelected && !confirmShadows">
          Confirm above to enable
        </span>
        <span v-else>
          Clean selected · {{ fmtBytes(totalSelectedBytes) }}
        </span>
      </button>
    </div>
  </div>
</template>
