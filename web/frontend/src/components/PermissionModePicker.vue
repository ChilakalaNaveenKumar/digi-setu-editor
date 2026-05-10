<!--
  PermissionModePicker — single-line dropdown.

  Three modes (the persisted IDs are the wire format; labels are
  what the user sees):

    auto      → "Auto"      Run every tool without asking. Audit log
                            still records every action.
    ask       → "Ask"       Ask before shell commands, file edits, and
                            background processes. Reads pass silently.
                            (Default — matches Cursor/Cline default.)
    cautious  → "Cautious"  Ask before every tool call, including
                            reads and searches.

  Backwards-compat: the picker ALSO accepts the legacy IDs
  (`approve_risky`, `approve_all`) on read; the backend's user_prefs
  service maps them to the new canonical IDs on first save.

  The picker writes to /api/me/prefs/permission_mode (persisted per
  user) and optimistically updates the local sessionMode in the
  permissions store so the modal-routing condition flips immediately.
  The backend persists the new value to a per-user "live" file that
  every running pi extension re-reads on each tool_call, so the change
  applies to the CURRENT chat from its very next tool call onward — no
  respawn needed.

  The dropdown is teleported to <body> so it doesn't get clipped when
  this component is nested inside another popover (e.g. ChatSettings-
  Menu) — same pattern as ModelPicker.
-->
<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useI18n } from "vue-i18n";
import { Icon } from "@iconify/vue";

import { apiJson, apiPatch } from "../api/client";
import { usePermissionsStore, type PermissionMode } from "../stores/permissions";

const permissions = usePermissionsStore();
const { t } = useI18n();
const { sessionMode } = storeToRefs(permissions);

const open = ref(false);
const triggerRef = ref<HTMLButtonElement | null>(null);
const dropdownRef = ref<HTMLDivElement | null>(null);
const persisted = ref<PermissionMode | null>(null);
const updating = ref(false);

interface PrefsResponse {
  permission_mode: PermissionMode;
  permission_modes_available: PermissionMode[];
}

/** Title-cased mode label, sourced from the locale file. */
function label(mode: PermissionMode): string {
  return t(`permission.mode.${mode}.label`);
}

/** One-line blurb shown under each row. */
function blurb(mode: PermissionMode): string {
  return t(`permission.mode.${mode}.blurb`);
}

// Order matters — least → most cautious so the user reads the spectrum
// top-down. This is the exact order Claude Code, Cursor, and Continue
// all use in their pickers.
const MODE_ORDER: PermissionMode[] = ["auto", "ask", "cautious"];

const popoverStyle = ref<Record<string, string>>({});

// Anchor the popover to the trigger via a fixed-position computed
// style. The chat settings popover and the chat pane both have
// overflow clipping, so a normal absolute-positioned dropdown gets
// cut on the left side. Going through <Teleport> + fixed positioning
// sidesteps every parent's clip box.
//
// Flip strategy: this picker lives in the composer toolbar, which
// itself lives at the BOTTOM of the chat pane. Opening downward
// almost always pushes the dropdown off-screen (or into the
// 200 px-strip-of-life cropping it to a single visible row).
// Rule:
//   space_below  := viewport.bottom - trigger.bottom
//   space_above  := trigger.top
//   desired      := 280 px (3 modes + footer + breathing room)
// Open downward only when space_below ≥ desired OR space_below ≥
// space_above. Otherwise flip up. The previous threshold was a
// hard "< 200 px below" cut-off which left the picker awkwardly
// half-off-screen at composer heights between 200–280 px below.
function reposition(): void {
  const t = triggerRef.value;
  if (!t) return;
  const rect = t.getBoundingClientRect();
  const margin = 8;
  const desiredWidth = 320;
  const desiredHeight = 280;
  const width = Math.min(desiredWidth, window.innerWidth - margin * 2);
  let left = rect.right - width;
  if (left < margin) left = margin;
  if (left + width > window.innerWidth - margin) {
    left = window.innerWidth - margin - width;
  }
  const spaceBelow = window.innerHeight - rect.bottom - margin;
  const spaceAbove = rect.top - margin;
  const flipUp = spaceBelow < desiredHeight && spaceAbove > spaceBelow;
  if (flipUp) {
    popoverStyle.value = {
      position: "fixed",
      top: "auto",
      bottom: `${window.innerHeight - rect.top + 4}px`,
      left: `${left}px`,
      width: `${width}px`,
      maxHeight: `${Math.min(desiredHeight, spaceAbove)}px`,
    };
    return;
  }
  popoverStyle.value = {
    position: "fixed",
    top: `${rect.bottom + 4}px`,
    left: `${left}px`,
    width: `${width}px`,
    maxHeight: `${Math.min(desiredHeight, spaceBelow)}px`,
  };
}

async function load(): Promise<void> {
  try {
    const r = await apiJson<PrefsResponse>("/api/me/prefs");
    persisted.value = r.permission_mode;
    permissions.setMode(r.permission_mode);
  } catch (exc) {
    console.warn("[perm-picker] could not load prefs", exc);
  }
}

async function pick(mode: PermissionMode): Promise<void> {
  open.value = false;
  if (mode === persisted.value) return;
  updating.value = true;
  try {
    const r = await apiPatch<PrefsResponse>("/api/me/prefs/permission_mode", { mode });
    persisted.value = r.permission_mode;
    permissions.setMode(r.permission_mode);
  } catch (exc) {
    console.warn("[perm-picker] update failed", exc);
  } finally {
    updating.value = false;
  }
}

function onDocClick(e: MouseEvent): void {
  const t = triggerRef.value;
  const d = dropdownRef.value;
  const target = e.target as Node;
  if (t && t.contains(target)) return;
  if (d && d.contains(target)) return;
  open.value = false;
}

onMounted(() => {
  void load();
  document.addEventListener("click", onDocClick);
  window.addEventListener("resize", reposition);
  // Capture-phase scroll listener so we re-anchor when ANY ancestor
  // scrolls, not just the document — settings popover + chat pane both
  // scroll.
  window.addEventListener("scroll", reposition, true);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocClick);
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
});

watch(open, async (v) => {
  if (!v) return;
  await nextTick();
  reposition();
});

const buttonLabel = (): string => label(sessionMode.value);
</script>

<template>
  <div class="relative inline-flex items-center">
    <button
      ref="triggerRef"
      type="button"
      class="flex w-full items-center gap-1.5 rounded border border-border bg-background px-2 py-0.5 text-caption font-medium text-foreground hover:bg-muted disabled:opacity-50"
      :disabled="updating"
      :title="$t('permission.modeLabel', { mode: label(sessionMode) })"
      @click="open = !open"
    >
      <Icon icon="codicon:shield" class="h-3 w-3 opacity-70" />
      <span class="flex-1 text-left">{{ buttonLabel() }}</span>
      <svg class="h-3 w-3 opacity-60" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
        <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.2" fill="none" />
      </svg>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="dropdownRef"
        :style="popoverStyle"
        class="z-[60] flex flex-col overflow-hidden rounded-md border border-border bg-popover shadow-xl ring-1 ring-black/10"
      >
        <div class="flex-1 overflow-y-auto py-1">
          <button
            v-for="m in MODE_ORDER"
            :key="m"
            type="button"
            class="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-muted"
            @click="pick(m)"
          >
            <span class="flex w-full items-center justify-between text-caption">
              <span class="flex items-center gap-1.5">
                <span
                  v-if="m === sessionMode"
                  class="h-1.5 w-1.5 rounded-full bg-success"
                  aria-label="active"
                />
                <span class="font-semibold">{{ label(m) }}</span>
              </span>
              <span
                v-if="m === persisted"
                class="text-caption uppercase tracking-wide text-muted-foreground"
              >{{ $t("common.saved") }}</span>
            </span>
            <span class="text-caption leading-snug text-muted-foreground">{{ blurb(m) }}</span>
          </button>
        </div>
        <div class="border-t border-border px-3 py-2 text-caption leading-snug text-muted-foreground">
          <i18n-t keypath="permission.appliesToChat" tag="span">
            <template #bold><strong>{{ $t("permission.thisChat") }}</strong></template>
          </i18n-t>
        </div>
      </div>
    </Teleport>
  </div>
</template>
