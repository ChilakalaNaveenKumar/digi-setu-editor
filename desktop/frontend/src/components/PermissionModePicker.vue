<!--
  PermissionModePicker — single-line dropdown.

  Three modes:
    auto           → backend never prompts; audit log still records every call
    approve_risky  → modal prompt for bash / write / edit / process; reads pass
    approve_all    → modal prompt for every tool call (incl. read/grep/find/ls)

  The picker writes to /api/me/prefs/permission_mode (persisted per user) and
  optimistically updates the local sessionMode in the permissions store so the
  modal-routing condition flips immediately. The backend persists the new
  value to a per-user "live" file that every running pi extension re-reads on
  each tool_call, so the change applies to the CURRENT chat from its very
  next tool call onward — no respawn needed.

  The dropdown is teleported to <body> so it doesn't get clipped when this
  component is nested inside another popover (e.g. ChatSettingsMenu) — same
  pattern as ModelPicker.
-->
<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { Icon } from "@iconify/vue";

import { apiJson, apiPatch } from "../api/client";
import { usePermissionsStore, type PermissionMode } from "../stores/permissions";

const permissions = usePermissionsStore();
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

const LABELS: Record<PermissionMode, string> = {
  auto: "auto",
  approve_risky: "approve risky",
  approve_all: "approve all",
};

const BLURBS: Record<PermissionMode, string> = {
  auto: "Never prompts. Every tool call still gets logged.",
  approve_risky: "Prompts for bash / write / edit / processes. Reads pass.",
  approve_all: "Prompts for every tool call. Slowest, most cautious.",
};

const popoverStyle = ref<Record<string, string>>({});

// Anchor the popover to the trigger via a fixed-position computed style.
// The chat settings popover and the chat pane both have overflow clipping,
// so a normal absolute-positioned dropdown gets cut on the left side
// (visible in the screenshot the user shared). Going through <Teleport>
// + fixed positioning sidesteps every parent's clip box.
function reposition(): void {
  const t = triggerRef.value;
  if (!t) return;
  const rect = t.getBoundingClientRect();
  const margin = 8;
  const desiredWidth = 288;
  const width = Math.min(desiredWidth, window.innerWidth - margin * 2);
  let left = rect.right - width;
  if (left < margin) left = margin;
  if (left + width > window.innerWidth - margin) {
    left = window.innerWidth - margin - width;
  }
  // Place below; if not enough room, flip above the trigger.
  const spaceBelow = window.innerHeight - rect.bottom;
  let top = rect.bottom + 4;
  let maxHeight = spaceBelow - margin;
  if (spaceBelow < 200 && rect.top > 200) {
    top = rect.top - 4;
    maxHeight = rect.top - margin;
    popoverStyle.value = {
      position: "fixed",
      top: "auto",
      bottom: `${window.innerHeight - rect.top + 4}px`,
      left: `${left}px`,
      width: `${width}px`,
      maxHeight: `${maxHeight}px`,
    };
    return;
  }
  popoverStyle.value = {
    position: "fixed",
    top: `${top}px`,
    left: `${left}px`,
    width: `${width}px`,
    maxHeight: `${Math.min(360, maxHeight)}px`,
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
  // Capture-phase scroll listener so we re-anchor when ANY ancestor scrolls,
  // not just the document — settings popover + chat pane both scroll.
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

const buttonLabel = () => LABELS[sessionMode.value] || sessionMode.value;
</script>

<template>
  <div class="relative inline-flex items-center">
    <button
      ref="triggerRef"
      type="button"
      class="flex w-full items-center gap-1.5 rounded border border-border bg-background px-2 py-0.5 text-[11px] font-mono text-foreground hover:bg-muted disabled:opacity-50"
      :disabled="updating"
      :title="`permission mode: ${sessionMode}`"
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
            v-for="m in ['auto', 'approve_risky', 'approve_all'] as PermissionMode[]"
            :key="m"
            type="button"
            class="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-muted"
            @click="pick(m)"
          >
            <span class="flex w-full items-center justify-between font-mono text-[11px]">
              <span class="flex items-center gap-1.5">
                <span
                  v-if="m === sessionMode"
                  class="h-1.5 w-1.5 rounded-full bg-success"
                  aria-label="active"
                />
                <span>{{ LABELS[m] }}</span>
              </span>
              <span v-if="m === persisted" class="text-[10px] uppercase text-muted-foreground">saved</span>
            </span>
            <span class="text-[10px] leading-tight text-muted-foreground">{{ BLURBS[m] }}</span>
          </button>
        </div>
        <div class="border-t border-border px-3 py-2 text-[10px] leading-tight text-muted-foreground">
          Applies to <strong>this chat</strong> from the next tool call onward.
        </div>
      </div>
    </Teleport>
  </div>
</template>
