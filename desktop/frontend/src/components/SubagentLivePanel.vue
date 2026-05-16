<!--
  SubagentLivePanel — right-side drawer that renders the LIVE transcript
  of a subagent (or set of parallel/chain subagents) as it streams.

  Why a separate panel and not just expanding the card inline:
    - Subagent transcripts are long (whole sub-runs with their own
      thinking + tool calls + final text). Inlining them in the parent
      chat scroll buries the parent's own messages.
    - The user explicitly asked for a "tab structure like desktop where
      multiple terminals are shown" — so for parallel mode each child
      gets its own tab at the top of this panel.
    - Pi's subagent extension calls `onUpdate(...)` on every
      `message_end`/`tool_result_end` of the child (see
      pi-coding-agent/examples/extensions/subagent/index.ts#emitUpdate),
      which lands in `call.result.details.results[*].messages` reactively
      via our existing event-router. So we don't need new SSE wiring —
      we just have to render it nicely.

  Rendering parity with the main chat:
    The pi-ai messages this panel receives have the SAME shape pi emits
    for the parent run (assistant content with thinking/text/toolCall +
    standalone toolResult messages). To get pixel-identical "feels like
    the main thread" rendering — ToolCardDispatch tool cards, markdown
    text with copy-buttons on fenced code, ThinkingBlock with timer —
    we map each pi-ai assistant message to our local `AssistantMessage`
    shape, fold each toolResult's content into the matching ToolCall's
    `result`, and hand the whole list off to <AssistantMessage>. No
    custom bubble HTML; no drift between subagent UI and main chat UI.

  Closing logic: ESC, click outside, click X, or open() with a
  different id (the store handles single-instance via openCallId).
-->
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { useChatStore } from "../stores/chat";
import { useSubagentPanelStore } from "../stores/subagent-panel";
import type {
  AssistantMessage as UiAssistantMessage,
  AssistantPart as UiAssistantPart,
  ToolCall as UiToolCall,
} from "../types/rpc";
import AssistantMessage from "./AssistantMessage.vue";

// ── Local mirrors of pi-ai's Message shape (avoid pulling pi-ai
// types into the frontend just for two interfaces). Keep field
// names byte-identical to pi-ai/dist/types.d.ts so future drift is
// caught by TS. ─────────────────────────────────────────────────────
interface PiTextContent {
  type: "text";
  text: string;
}
interface PiThinkingContent {
  type: "thinking";
  thinking: string;
}
interface PiImageContent {
  type: "image";
  data: string;
  mimeType: string;
}
interface PiToolCallContent {
  type: "toolCall";
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}
type PiAssistantContent = PiTextContent | PiThinkingContent | PiToolCallContent;
type PiUserContent = PiTextContent | PiImageContent;

interface PiUserMessage {
  role: "user";
  content: string | PiUserContent[];
}
interface PiAssistantMessage {
  role: "assistant";
  content: PiAssistantContent[];
  model?: string;
  usage?: {
    input?: number;
    output?: number;
    cacheRead?: number;
    cacheWrite?: number;
    totalTokens?: number;
    cost?: { total?: number };
  };
  stopReason?: string;
  errorMessage?: string;
}
interface PiToolResultMessage {
  role: "toolResult";
  toolCallId: string;
  toolName: string;
  content: (PiTextContent | PiImageContent)[];
  isError?: boolean;
}
type PiMessage = PiUserMessage | PiAssistantMessage | PiToolResultMessage;

interface SubagentResult {
  agent: string;
  agentSource?: string;
  task: string;
  exitCode: number;
  stopReason?: string;
  errorMessage?: string;
  usage?: {
    input?: number;
    output?: number;
    cacheRead?: number;
    cacheWrite?: number;
    cost?: number;
    turns?: number;
  };
  model?: string;
  messages?: PiMessage[];
}

interface SubagentDetails {
  mode: "single" | "chain" | "parallel";
  results: SubagentResult[];
}

const chat = useChatStore();
const panelStore = useSubagentPanelStore();
const { messages, isAborting } = storeToRefs(chat);
const { openCallId } = storeToRefs(panelStore);

/**
 * Walk chat.messages to find the ToolCall whose id matches openCallId.
 * We don't use the router's toolCallIndex Map because it isn't exported
 * from the store — and iterating is O(n_messages * n_parts), which for
 * a session of a few hundred messages is < 1ms anyway.
 */
const activeCall = computed<UiToolCall | null>(() => {
  const id = openCallId.value;
  if (!id) return null;
  for (const m of messages.value) {
    if (m.kind !== "assistant") continue;
    const am = m as UiAssistantMessage;
    for (const p of am.parts) {
      if (p.kind === "tool" && p.call.id === id) return p.call;
    }
  }
  return null;
});

const details = computed<SubagentDetails | null>(() => {
  const c = activeCall.value;
  if (!c) return null;
  const d = c.result?.details as SubagentDetails | undefined;
  if (!d || !Array.isArray(d.results)) {
    // Pre-update: extension hasn't emitted onUpdate yet. Show
    // skeleton from the call's args so the user sees SOMETHING the
    // moment they click — instead of an empty drawer for the 1-3 s
    // before the first turn lands.
    const a = c.args as
      | { agent?: string; task?: string; tasks?: Array<{ agent: string; task: string }>; chain?: Array<{ agent: string; task: string }> }
      | undefined;
    if (!a) return null;
    if (a.tasks && a.tasks.length > 0) {
      return {
        mode: "parallel",
        results: a.tasks.map((t) => ({
          agent: t.agent,
          task: t.task,
          exitCode: -1,
          messages: [],
        })),
      };
    }
    if (a.chain && a.chain.length > 0) {
      return {
        mode: "chain",
        results: a.chain.map((t) => ({
          agent: t.agent,
          task: t.task,
          exitCode: -1,
          messages: [],
        })),
      };
    }
    if (a.agent) {
      return {
        mode: "single",
        results: [{ agent: a.agent, task: a.task ?? "", exitCode: -1, messages: [] }],
      };
    }
    return null;
  }
  return d;
});

// ── Tab selection ──────────────────────────────────────────────────
// Auto-pick the first agent. If the user clicks another tab we
// remember it for as long as this card is open; switching to a
// different card resets to index 0. We also keep the tab valid if
// the underlying `results` array shrinks (shouldn't happen but cheap
// to guard against).
const selectedIndex = ref(0);

watch(
  () => openCallId.value,
  () => {
    selectedIndex.value = 0;
  },
);

const safeIndex = computed(() => {
  const d = details.value;
  if (!d || d.results.length === 0) return 0;
  return Math.min(Math.max(selectedIndex.value, 0), d.results.length - 1);
});

const activeResult = computed<SubagentResult | null>(() => {
  const d = details.value;
  if (!d) return null;
  return d.results[safeIndex.value] ?? null;
});

// ── Status helpers (match SubagentToolCard styling) ────────────────
function statusIcon(r: SubagentResult): string {
  if (r.exitCode === -1) return "codicon:loading";
  if (r.exitCode === 0) return "codicon:check";
  return "codicon:close";
}

function statusClass(r: SubagentResult): string {
  if (r.exitCode === -1) return "text-primary animate-spin";
  if (r.exitCode === 0) return "text-success";
  return "text-destructive";
}

function fmtCost(cost?: number): string {
  if (typeof cost !== "number" || cost === 0) return "";
  if (cost < 0.01) return `$${(cost * 1000).toFixed(2)}m`;
  return `$${cost.toFixed(2)}`;
}

// ── Map pi-ai Message[] → main-chat AssistantMessage[] ─────────────
// Each pi-ai assistant message becomes one synthetic AssistantMessage.
// Following toolResult messages are folded into the matching ToolCall's
// `result` so ToolCardDispatch sees the same `status` + `result.text` +
// `result.raw` shape it gets in the main thread. This is what gives us
// the bash/edit/read/grep cards "for free" inside subagents.
//
// Pi-ai routinely starts a subagent transcript with a `user` message
// (the seed task). We already render that as the dedicated TASK card
// above the transcript, so we skip user messages here to avoid showing
// the same prompt twice.
const syntheticMessages = computed<UiAssistantMessage[]>(() => {
  const r = activeResult.value;
  const msgs = r?.messages;
  if (!r || !msgs || msgs.length === 0) return [];

  const baseId = `${activeCall.value?.id ?? "sub"}-${safeIndex.value}`;
  const out: UiAssistantMessage[] = [];

  // We hand toolResults to the most-recently-built assistant message
  // by toolCallId. A toolResult that arrives BEFORE its matching
  // assistant message would be a pi protocol bug — log and ignore.
  let pendingTools = new Map<string, UiToolCall>();

  for (let i = 0; i < msgs.length; i++) {
    const m = msgs[i];

    if (m.role === "assistant") {
      const id = `${baseId}-a-${i}`;
      const parts: UiAssistantPart[] = [];
      const toolCalls: UiToolCall[] = [];
      let textBuf = "";
      let thinkingBuf = "";
      let pi = 0;

      for (const c of m.content) {
        if (c.type === "thinking") {
          parts.push({
            kind: "thinking",
            id: `${id}-th-${pi++}`,
            text: c.thinking,
            // We don't get real timestamps from a child run's
            // serialised messages — start = end means ThinkingBlock
            // shows "Thought" without a "for Xs" timer (it gracefully
            // degrades when startedAt === endedAt).
            startedAt: 0,
            endedAt: 0,
          });
          thinkingBuf += (thinkingBuf ? "\n\n" : "") + c.thinking;
        } else if (c.type === "text") {
          parts.push({ kind: "text", id: `${id}-tx-${pi++}`, text: c.text });
          textBuf += (textBuf ? "\n\n" : "") + c.text;
        } else if (c.type === "toolCall") {
          const tc: UiToolCall = {
            id: c.id,
            name: c.name,
            args: c.arguments,
            argsPartial: "",
            // We default to "running" so a tool call whose
            // matching toolResult hasn't been streamed yet shows
            // its in-flight spinner. As soon as the toolResult
            // lands below in this same loop we flip it to
            // success/error.
            status: "running",
          };
          parts.push({ kind: "tool", id: c.id, call: tc });
          toolCalls.push(tc);
          pendingTools.set(c.id, tc);
        }
      }

      const isLast = i === msgs.length - 1;
      out.push({
        kind: "assistant",
        id,
        parts,
        text: textBuf,
        thinking: thinkingBuf,
        toolCalls,
        // Mark the tail message as "still streaming" iff the whole
        // child run is still in flight. AssistantMessage uses `done`
        // to drive the pulsing caret on the last text part.
        done: !(isLast && r.exitCode === -1),
        usage: m.usage?.cost?.total != null
          ? {
              input: m.usage.input ?? 0,
              output: m.usage.output ?? 0,
              cacheRead: m.usage.cacheRead ?? 0,
              cacheWrite: m.usage.cacheWrite ?? 0,
              cost: m.usage.cost.total,
            }
          : undefined,
        error: m.errorMessage || undefined,
      });
    } else if (m.role === "toolResult") {
      const tc = pendingTools.get(m.toolCallId);
      if (!tc) continue;
      const text = m.content
        .filter((c): c is PiTextContent => c.type === "text")
        .map((c) => c.text)
        .join("\n");
      tc.result = {
        text,
        isError: m.isError === true,
        // Pass content through verbatim so cards that read images
        // (FilePreview-style) still see the raw payload.
        raw: m.content.map((c) =>
          c.type === "text"
            ? { type: "text", text: c.text }
            : { type: "image", data: c.data, mimeType: c.mimeType },
        ),
        details: undefined,
      };
      tc.status = m.isError ? "error" : "success";
      tc.endedAt = Date.now();
    }
    // user role: skipped — already rendered as the TASK card.
  }

  return out;
});

const hasAnyContent = computed(() => syntheticMessages.value.length > 0);

// ── Auto-scroll to bottom while streaming ──────────────────────────
// Only nudge to the bottom if the user is already near the bottom —
// otherwise we stomp on someone trying to read an earlier turn.
const scrollHost = ref<HTMLElement | null>(null);
const stickToBottom = ref(true);

function onScroll(): void {
  const el = scrollHost.value;
  if (!el) return;
  const slack = 80;
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < slack;
}

// Hash whatever can grow during a streamed update: number of synthetic
// messages, plus the last message's text+thinking+toolCall counts. Same
// pattern MessageList uses to keep the parent chat pinned.
watch(
  () => {
    const list = syntheticMessages.value;
    const last = list[list.length - 1];
    if (!last) return list.length;
    const completedTools = last.toolCalls.reduce(
      (n, t) => n + (t.status === "success" || t.status === "error" ? 1 : 0),
      0,
    );
    return (
      list.length * 1_000_000 +
      last.text.length +
      last.thinking.length +
      last.toolCalls.length * 1000 +
      completedTools
    );
  },
  async () => {
    if (!stickToBottom.value) return;
    await nextTick();
    const el = scrollHost.value;
    if (el) el.scrollTop = el.scrollHeight;
  },
);

// ── Close handlers ─────────────────────────────────────────────────
function close(): void {
  panelStore.close();
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Escape" && openCallId.value) {
    e.preventDefault();
    close();
  }
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

// ── Stop button ────────────────────────────────────────────────────
// Pi only supports turn-level abort (not per-subagent), so "Stop"
// here triggers the same chat.abort the composer's Stop pill uses.
// We label it "Stop turn" to make that explicit — the user is killing
// the whole parent run, which by SIGTERM-propagation also kills the
// subagent process. See chat.abort in stores/chat.ts.
//
// The "running" derivation is intentionally CHILD-FIRST, not
// parent-status-first: pi's stream sometimes delivers
// `tool_execution_update` AFTER `tool_execution_end` for the same
// toolCallId (the subagent extension fires a final emitUpdate
// synchronously from a child's last `message_end`, but pi marshals
// it through its post-stream pump so it can race the END envelope),
// and our event-router can lose the END flip in that race. Trusting
// `c.status === "running"` alone left a stale "Stop turn" pill on
// finished runs even though the footer correctly showed "✓ done".
//
// Logical truth: a subagent run is done iff every child has reported
// a final exitCode (≥ 0). When `details.results` is non-empty, that
// is the source of truth. Only when no `details.results` exist yet
// (pre-first-update skeleton) do we fall back to the parent's flag.
const isCallRunning = computed(() => {
  const c = activeCall.value;
  if (!c) return false;
  const results = details.value?.results;
  if (results && results.length > 0) {
    return results.some((r) => r.exitCode === -1);
  }
  return c.status === "running" || c.status === "pending";
});

function onStop(): void {
  void chat.abort();
}
</script>

<template>
  <!--
    No slide-in transition / no `absolute` positioning anymore. Earlier
    iterations rendered this as a 560 px right-side drawer overlay — but
    that hard-clamped the cards regardless of how wide the chat column
    was, and on a wide window the bash/edit cards overflowed the drawer
    while the rest of MessageList sat empty next to it. We now slot
    in-place where MessageList would be (see ChatPane.vue), so the
    transcript inherits the chat column's responsive width AND leaves
    Composer + PermissionPrompt + CompactionPill below it usable.

    Width/height sizing is intentionally identical to MessageList:
    `h-full w-full min-w-0 flex` — we want byte-identical layout so the
    user's eye doesn't track any geometry change when they open/close
    the panel.
  -->
  <Transition
    enter-active-class="transition-opacity duration-150 ease-out"
    leave-active-class="transition-opacity duration-100 ease-in"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <section
      v-if="openCallId && details"
      class="relative flex h-full w-full min-w-0 flex-col bg-background text-foreground"
      role="complementary"
      aria-label="Subagent live progress"
    >
      <!-- ── Header ─────────────────────────────────────────────── -->
      <header
        class="flex items-center gap-2 border-b border-border px-3 py-2"
      >
        <Icon icon="codicon:organization" class="h-4 w-4 text-primary" />
        <span class="text-caption uppercase tracking-wide text-muted-foreground">subagent</span>
        <span class="text-caption text-muted-foreground">·</span>
        <span class="truncate text-body font-mono text-foreground">
          {{
            details.mode === "parallel"
              ? `parallel · ${details.results.length} agents`
              : details.mode === "chain"
                ? `chain · ${details.results.length} steps`
                : (details.results[0]?.agent ?? "subagent")
          }}
        </span>
        <span class="flex-1"></span>

        <button
          v-if="isCallRunning || isAborting"
          type="button"
          :disabled="isAborting"
          :class="[
            'inline-flex items-center gap-1 rounded border px-2 py-0.5 text-caption',
            isAborting
              ? 'cursor-wait border-destructive/30 bg-destructive/5 text-destructive/80'
              : 'border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20',
          ]"
          :title="isAborting ? 'Stopping pi turn (and its subagents)…' : 'Stop the current pi turn (kills the subagent too)'"
          @click="onStop"
        >
          <Icon
            :icon="isAborting ? 'codicon:loading' : 'codicon:debug-stop'"
            :class="['h-3 w-3', isAborting && 'animate-spin']"
          />
          {{ isAborting ? "Stopping…" : "Stop turn" }}
        </button>

        <button
          type="button"
          class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          title="Close (Esc)"
          aria-label="Close subagent panel"
          @click="close"
        >
          <Icon icon="codicon:close" class="h-4 w-4" />
        </button>
      </header>

      <!-- ── Tabs (parallel/chain only) ─────────────────────────── -->
      <div
        v-if="details.results.length > 1"
        class="flex overflow-x-auto border-b border-border bg-muted/30"
        role="tablist"
      >
        <button
          v-for="(r, idx) in details.results"
          :key="idx"
          type="button"
          role="tab"
          :aria-selected="idx === safeIndex"
          :class="[
            'flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-1.5 text-caption transition-colors',
            idx === safeIndex
              ? 'border-primary bg-background text-foreground'
              : 'border-transparent text-muted-foreground hover:bg-muted/50 hover:text-foreground',
          ]"
          @click="selectedIndex = idx"
        >
          <Icon
            :icon="statusIcon(r)"
            :class="['h-3 w-3 shrink-0', statusClass(r)]"
          />
          <span class="font-mono">{{ r.agent }}</span>
        </button>
      </div>

      <!-- ── Body ──────────────────────────────────────────────── -->
      <!--
        We give the body the same horizontal padding (`px-5`) and
        background (`bg-background`) as MessageList so the embedded
        AssistantMessage renders identically to the parent thread —
        no double-card framing, no reduced contrast.
      -->
      <div
        ref="scrollHost"
        class="flex-1 overflow-y-auto px-5 pb-6 pt-3"
        @scroll.passive="onScroll"
      >
        <template v-if="activeResult">
          <!-- Task seed (rendered once at the top, equivalent to
               the main thread's first UserMessage). We do this
               manually instead of including a synthetic UserMessage
               because pi-ai sometimes emits the task as the first
               role:user message inside r.messages and sometimes
               only as the standalone `task` field — the dedicated
               card normalises both paths. -->
          <div class="my-5 rounded-lg border border-border bg-muted/40 px-4 py-3">
            <div class="mb-1 flex items-center gap-1.5 text-caption uppercase tracking-wide text-muted-foreground">
              <Icon icon="codicon:account" class="h-3 w-3" />
              task
              <span v-if="activeResult.agent" class="text-caption text-muted-foreground">· {{ activeResult.agent }}</span>
            </div>
            <div class="whitespace-pre-wrap break-words text-body text-foreground">
              {{ activeResult.task }}
            </div>
          </div>

          <!-- Main transcript: one <AssistantMessage> per pi-ai
               assistant message, with toolResults already folded
               into each ToolCall's `result`. ToolCardDispatch handles
               bash/edit/read/grep/ls/find/write/todo/subagent
               specialisation just like in the main chat. -->
          <AssistantMessage
            v-for="m in syntheticMessages"
            :key="m.id"
            :message="m"
          />

          <!-- Empty-state while we wait for first turn -->
          <div
            v-if="!hasAnyContent"
            class="mt-2 flex items-center gap-2 text-caption text-muted-foreground"
          >
            <Icon icon="codicon:loading" class="h-3.5 w-3.5 animate-spin" />
            spawning child agent — first turn lands in a moment…
          </div>

          <!-- Error footer if this child failed and didn't already
               include the error inside the assistant message. -->
          <div
            v-if="
              activeResult.errorMessage &&
                activeResult.exitCode !== 0 &&
                !syntheticMessages.some((m) => m.error === activeResult.errorMessage)
            "
            class="mt-2 rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-caption text-destructive"
          >
            {{ activeResult.errorMessage }}
          </div>
        </template>
      </div>

      <!-- ── Footer ──────────────────────────────────────────── -->
      <footer
        v-if="activeResult"
        class="flex items-center gap-3 border-t border-border bg-muted/30 px-3 py-1.5 text-caption text-muted-foreground"
      >
        <Icon
          :icon="statusIcon(activeResult)"
          :class="['h-3.5 w-3.5 shrink-0', statusClass(activeResult)]"
        />
        <span class="font-mono">
          {{
            activeResult.exitCode === -1
              ? "running"
              : activeResult.exitCode === 0
                ? "done"
                : "failed"
          }}
        </span>
        <span v-if="activeResult.model" class="truncate font-mono">· {{ activeResult.model }}</span>
        <span class="flex-1"></span>
        <span
          v-if="activeResult.usage?.turns"
          class="tabular-nums"
        >{{ activeResult.usage.turns }}t</span>
        <span
          v-if="fmtCost(activeResult.usage?.cost)"
          class="tabular-nums"
        >{{ fmtCost(activeResult.usage?.cost) }}</span>
      </footer>
    </section>
  </Transition>
</template>
