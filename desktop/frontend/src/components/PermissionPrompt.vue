<!--
  PermissionPrompt — inline tool-call approval card.

  Lives at the bottom-right of the chat pane (NOT a screen-blocking
  modal). Default state shows one line: "Digi Setu wants to …" + 4
  primary buttons. Click the chevron to expand for intent +
  command/diff preview. Cursor / Aider / Goose all use this pattern —
  the dialog never steals the screen.

  Decisions go back over the WS via chat.sendPermissionResponse, then
  we dequeue locally so the next pending request takes the slot.

  Keyboard (only when no editable element is focused):
    Esc          → deny_once       (safe default if user dismisses)
    Enter        → allow_once
    Shift+Enter  → allow_session   (= "always allow for this chat")
    a            → toggle expanded view (aider muscle memory)

  Typography: Inter (sans) for every label, button, and section
  caption. JetBrains Mono ONLY for the actual command/argument
  preview <pre> blocks where the user is reading literal shell
  syntax that must align character-by-character.
-->
<script setup lang="ts">
import { createPatch } from "diff";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { Icon } from "@iconify/vue";

import { useChatStore } from "../stores/chat";
import {
  normalizeMode,
  usePermissionsStore,
  type PermissionDecision,
} from "../stores/permissions";

import DiffView from "./tools/DiffView.vue";

const chat = useChatStore();
const permissions = usePermissionsStore();
const { t, te } = useI18n();

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

// Icons stay as a JS map (no translation needed for icon names).
const TOOL_ICONS: Record<string, string> = {
  bash: "codicon:terminal",
  write: "codicon:new-file",
  edit: "codicon:edit",
  process: "codicon:server-process",
  process_start: "codicon:server-process",
};

/** Resolve the natural-language tool action from the locale file.
 *  Falls back to "use <tool>" for any tool the locale doesn't list. */
function toolAction(tool: string): string {
  const key = `permission.prompt.tools.${tool}`;
  return te(key) ? t(key) : `use ${tool}`;
}

function toolIcon(tool: string): string {
  return TOOL_ICONS[tool] || "codicon:tools";
}

/** Render the permission-mode chip label for any mode ID — accepts
 *  canonical IDs (auto / ask / cautious) AND legacy aliases. */
function modeChip(mode: string): string {
  const canonical = normalizeMode(mode);
  return t(`permission.mode.${canonical}.label`);
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
              <div id="permission-title" class="truncate text-body">
                <span class="text-muted-foreground">{{ $t("permission.prompt.wantsTo") }}</span>
                <span class="ml-1 font-semibold">{{ toolAction(current.tool) }}</span>
                <span v-if="snippet()" class="ml-2 text-muted-foreground">·</span>
                <!-- The snippet IS code (a shell command or a path) so it
                     gets the mono treatment — but small, so it sits
                     comfortably inside the otherwise-Inter header. -->
                <span
                  v-if="snippet()"
                  class="ml-2 font-mono text-caption text-foreground/80"
                  :title="snippet()"
                >{{ snippet() }}</span>
              </div>
            </div>
            <!-- Mode chip lives in the header so the action row stays a
                 clean 4-button strip. Title-cased label so it reads as
                 a noun, not a wire token. -->
            <span
              class="shrink-0 rounded bg-muted/70 px-1.5 py-0.5 text-caption font-medium tracking-wide text-muted-foreground"
              :title="$t('permission.modeLabel', { mode: modeChip(current.mode) })"
            >{{ modeChip(current.mode) }}</span>
            <span
              v-if="permissions.pendingCount > 1"
              class="shrink-0 rounded bg-muted px-1.5 py-0.5 text-caption font-medium text-muted-foreground"
              :title="$t('common.moreQueued', { count: permissions.pendingCount - 1 })"
            >+{{ permissions.pendingCount - 1 }}</span>
            <button
              type="button"
              class="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              :title="expanded ? $t('permission.prompt.hideDetails') : $t('permission.prompt.showDetails')"
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
                <div class="mb-0.5 text-caption font-medium uppercase tracking-wide text-muted-foreground">
                  {{ $t("permission.prompt.intent") }}
                </div>
                <div class="whitespace-pre-wrap text-body leading-snug">
                  {{ current.intent }}
                </div>
              </section>

              <section
                v-if="current.tool === 'bash' || current.tool === 'process' || current.tool === 'process_start'"
                class="px-3 py-2"
              >
                <div class="mb-0.5 text-caption font-medium uppercase tracking-wide text-muted-foreground">
                  {{ $t("permission.prompt.command") }}
                </div>
                <pre class="whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-caption leading-snug">{{ commandText(current.input) }}</pre>
              </section>

              <section
                v-else-if="current.tool === 'write' || current.tool === 'edit'"
                class="px-3 py-2"
              >
                <div class="mb-0.5 flex items-baseline justify-between text-caption font-medium uppercase tracking-wide text-muted-foreground">
                  <span>{{ current.tool === "write" ? $t("permission.prompt.create") : $t("permission.prompt.modify") }}</span>
                  <span class="font-mono normal-case text-foreground/80">{{ fileTarget(current.input) }}</span>
                </div>
                <DiffView
                  v-if="current.preview && current.preview.kind === 'diff'"
                  :diff="unifiedDiff(current.preview.filePath, current.preview.oldText, current.preview.newText)"
                  :max-rows="20"
                  :max-diff-lines="600"
                />
                <pre v-else class="whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-caption leading-snug">{{ commandText(current.input) }}</pre>
              </section>

              <section v-else class="px-3 py-2">
                <div class="mb-0.5 text-caption font-medium uppercase tracking-wide text-muted-foreground">
                  {{ $t("permission.prompt.arguments") }}
                </div>
                <pre class="whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-caption leading-snug">{{ commandText(current.input) }}</pre>
              </section>
            </div>
          </div>

          <!-- Action row.
               Order (left → right): Allow · Always allow · Always deny · Deny.
               Allow leads because it's the hot-path action — most calls
               in Ask mode are routine and the user wants the click to
               land on the leftmost button without scanning the row.
               Deny stays anchored to the right as the safe escape.

               Keyboard:
                 ↵    → Allow once       (1st button)
                 ⇧↵   → Always allow     (2nd button)
                 esc  → Deny             (last button)
            -->
          <div class="border-t border-border bg-muted/20 px-2 py-1.5">
            <div class="flex h-7 items-stretch gap-1">
              <button
                type="button"
                class="flex-1 rounded border border-success/60 bg-success/15 px-1.5 text-caption font-semibold leading-none whitespace-nowrap text-success hover:bg-success/25"
                :title="$t('permission.prompt.buttons.allowTitle')"
                @click="respond('allow_once')"
              >{{ $t("permission.prompt.buttons.allow") }}</button>
              <button
                type="button"
                class="flex-1 rounded border border-transparent bg-background px-1.5 text-caption font-medium leading-none whitespace-nowrap text-success/80 hover:border-success/40 hover:bg-success/10 hover:text-success"
                :title="$t('permission.prompt.buttons.alwaysAllowTitle')"
                @click="respond('allow_session')"
              >{{ $t("permission.prompt.buttons.alwaysAllow") }}</button>
              <button
                type="button"
                class="flex-1 rounded border border-transparent bg-background px-1.5 text-caption font-medium leading-none whitespace-nowrap text-destructive/75 hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
                :title="$t('permission.prompt.buttons.alwaysDenyTitle')"
                @click="respond('deny_session')"
              >{{ $t("permission.prompt.buttons.alwaysDeny") }}</button>
              <button
                type="button"
                class="flex-1 rounded border border-border bg-background px-1.5 text-caption font-semibold leading-none whitespace-nowrap hover:border-destructive/40 hover:bg-destructive/5 hover:text-destructive"
                :title="$t('permission.prompt.buttons.denyTitle')"
                @click="respond('deny_once')"
              >{{ $t("permission.prompt.buttons.deny") }}</button>
            </div>
            <!-- Keyboard hint strip — half-height, dimmed, non-clickable.
                 Aligned to the buttons above so each shortcut sits
                 directly under its action. Skipped on touch devices
                 via the no-hover media query. -->
            <div
              class="mt-0.5 hidden h-3 items-center gap-1 text-caption uppercase tracking-wide text-muted-foreground/60 sm:flex"
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
