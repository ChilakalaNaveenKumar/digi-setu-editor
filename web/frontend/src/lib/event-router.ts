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

/**
 * Classify a raw provider error string into a stable category code
 * the i18n layer can render as a friendly user-facing message.
 *
 * The returned code is the ONLY thing the rest of the app should
 * surface — the raw upstream string is for our debugging (logged
 * via console.warn) and MUST NOT reach the UI.
 *
 * Pattern sources (real production strings, not guesses):
 *   - https://docs.anthropic.com/en/api/errors
 *   - https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/api-errors
 *   - https://ai.google.dev/gemini-api/docs/safety-settings  (finishReason)
 *   - https://platform.openai.com/docs/guides/error-codes
 *
 * Categories (priority order, first match wins):
 *
 *   provider_usage_policy     Anthropic AUP / "violates our Usage Policy"
 *   provider_safety_block     Gemini SAFETY / PROHIBITED_CONTENT / BLOCKLIST
 *   provider_context_too_large 413 / request_too_large / context window
 *   provider_billing          Anthropic 402 billing_error / OpenAI insufficient_quota
 *   provider_rate_limit       429 / rate_limit_error / RESOURCE_EXHAUSTED
 *   provider_quota_exhausted  monthly quota / out of credits (explicit)
 *   provider_overloaded       529 overloaded_error / 5xx UNAVAILABLE / api_error
 *   provider_model_unavailable 404 not_found_error / model gated
 *   provider_auth             401 / 403 / unauthenticated / bad ADC
 *   provider_invalid_request  400 invalid_request_error / INVALID_ARGUMENT
 *   provider_timeout          504 / timeout_error / DEADLINE_EXCEEDED
 *   provider_network          DNS / ECONNRESET / fetch failed
 *   provider_error            unknown — store renders generic "Something went wrong"
 *
 * NOTE: kept in sync (line-for-line) with the desktop fork at
 * desktop/frontend/src/lib/event-router.ts. Any pattern change here
 * MUST land in the desktop file the same commit.
 */
export function categorizeProviderError(raw: string | undefined | null): {
  code: string;
} {
  const text = String(raw ?? "").trim();
  if (!text) return { code: "provider_error" };
  const lc = text.toLowerCase();

  if (
    /violates? (our )?usage policy|aup\.|anthropic\.com\/legal\/aup|unable to respond to this request/i.test(
      text,
    )
  ) {
    return { code: "provider_usage_policy" };
  }
  if (
    /\b(safety|prohibited_content|blocklist|recitation|blocked by safety|content filter|content[_\s-]?policy|harm[_\s-]?category)\b/i.test(
      text,
    )
  ) {
    return { code: "provider_safety_block" };
  }
  if (
    /(request_too_large|payload too large|\b413\b|context[_\s-]?length|context[_\s-]?window|maximum (context|tokens?)|input is too long|prompt is too long)/i.test(
      lc,
    )
  ) {
    return { code: "provider_context_too_large" };
  }
  if (/\b402\b|billing_error|payment[_\s-]?(failed|required)|insufficient_quota/i.test(lc)) {
    return { code: "provider_billing" };
  }
  if (
    /\b429\b|rate[_\s-]?limit|too many requests|requests per (minute|second)|resource[_\s-]?exhausted/i.test(
      lc,
    )
  ) {
    return { code: "provider_rate_limit" };
  }
  if (/(monthly quota|quota.*exceed|out of credits?|credit (limit|exhaust))/i.test(lc)) {
    return { code: "provider_quota_exhausted" };
  }
  if (
    /\b5(00|02|03|29)\b|overloaded|api_error|service unavailable|temporarily unavailable|\bunavailable\b|server is (busy|overloaded)|try again later/i.test(
      lc,
    )
  ) {
    return { code: "provider_overloaded" };
  }
  if (
    /not_found_error|model.*not[_\s-]?(found|enabled|supported)|publisher.?model.*not found|model.*does not exist|access denied to model|location is not supported|region.*not[_\s-]?support/i.test(
      lc,
    )
  ) {
    return { code: "provider_model_unavailable" };
  }
  if (
    /\b401\b|\b403\b|authentication_error|permission_error|permission_denied|unauthenticated|invalid[_\s-]?api[_\s-]?key|invalid_authentication|expired[_\s-]?credentials|application[_\s-]?default[_\s-]?credentials|\badc\b/i.test(
      lc,
    )
  ) {
    return { code: "provider_auth" };
  }
  if (
    /\b400\b|\b422\b|invalid_request_error|invalid_argument|failed_precondition|bad request|malformed|unprocessable_entity/i.test(
      lc,
    )
  ) {
    return { code: "provider_invalid_request" };
  }
  if (/\b504\b|timeout_error|deadline_exceeded|timed out|request timeout/i.test(lc)) {
    return { code: "provider_timeout" };
  }
  if (
    /econnreset|enotfound|etimedout|enetunreach|fetch failed|network[_\s-]?error|socket hang up|getaddrinfo|dns lookup failed|tls handshake|ssl[_\s-]?alert|connection (reset|refused|closed|aborted)/i.test(
      lc,
    )
  ) {
    return { code: "provider_network" };
  }
  return { code: "provider_error" };
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
      const role = (evt as any).message?.role;
      if (role && role !== "assistant") return;
      const message = (evt as any).message ?? {};
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
      // Provider-side failure: pi finished the turn but stopped because
      // the upstream model returned an error envelope (Anthropic 429,
      // Vertex SAFETY, OpenAI insufficient_quota, …). The raw string is
      // useful for our diagnostics but MUST NOT reach the user — we
      // categorise it into a stable code and let the chat store
      // localise it via i18n.
      if (message.stopReason === "error") {
        const raw =
          typeof message.errorMessage === "string"
            ? message.errorMessage
            : typeof message.error === "string"
            ? message.error
            : "";
        if (raw) {
          // eslint-disable-next-line no-console
          console.warn("[chat] provider error (raw, suppressed in UI):", raw);
        }
        const { code } = categorizeProviderError(raw);
        asst.errorCode = code;
        // Leave asst.error empty here — the store fills it with the
        // localised string so unit tests for this reducer don't have
        // to depend on i18n being initialised.
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
      // Server emits {type:"_bridge_error", code, message}. The `code`
      // is our stable contract (see services/error_codes.py); the
      // `message` is for our logs only — the SPA ALWAYS renders the
      // i18n string keyed off `code`, never the raw server text.
      const code = String((evt as any).code ?? "internal");
      const raw = (evt as any).message;
      if (raw) {
        // eslint-disable-next-line no-console
        console.warn(`[chat] bridge_error code=${code} (raw, suppressed in UI):`, raw);
      }
      const asst = ensureCurrentAssistant(state);
      asst.errorCode = code;
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
