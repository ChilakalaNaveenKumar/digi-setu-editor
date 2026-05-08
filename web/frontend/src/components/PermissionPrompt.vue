<!--
  PermissionPrompt — compact, inline tool-call approval card.

  Lives at the bottom-right of the chat pane (NOT a screen-blocking
  modal). Default state shows one line: "pi wants to run X" + 2 primary
  buttons (Allow / Deny). Click the chevron to expand for intent +
  command/diff preview + the "always" variants. Cursor / Aider / Goose
  all use this pattern — the dialog never steals the screen.

  Decisions go back over the WS via chat.sendPermissionResponse, then we
  dequeue locally so the next pending request takes the slot.

  Keyboard (only when no editable element is focused):
    Esc          → deny_once  (safe default if user dismisses)
    Enter        → allow_once
    Shift+Enter  → allow_session
    a            → toggle expanded view (aider muscle memory)
-->
<script setup lang="ts">
import { createPatch } from "diff";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { Icon } from "@iconify/vue";

import { useChatStore } from "../stores/chat";
import { usePermissionsStore, type PermissionDecision } from "../stores/permissions";

import DiffView from "./tools/DiffView.vue";

const chat = useChatStore();
const permissions = usePermissionsStore();

const current = computed(() => permissions.current);

const expanded = ref(false);

// Reset expansion state whenever a new request takes the slot — no
// reason a previously-expanded prompt should leak its state into the
// next decision the user has to make.
watch(
  () => current.value?.id,
  () => {
    expanded.value = false;
  },
);

const TOOL_LABELS: Record<string, string> = {
  bash: "run shell",
  write: "write file",
  edit: "edit file",
  process: "start process",
  process_start: "start process",
};

const TOOL_ICONS: Record<string, string> = {
  bash: "codicon:terminal",
  write: "codicon:new-file",
  edit: "codicon:edit",
  process: "codicon:server-process",
  process_start: "codicon:server-process",
};

function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] || tool;
}

function toolIcon(tool: string): string {
  return TOOL_ICONS[tool] || "codicon:tools";
}

// Short, non-wrapping label for the mode chip in the header. Full label
// is shown via title attribute on hover.
const MODE_CHIP: Record<string, string> = {
  auto: "auto",
  approve_risky: "risky",
  approve_all: "all",
};

function modeChip(mode: string): string {
  return MODE_CHIP[mode] || mode;
}

// Single-line summary used in the collapsed header. We try to surface
// the most operator-relevant detail so the user can decide without
// expanding 80 % of the time:
//   bash      → first ~80 chars of the command
//   write/edit → file path
//   anything else → JSON-stringified args trimmed
function snippet(): string {
  const c = current.value;
  if (!c) return "";
  const input = c.input || {};
  if (c.tool === "bash") {
    const cmd = String(input.command ?? "");
    return cmd.length > 90 ? cmd.slice(0, 87) + "…" : cmd;
  }
  if (c.tool === "write" || c.tool === "edit") {
    return String(input.file_path ?? input.path ?? "(unknown path)");
  }
  if (c.tool === "process" || c.tool === "process_start") {
    const cmd = String(input.command ?? input.cmd ?? "");
    return cmd.length > 90 ? cmd.slice(0, 87) + "…" : cmd;
  }
  try {
    const j = JSON.stringify(input);
    return j.length > 90 ? j.slice(0, 87) + "…" : j;
  } catch {
    return "";
  }
}

function unifiedDiff(filePath: string, oldText: string, newText: string): string {
  try {
    return createPatch(filePath || "file", oldText || "", newText || "", "", "", { context: 3 });
  } catch (exc) {
    console.warn("[permission] diff render failed", exc);
    return "";
  }
}

function commandText(input: Record<string, unknown> | undefined): string {
  if (!input) return "";
  if (typeof input.command === "string") return input.command;
  return JSON.stringify(input, null, 2);
}

function fileTarget(input: Record<string, unknown> | undefined): string {
  if (!input) return "";
  return String(input.file_path ?? input.path ?? "");
}

function respond(decision: PermissionDecision): void {
  const c = current.value;
  if (!c) return;
  chat.sendPermissionResponse(c.id, decision);
  permissions.dequeue(c.id);
}

function onKey(e: KeyboardEvent): void {
  if (!current.value) return;
  // Don't hijack typing inside the chat composer / editor / file tree
  // rename inputs — only react when focus is on the body / a button.
  const target = e.target as HTMLElement | null;
  if (
    target &&
    (target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable)
  ) {
    return;
  }
  if (e.key === "Escape") {
    e.preventDefault();
    respond("deny_once");
  } else if (e.key === "Enter") {
    e.preventDefault();
    respond(e.shiftKey ? "allow_session" : "allow_once");
  } else if (e.key === "a" || e.key === "A") {
    e.preventDefault();
    expanded.value = !expanded.value;
  }
}

onMounted(() => document.addEventListener("keydown", onKey));
onUnmounted(() => document.removeEventListener("keydown", onKey));
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-150 ease-out"
      leave-active-class="transition-all duration-100 ease-in"
      enter-from-class="opacity-0 translate-y-2"
      leave-to-class="opacity-0 translate-y-2"
    >
      <!--
        Bottom-right anchor on desktop, full-width on small screens. We
        deliberately don't blur or dim the page — long-running chat
        threads stay readable while the user decides. Cursor /
        Continue.dev both behave this way.
      -->
      <div
        v-if="current"
        class="pointer-events-none fixed inset-x-3 bottom-3 z-40 flex justify-end sm:inset-x-auto sm:right-4 sm:bottom-4"
        role="dialog"
        aria-modal="false"
        aria-labelledby="permission-title"
      >
        <div
          :key="current.id"
          class="pi-permission-card pointer-events-auto w-full max-w-[440px] overflow-hidden rounded-md border border-border bg-popover text-foreground shadow-lg ring-1 ring-black/5"
        >
          <!-- Compact header: icon · title · mode chip · queue · expand -->
          <div class="flex items-center gap-2 px-3 py-2">
            <Icon
              :icon="toolIcon(current.tool)"
              class="h-3.5 w-3.5 shrink-0 text-warning"
              aria-hidden="true"
            />
            <div class="min-w-0 flex-1">
              <div id="permission-title" class="truncate font-mono text-[12px]">
                <span class="text-muted-foreground">pi wants to</span>
                <span class="ml-1 font-semibold">{{ toolLabel(current.tool) }}</span>
                <span v-if="snippet()" class="ml-2 text-muted-foreground">·</span>
                <span
                  v-if="snippet()"
                  class="ml-2 text-foreground/80"
                  :title="snippet()"
                >{{ snippet() }}</span>
              </div>
            </div>
            <!-- Mode chip lives in the header so the action row stays a
                 clean 4-button strip. Use the abbreviated label so it
                 never wraps; full label shown on hover. -->
            <span
              class="shrink-0 rounded bg-muted/70 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted-foreground"
              :title="`permission mode: ${current.mode.replace('_', ' ')}`"
            >{{ modeChip(current.mode) }}</span>
            <span
              v-if="permissions.pendingCount > 1"
              class="shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              :title="`${permissions.pendingCount - 1} more queued`"
            >+{{ permissions.pendingCount - 1 }}</span>
            <button
              type="button"
              class="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              :title="expanded ? 'Hide details (a)' : 'Show details (a)'"
              :aria-expanded="expanded"
              @click="expanded = !expanded"
            >
              <Icon
                :icon="expanded ? 'codicon:chevron-down' : 'codicon:chevron-up'"
                class="h-3.5 w-3.5"
              />
            </button>
          </div>

          <!-- Expanded details (intent + command/diff). The "always"
               buttons used to live here too, but users couldn't find
               them — now they're in the always-visible action row. -->
          <div v-if="expanded" class="border-t border-border">
            <div class="max-h-[55vh] overflow-auto">
              <section v-if="current.intent" class="border-b border-border px-3 py-2">
                <div class="mb-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  intent
                </div>
                <div class="whitespace-pre-wrap font-mono text-[11px] leading-snug">
                  {{ current.intent }}
                </div>
              </section>

              <section
                v-if="current.tool === 'bash' || current.tool === 'process' || current.tool === 'process_start'"
                class="px-3 py-2"
              >
                <div class="mb-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  command
                </div>
                <pre class="whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-[11px] leading-snug">{{ commandText(current.input) }}</pre>
              </section>

              <section
                v-else-if="current.tool === 'write' || current.tool === 'edit'"
                class="px-3 py-2"
              >
                <div class="mb-0.5 flex items-baseline justify-between font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  <span>{{ current.tool === "write" ? "write" : "edit" }}</span>
                  <span class="normal-case text-foreground/80">{{ fileTarget(current.input) }}</span>
                </div>
                <DiffView
                  v-if="current.preview && current.preview.kind === 'diff'"
                  :diff="unifiedDiff(current.preview.filePath, current.preview.oldText, current.preview.newText)"
                  :max-rows="20"
                  :max-diff-lines="600"
                />
                <pre v-else class="whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-[11px] leading-snug">{{ commandText(current.input) }}</pre>
              </section>

              <section v-else class="px-3 py-2">
                <div class="mb-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  arguments
                </div>
                <pre class="whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-[11px] leading-snug">{{ commandText(current.input) }}</pre>
              </section>
            </div>
          </div>

          <!-- Action row.
               Order (left → right): Allow · Allow always · Deny always · Deny.
               Allow leads because it's the hot-path action — most calls
               in approve_risky mode are routine and the user wants the
               click to land on the leftmost button without scanning
               the row. Deny stays anchored to the right as the safe
               escape.

               Keyboard:
                 ↵    → Allow once       (1st button)
                 ⇧↵   → Allow always     (2nd button)
                 esc  → Deny once        (last button)
            -->
          <div class="border-t border-border bg-muted/20 px-2 py-1.5">
            <div class="flex h-7 items-stretch gap-1">
              <button
                type="button"
                class="flex-1 rounded border border-success/60 bg-success/15 px-1.5 font-mono text-[11px] font-semibold leading-none whitespace-nowrap text-success hover:bg-success/25"
                title="Allow this single call. Pi will ask again next time. (↵)"
                @click="respond('allow_once')"
              >Allow</button>
              <button
                type="button"
                class="flex-1 rounded border border-transparent bg-background px-1.5 font-mono text-[10px] leading-none whitespace-nowrap text-success/80 hover:border-success/40 hover:bg-success/10 hover:text-success"
                title="Allow this AND every future call with the same arguments for the rest of this chat. (⇧↵)"
                @click="respond('allow_session')"
              >Allow&nbsp;always</button>
              <button
                type="button"
                class="flex-1 rounded border border-transparent bg-background px-1.5 font-mono text-[10px] leading-none whitespace-nowrap text-destructive/75 hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
                title="Deny this AND every future call with the same arguments for the rest of this chat."
                @click="respond('deny_session')"
              >Deny&nbsp;always</button>
              <button
                type="button"
                class="flex-1 rounded border border-border bg-background px-1.5 font-mono text-[11px] leading-none whitespace-nowrap hover:border-destructive/40 hover:bg-destructive/5 hover:text-destructive"
                title="Deny this single call. Pi will ask again next time. (esc)"
                @click="respond('deny_once')"
              >Deny</button>
            </div>
            <!-- Keyboard hint strip — half-height, dimmed, non-clickable.
                 Aligned to the buttons above so each shortcut sits
                 directly under its action. Skipped on touch devices
                 via the no-hover media query. -->
            <div
              class="mt-0.5 hidden h-3 items-center gap-1 font-mono text-[9px] uppercase tracking-wide text-muted-foreground/60 sm:flex"
              aria-hidden="true"
            >
              <span class="flex-1 text-center">↵</span>
              <span class="flex-1 text-center">⇧↵</span>
              <span class="flex-1 text-center">&nbsp;</span>
              <span class="flex-1 text-center">esc</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
