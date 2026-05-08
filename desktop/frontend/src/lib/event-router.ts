/**
 * RPC event → ChatMessage[] reducer.
 *
 * Source of truth for event shapes (ground truth, captured live from
 * pi 0.73 + the patched anthropic-vertex provider):
 *
 *   message_update.assistantMessageEvent.type ∈
 *     | "text_start" | "text_delta"        | "text_end"
 *     | "thinking_start" | "thinking_delta"| "thinking_end"
 *     | "toolcall_start"                            ← NOTE: no underscore in "tool"
 *     | "toolcall_delta"                            ← partial.content[idx].arguments is
 *                                                    progressively parsed for us
 *     | "toolcall_end"                              ← carries full toolCall object
 *
 *   tool_execution_start { toolCallId, toolName }
 *   tool_execution_end   { toolCallId, toolName, isError, result: { content[] } }
 *   (tool_execution_update DOES fire — for `bash`. Not for `write`/`read`/`edit`.)
 *
 * Design:
 *   • Mutate the SAME reactive() ToolCall object as deltas arrive so Vue's
 *     reactivity tracks streaming changes (not new array refs every event).
 *   • For tools where partial parsing matters (write, edit), expose
 *     `args` as the latest progressively-parsed object — never the raw
 *     concatenated JSON string.
 *   • Side-effects (e.g. updating the editor pane) live in the store, not
 *     here. This file is pure: events in, ChatMessage tree out.
 */

import { reactive } from "vue";
import type {
  AssistantMessage,
  AssistantPart,
  ChatMessage,
  RpcEvent,
  ToolCall,
  UserMessage,
} from "../types/rpc";

export interface RouterState {
  messages: ChatMessage[];
  /** toolCallId → ToolCall ref (lives inside the assistant message it belongs to). */
  toolCallIndex: Map<string, ToolCall>;
  /**
   * Per-assistant-message cursors for the currently-open thinking/text parts.
   * Reset to null whenever an event from another channel arrives so the next
   * thinking/text delta starts a NEW part. Keyed by assistant message id.
   */
  activeThinking: Map<string, AssistantPart & { kind: "thinking" }>;
  activeText: Map<string, AssistantPart & { kind: "text" }>;
}

export function createRouterState(): RouterState {
  return {
    messages: [],
    toolCallIndex: new Map(),
    activeThinking: new Map(),
    activeText: new Map(),
  };
}

/** Push the user's prompt as a bubble immediately so the UI feels snappy. */
export function pushUserMessage(state: RouterState, text: string, id: string): void {
  const msg: UserMessage = reactive({ kind: "user", id, text });
  state.messages = [...state.messages, msg];
}

function ensureCurrentAssistant(state: RouterState): AssistantMessage {
  const last = state.messages[state.messages.length - 1];
  if (last && last.kind === "assistant" && !last.done) {
    return last;
  }
  const fresh: AssistantMessage = reactive({
    kind: "assistant",
    id: `asst-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    parts: [],
    text: "",
    thinking: "",
    toolCalls: [],
    done: false,
  });
  state.messages = [...state.messages, fresh];
  return fresh;
}

/**
 * Close the active thinking part for `asst` (so the next thinking delta
 * starts a fresh "Thought for Xs" block). Stamps endedAt for duration UI.
 */
function closeActiveThinking(state: RouterState, asst: AssistantMessage): void {
  const active = state.activeThinking.get(asst.id);
  if (active && active.endedAt === undefined) {
    active.endedAt = Date.now();
  }
  state.activeThinking.delete(asst.id);
}

function closeActiveText(state: RouterState, asst: AssistantMessage): void {
  state.activeText.delete(asst.id);
}

type ThinkingPart = Extract<AssistantPart, { kind: "thinking" }>;
type TextPart = Extract<AssistantPart, { kind: "text" }>;
type ToolPart = Extract<AssistantPart, { kind: "tool" }>;

function _appendThinkingDelta(
  state: RouterState,
  asst: AssistantMessage,
  delta: string,
): void {
  if (!delta) return;
  closeActiveText(state, asst);
  const existing = state.activeThinking.get(asst.id);
  const active: ThinkingPart =
    existing ??
    (reactive({
      kind: "thinking",
      id: `think-${asst.id}-${asst.parts.length}`,
      text: "",
      startedAt: Date.now(),
    }) as ThinkingPart);
  if (!existing) {
    asst.parts = [...asst.parts, active];
    state.activeThinking.set(asst.id, active);
  }
  active.text += delta;
  asst.thinking += delta;
}

function _appendTextDelta(
  state: RouterState,
  asst: AssistantMessage,
  delta: string,
): void {
  if (!delta) return;
  closeActiveThinking(state, asst);
  const existing = state.activeText.get(asst.id);
  const active: TextPart =
    existing ??
    (reactive({
      kind: "text",
      id: `text-${asst.id}-${asst.parts.length}`,
      text: "",
    }) as TextPart);
  if (!existing) {
    asst.parts = [...asst.parts, active];
    state.activeText.set(asst.id, active);
  }
  active.text += delta;
  asst.text += delta;
}

function _appendToolCallPart(
  asst: AssistantMessage,
  state: RouterState,
  call: ToolCall,
): void {
  closeActiveThinking(state, asst);
  closeActiveText(state, asst);
  if (asst.parts.some((p) => p.kind === "tool" && p.id === call.id)) return;
  const part = reactive({ kind: "tool", id: call.id, call }) as ToolPart;
  asst.parts = [...asst.parts, part];
}

/**
 * Extract the progressively-parsed `arguments` object for a toolcall delta.
 * pi-ai's parseStreamingJson already builds this for us on every chunk; we
 * just have to find the right block in `partial.content[]`.
 */
function pickPartialArguments(
  partial: any,
  contentIndex: number | undefined
): Record<string, unknown> | undefined {
  if (!partial || typeof partial !== "object") return undefined;
  const content = (partial as any).content;
  if (!Array.isArray(content)) return undefined;
  const idx = typeof contentIndex === "number" ? contentIndex : content.length - 1;
  const block = content[idx];
  if (!block || block.type !== "toolCall") return undefined;
  const args = block.arguments;
  if (args && typeof args === "object") return args as Record<string, unknown>;
  return undefined;
}

function pickPartialJsonRaw(
  partial: any,
  contentIndex: number | undefined
): string | undefined {
  if (!partial || typeof partial !== "object") return undefined;
  const content = (partial as any).content;
  if (!Array.isArray(content)) return undefined;
  const idx = typeof contentIndex === "number" ? contentIndex : content.length - 1;
  const block = content[idx];
  if (!block || block.type !== "toolCall") return undefined;
  if (typeof block.partialJson === "string") return block.partialJson;
  return undefined;
}

function upsertToolCall(
  state: RouterState,
  asst: AssistantMessage,
  id: string,
  init?: Partial<ToolCall>
): ToolCall {
  let call = state.toolCallIndex.get(id);
  if (call) return call;
  call = reactive({
    id,
    name: "tool",
    args: undefined,
    argsPartial: "",
    status: "pending",
    ...init,
  } as ToolCall);
  asst.toolCalls = [...asst.toolCalls, call];
  state.toolCallIndex.set(id, call);
  // Insert as an ordered "tool" part so renderers can interleave it with
  // thinking/text in the order pi emitted them.
  _appendToolCallPart(asst, state, call);
  return call;
}

export function applyEvent(state: RouterState, evt: RpcEvent): void {
  switch (evt.type) {
    case "agent_start":
    case "turn_start": {
      ensureCurrentAssistant(state);
      return;
    }

    case "message_update": {
      const sub: any = (evt as any).assistantMessageEvent;
      if (!sub || typeof sub !== "object") return;
      const asst = ensureCurrentAssistant(state);

      switch (sub.type) {
        case "text_delta":
          _appendTextDelta(state, asst, String(sub.delta ?? ""));
          return;

        case "text_end":
          closeActiveText(state, asst);
          return;

        case "thinking_delta":
          _appendThinkingDelta(state, asst, String(sub.delta ?? ""));
          return;

        case "thinking_end":
          closeActiveThinking(state, asst);
          return;

        // ── tool call lifecycle (correct event names: toolcall_*, no underscore) ──
        case "toolcall_start": {
          // partial.content[contentIndex] is the toolCall block; pull id+name from it.
          const block = pickToolCallBlock(sub.partial, sub.contentIndex);
          const id: string =
            (typeof block?.id === "string" && block.id) ||
            `tc-${Date.now()}-${asst.toolCalls.length}`;
          const name: string =
            (typeof block?.name === "string" && block.name) || "tool";

          upsertToolCall(state, asst, id, {
            name,
            status: "pending",
          });
          return;
        }

        case "toolcall_delta": {
          const block = pickToolCallBlock(sub.partial, sub.contentIndex);
          if (!block || typeof block.id !== "string") return;
          const call = upsertToolCall(state, asst, block.id, {
            name: typeof block.name === "string" ? block.name : "tool",
          });
          // pi-ai already parsed the partial JSON for us — use it directly.
          const args = pickPartialArguments(sub.partial, sub.contentIndex);
          if (args !== undefined) call.args = args;
          const raw = pickPartialJsonRaw(sub.partial, sub.contentIndex);
          if (raw !== undefined) call.argsPartial = raw;
          return;
        }

        case "toolcall_end": {
          const tc = sub.toolCall;
          const id: string | undefined = tc?.id;
          if (!id) return;
          const call = upsertToolCall(state, asst, id, {
            name: typeof tc?.name === "string" ? tc.name : "tool",
          });
          if (tc?.arguments && typeof tc.arguments === "object") {
            call.args = tc.arguments;
          }
          // status stays "pending" until tool_execution_start flips it.
          return;
        }

        // Legacy / variant names — keep as fallbacks for safety.
        case "tool_call_start":
        case "tool_call_delta":
        case "tool_call_end":
          // Same handlers as the toolcall_* path; these names show up in some
          // pi-ai variants. Re-dispatch by rewriting type and recursing.
          applyEvent(state, {
            ...(evt as any),
            assistantMessageEvent: {
              ...sub,
              type: sub.type.replace("tool_call", "toolcall"),
            },
          } as any);
          return;

        default:
          return;
      }
    }

    case "tool_execution":
    case "tool_execution_start": {
      const id: string | undefined = (evt as any).toolCallId;
      if (!id) return;
      const asst = ensureCurrentAssistant(state);
      // Tool execution starting → any still-open thinking/text part is over.
      closeActiveThinking(state, asst);
      closeActiveText(state, asst);
      const call = upsertToolCall(state, asst, id, {
        name: String((evt as any).toolName ?? "tool"),
      });
      // Lazy-fill args if no toolcall_delta arrived first (defensive).
      const args = (evt as any).args ?? (evt as any).arguments;
      if (call.args === undefined && args !== undefined) call.args = args;
      call.status = "running";
      if (call.startedAt === undefined) call.startedAt = Date.now();
      return;
    }

    case "tool_execution_update": {
      // pi's `bash` tool throttle-emits cumulative stdout snapshots
      // (~10×/sec). The payload key is `partialResult.content` (NOT
      // `result.content` — that name only appears on `_end`). Verified
      // against pi-mono-main/packages/coding-agent/docs/rpc.md and a live
      // WS probe. Other tools never send this event.
      const id: string | undefined = (evt as any).toolCallId;
      if (!id) return;
      const call = state.toolCallIndex.get(id);
      if (!call) return;
      const partial = (evt as any).partialResult ?? (evt as any).result ?? {};
      const content = Array.isArray(partial.content)
        ? partial.content
        : Array.isArray((evt as any).content)
        ? (evt as any).content
        : [];
      const text = content
        .filter((c: any) => c.type === "text" && typeof c.text === "string")
        .map((c: any) => c.text as string)
        .join("");
      // Snapshot semantics: pi sends the full cumulative output every
      // time, so we overwrite — never append (appending duplicates).
      call.streamingOutput = text;
      return;
    }

    case "tool_execution_end":
    case "tool_result": {
      const id: string | undefined = (evt as any).toolCallId;
      if (!id) return;
      const call = state.toolCallIndex.get(id);
      if (!call) return;
      const isError = Boolean((evt as any).isError);
      const result = (evt as any).result ?? {};
      const rawContent = Array.isArray(result.content)
        ? result.content
        : Array.isArray((evt as any).content)
        ? (evt as any).content
        : [];
      const text = rawContent
        .filter((c: any) => c.type === "text" && typeof c.text === "string")
        .map((c: any) => c.text as string)
        .join("\n")
        .trim();
      call.status = isError ? "error" : "success";
      if (call.endedAt === undefined) call.endedAt = Date.now();
      call.result = {
        text,
        isError,
        raw: rawContent,
        details: result.details,
      };
      return;
    }

    case "message_end": {
      const message = (evt as any).message ?? {};
      const role = message.role;
      if (role && role !== "assistant") return;
      const usage = message.usage;
      const asst = ensureCurrentAssistant(state);
      if (usage) {
        asst.usage = {
          input: Number(usage.input ?? 0),
          output: Number(usage.output ?? 0),
          cacheRead: Number(usage.cacheRead ?? 0),
          cacheWrite: Number(usage.cacheWrite ?? 0),
          cost: Number(usage.cost?.total ?? 0),
        };
      }
      // Provider-side errors (Vertex 404, "Model not found for provider",
      // 429, network failures, etc.) arrive as a `message_end` whose
      // `message.stopReason === "error"` and `message.errorMessage`
      // carries the human-readable cause. Without this branch the chat
      // looks frozen with no visible response — exactly the silent-hang
      // bug we hit when picking a model the project lacks access to.
      // We stamp `asst.error` so the assistant bubble renders the
      // failure inline; the store's onMessage handler reads it back to
      // also drive the bottom banner.
      if (message.stopReason === "error" && message.errorMessage) {
        const msg = String(message.errorMessage);
        asst.error = msg;
        asst.done = true;
        closeActiveThinking(state, asst);
        closeActiveText(state, asst);
      }
      return;
    }

    case "agent_end": {
      const last = state.messages[state.messages.length - 1];
      if (last && last.kind === "assistant") {
        // Stamp the duration on any still-open thinking part so the UI
        // can render "Thought for Xs" instead of an open-ended counter.
        closeActiveThinking(state, last);
        closeActiveText(state, last);
        last.done = true;
      }
      return;
    }

    case "_bridge_error": {
      const asst = ensureCurrentAssistant(state);
      asst.error = String((evt as any).message ?? "Bridge error");
      asst.done = true;
      return;
    }

    default:
      return;
  }
}

function pickToolCallBlock(partial: any, contentIndex: number | undefined): any {
  if (!partial || typeof partial !== "object") return undefined;
  const content = (partial as any).content;
  if (!Array.isArray(content)) return undefined;
  const idx = typeof contentIndex === "number" ? contentIndex : content.length - 1;
  const block = content[idx];
  if (!block || block.type !== "toolCall") return undefined;
  return block;
}
