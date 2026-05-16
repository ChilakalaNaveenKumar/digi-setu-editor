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
 * the i18n layer can render as a friendly message.
 *
 * The function returns ONLY a category code. The raw upstream string
 * is NEVER part of the user-facing surface — it goes to console.warn
 * for our debugging only (see `applyEvent` callers that lookup
 * `errors.<code>` via i18n).
 *
 * Why pattern-match instead of relying on structured codes? Because
 * `pi`'s SDK passes the upstream provider's error verbatim into
 * `message.errorMessage` — we never see a typed code. Anthropic
 * returns `{type: "rate_limit_error", message: "..."}`, Vertex returns
 * gRPC-style `code: 429, message: "Resource has been exhausted..."`,
 * OpenAI returns `{code: "rate_limit_exceeded", message: "..."}`, and
 * pi flattens all three into a single English string. So we sniff
 * known substrings sourced from each vendor's official error doc:
 *
 *   - https://docs.anthropic.com/en/api/errors
 *   - https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/api-errors
 *   - https://ai.google.dev/gemini-api/docs/safety-settings  (finishReason)
 *   - https://platform.openai.com/docs/guides/error-codes
 *
 * Categories in priority order (first match wins):
 *
 *   provider_usage_policy     Anthropic AUP / "violates our Usage Policy"
 *   provider_safety_block     Gemini SAFETY / PROHIBITED_CONTENT / BLOCKLIST
 *   provider_context_too_large 413 / request_too_large / context window
 *   provider_billing          Anthropic 402 billing_error / payment failed
 *   provider_quota_exhausted  RESOURCE_EXHAUSTED + monthly quota / billing tier hit
 *   provider_rate_limit       429 / rate_limit_error
 *   provider_overloaded       529 overloaded_error / 5xx UNAVAILABLE / api_error
 *   provider_model_unavailable 404 not_found_error / model gated / publisher_model_not_found
 *   provider_auth             401 authentication_error / 403 permission_error / ADC missing
 *   provider_invalid_request  400 invalid_request_error / INVALID_ARGUMENT
 *   provider_timeout          504 timeout_error / DEADLINE_EXCEEDED
 *   provider_network          DNS / ECONNRESET / fetch failed
 *   provider_error            unknown — store renders generic "Something went wrong"
 */
export function categorizeProviderError(raw: string | undefined | null): {
  code: string;
} {
  const text = String(raw ?? "").trim();
  if (!text) return { code: "provider_error" };
  const lc = text.toLowerCase();

  // ── Anthropic Usage Policy (most user-visible block) ──────────
  // Pattern from real-world reports + official AUP block message.
  // See e.g. anthropics/claude-code#3035, #6060, #46575.
  if (
    /violates? (our )?usage policy|aup\.|anthropic\.com\/legal\/aup|unable to respond to this request/i.test(
      text,
    )
  ) {
    return { code: "provider_usage_policy" };
  }

  // ── Gemini safety / Vertex content filter ─────────────────────
  // finishReason values (from Gemini docs): SAFETY, PROHIBITED_CONTENT,
  // BLOCKLIST, RECITATION. Vertex sometimes flattens to "blocked by
  // safety settings".
  if (
    /\b(safety|prohibited_content|blocklist|recitation|blocked by safety|content filter|content[_\s-]?policy|harm[_\s-]?category)\b/i.test(
      text,
    )
  ) {
    return { code: "provider_safety_block" };
  }

  // ── Context / payload too large ───────────────────────────────
  // Anthropic: 413 request_too_large (32 MB cap).
  // Anthropic / OpenAI: "maximum context length is N tokens".
  if (
    /(request_too_large|payload too large|\b413\b|context[_\s-]?length|context[_\s-]?window|maximum (context|tokens?)|input is too long|prompt is too long)/i.test(
      lc,
    )
  ) {
    return { code: "provider_context_too_large" };
  }

  // ── Billing (Anthropic 402) ───────────────────────────────────
  if (/\b402\b|billing_error|payment[_\s-]?(failed|required)|insufficient_quota/i.test(lc)) {
    // OpenAI uses insufficient_quota for paid-account-out-of-credit
    // which is structurally a billing problem, not a rate limit.
    return { code: "provider_billing" };
  }

  // ── Per-second rate limit (vs monthly quota) ──────────────────
  // Anthropic: 429 rate_limit_error
  // Vertex:    429 RESOURCE_EXHAUSTED with retry-after under a minute
  // OpenAI:    rate_limit_exceeded
  //
  // Checked BEFORE quota_exhausted because Vertex's RESOURCE_EXHAUSTED
  // message ("Resource has been exhausted (e.g. check quota)") is
  // genuinely ambiguous between rate-limit and monthly-quota — only
  // the retry-after header tells them apart, and pi flattens that
  // out. Defaulting to rate-limit matches the more common case AND
  // gives advice ("wait a few seconds") that's safe for both: a true
  // monthly-quota hit will simply fail again and the user can switch
  // models.
  if (
    /\b429\b|rate[_\s-]?limit|too many requests|requests per (minute|second)|resource[_\s-]?exhausted/i.test(
      lc,
    )
  ) {
    return { code: "provider_rate_limit" };
  }

  // ── Quota / monthly tier exhausted (separate from per-second rate) ─
  // We only land here for messages that EXPLICITLY name a monthly /
  // credit / billing dimension — bare "resource has been exhausted"
  // already routed to rate_limit above.
  if (
    /(monthly quota|quota.*exceed|out of credits?|credit (limit|exhaust))/i.test(lc)
  ) {
    return { code: "provider_quota_exhausted" };
  }

  // ── Overloaded / 5xx outage ───────────────────────────────────
  // Anthropic: 529 overloaded_error, 500 api_error
  // Vertex:    503 UNAVAILABLE, 500 INTERNAL
  if (
    /\b5(00|02|03|29)\b|overloaded|api_error|service unavailable|temporarily unavailable|\bunavailable\b|server is (busy|overloaded)|try again later/i.test(
      lc,
    )
  ) {
    return { code: "provider_overloaded" };
  }

  // ── Model gated / unavailable ─────────────────────────────────
  // Anthropic: not_found_error
  // Vertex:    "Publisher Model ... not found", "model is not supported in region"
  if (
    /not_found_error|model.*not[_\s-]?(found|enabled|supported)|publisher.?model.*not found|model.*does not exist|access denied to model|location is not supported|region.*not[_\s-]?support/i.test(
      lc,
    )
  ) {
    return { code: "provider_model_unavailable" };
  }

  // ── Auth / permission ─────────────────────────────────────────
  // Anthropic: 401 authentication_error, 403 permission_error
  // Vertex:    UNAUTHENTICATED, PERMISSION_DENIED, ADC errors
  if (
    /\b401\b|\b403\b|authentication_error|permission_error|permission_denied|unauthenticated|invalid[_\s-]?api[_\s-]?key|invalid_authentication|expired[_\s-]?credentials|application[_\s-]?default[_\s-]?credentials|\badc\b/i.test(
      lc,
    )
  ) {
    return { code: "provider_auth" };
  }

  // ── Bad request ───────────────────────────────────────────────
  if (
    /\b400\b|\b422\b|invalid_request_error|invalid_argument|failed_precondition|bad request|malformed|unprocessable_entity/i.test(
      lc,
    )
  ) {
    return { code: "provider_invalid_request" };
  }

  // ── Timeout ───────────────────────────────────────────────────
  if (/\b504\b|timeout_error|deadline_exceeded|timed out|request timeout/i.test(lc)) {
    return { code: "provider_timeout" };
  }

  // ── Network ───────────────────────────────────────────────────
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
      // WS probe.
      //
      // The stock `subagent` extension also rides this event: on every
      // child `message_end` / `tool_result_end` it calls `onUpdate({
      // content, details })` (see pi-mono-main subagent/index.ts:284 →
      // emitUpdate). The `details` payload is the same `SubagentDetails`
      // shape that lands in `call.result.details` on `_end`, just
      // mid-flight. Without forwarding it here the SubagentLivePanel
      // would sit on its skeleton "spawning child agent — first turn
      // lands in a moment…" until the WHOLE chain finishes, even though
      // every intermediate turn was already on the wire.
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
      // Forward structured progress (subagent transcripts, future
      // tools that want incremental UIs) to `call.result.details` so
      // reactive views re-render mid-flight. Tools that don't ship
      // `details` (bash, write, edit, read) are unaffected — we only
      // mutate when the field is actually present.
      if (partial.details !== undefined) {
        if (!call.result) {
          call.result = {
            text: "",
            isError: false,
            raw: [],
            details: partial.details,
          };
        } else {
          call.result.details = partial.details;
        }
      }
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
      // Preserve the most recent `details` we already accumulated from
      // tool_execution_update if the END payload doesn't carry them.
      // The stock `subagent` extension always returns `details` on its
      // final result, but custom extensions may not — and even for
      // subagent we'd rather defensively keep the last good snapshot
      // than null-out the SubagentLivePanel's transcript when an event
      // arrives without that field.
      const priorDetails =
        call.result && (call.result as { details?: unknown }).details !== undefined
          ? (call.result as { details?: unknown }).details
          : undefined;
      call.result = {
        text,
        isError,
        raw: rawContent,
        details: result.details !== undefined ? result.details : priorDetails,
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
        const raw = String(message.errorMessage);
        // Categorise upstream provider errors (Anthropic 429, Vertex
        // safety block, OpenAI insufficient_quota, …) and stamp ONLY
        // the stable code. The store's _localiseError helper turns
        // the code into a friendly user-visible message; the raw
        // upstream text is logged to the console for our debugging
        // and NEVER reaches the chat UI.
        const { code } = categorizeProviderError(raw);
        try {
          // eslint-disable-next-line no-console
          console.warn(
            `[chat] provider error category=${code} raw=${JSON.stringify(raw)}`,
          );
        } catch {
          /* console may be unavailable in some contexts */
        }
        asst.errorCode = code;
        // Leave `asst.error` empty — the store fills it in with the
        // localised message once it processes this tick. AssistantMessage.vue
        // only renders when `asst.error` is non-empty so there's no
        // visible flash of empty state.
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
      // _bridge_error always carries a stable `code` from the backend
      // (services/error_codes.py + services/relay_bridge.py). Stamp
      // ONLY the code; the store's _localiseError helper renders the
      // friendly i18n message. We deliberately drop `evt.message` so
      // a backend that accidentally leaks a stack trace or an HTTP
      // status code still results in a friendly, localised UI.
      const rawCode = (evt as any).code;
      const rawMsg = (evt as any).message;
      try {
        // eslint-disable-next-line no-console
        console.warn(
          `[chat] bridge error code=${String(rawCode ?? "internal")} ` +
            `raw=${JSON.stringify(rawMsg ?? "")}`,
        );
      } catch {
        /* console may be unavailable */
      }
      asst.errorCode = typeof rawCode === "string" && rawCode ? rawCode : "internal";
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
