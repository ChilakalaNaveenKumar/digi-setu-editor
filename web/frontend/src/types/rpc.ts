/**
 * RPC event types streamed by `pi --mode rpc`.
 *
 * Source of truth: pi-mono-main/packages/coding-agent/docs/rpc.md +
 * the AssistantMessageEventStream definitions in pi-ai. We intentionally
 * keep this loose (most fields are `unknown`) — the UI only narrows the
 * fields it actually renders. Anything we don't recognize is rendered as
 * a fallback debug row, never crashes.
 */

export interface RpcSessionEvent {
  type: "session";
  id: string;
  cwd: string;
  // a few more fields exist (model, etc.) — read on demand.
  [k: string]: unknown;
}

export interface RpcAgentLifecycleEvent {
  type: "agent_start" | "agent_end" | "turn_start" | "turn_end";
  [k: string]: unknown;
}

export interface RpcMessageStartEvent {
  type: "message_start";
  message?: { role?: "user" | "assistant" | "tool" };
  [k: string]: unknown;
}

export interface RpcMessageEndEvent {
  type: "message_end";
  message?: {
    role?: string;
    usage?: {
      input?: number;
      output?: number;
      cacheRead?: number;
      cacheWrite?: number;
      cost?: { total?: number };
    };
  };
  [k: string]: unknown;
}

export type AssistantMessageEvent =
  | { type: "text_delta"; delta: string }
  | { type: "thinking_delta"; delta: string }
  | { type: "tool_call_start"; toolName: string; toolCallId?: string }
  | { type: "tool_call_delta"; delta?: string; toolCallId?: string }
  | { type: "tool_call_end"; toolCallId?: string; toolName?: string; arguments?: unknown }
  | { type: string; [k: string]: unknown };

export interface RpcMessageUpdateEvent {
  type: "message_update";
  assistantMessageEvent: AssistantMessageEvent;
}

export interface RpcToolExecutionEvent {
  type:
    | "tool_execution_start"
    | "tool_execution_update"
    | "tool_execution_end"
    | "tool_execution"
    | "tool_result";
  toolName?: string;
  toolCallId?: string;
  arguments?: unknown;
  args?: unknown;
  content?: Array<{ type: string; text?: string; data?: string; mimeType?: string }>;
  isError?: boolean;
  [k: string]: unknown;
}

export interface RpcResponseEvent {
  type: "response";
  id?: string;
  command: string;
  success: boolean;
  data?: unknown;
}

export interface RpcBridgeError {
  type: "_bridge_error";
  message: string;
}

/** Pushed by the backend WorkspaceWatcher whenever workspace files change. */
export interface RpcFsChangeEvent {
  type: "fs_change";
  events: Array<{
    kind: "created" | "modified" | "deleted" | "moved";
    path: string;
    is_dir: boolean;
    src?: string; // for "moved": old path
  }>;
}

export type RpcEvent =
  | RpcSessionEvent
  | RpcAgentLifecycleEvent
  | RpcMessageStartEvent
  | RpcMessageEndEvent
  | RpcMessageUpdateEvent
  | RpcToolExecutionEvent
  | RpcResponseEvent
  | RpcBridgeError
  | RpcFsChangeEvent
  | { type: string; [k: string]: unknown };

/** A workspace file or directory entry as returned by `GET /api/files`. */
export interface FileEntry {
  path: string; // workspace-relative posix path
  is_dir: boolean;
  size: number;
  mtime: number;
}

// ── Render-ready domain model (built by event-router) ───────────────────────

export interface UserMessage {
  kind: "user";
  id: string;
  text: string;
}

export interface ToolCall {
  id: string; // toolCallId
  name: string;
  /**
   * The tool's args, progressively parsed by pi-ai's parseStreamingJson on
   * every `toolcall_delta`. So even mid-stream you can read `args.path` for
   * a `write` call as soon as the LLM has emitted the path key.
   */
  args: unknown;
  /** Raw partial JSON string (rarely needed; expose for debugging). */
  argsPartial: string;
  status: "pending" | "running" | "success" | "error";
  /**
   * Cumulative stdout/stderr from `tool_execution_update` events. pi sends
   * full snapshots (not deltas) ~10×/sec while a `bash` call is running, so
   * we just overwrite this on every update — no concatenation needed.
   * Empty for non-streaming tools (write/edit/read).
   */
  streamingOutput?: string;
  /** ms epoch when status flipped to "running" (tool_execution_start). */
  startedAt?: number;
  /** ms epoch when status flipped to "success"/"error" (tool_execution_end). */
  endedAt?: number;
  result?: {
    text: string;
    isError: boolean;
    raw: Array<{ type: string; text?: string; data?: string; mimeType?: string }>;
    /** Tool-specific structured details (e.g. `edit` includes `diff`, `firstChangedLine`). */
    details?: unknown;
  };
}

/**
 * Ordered "stream of consciousness" segment. The router builds an array of
 * these so the UI can render thought, prose, and tool calls in the SAME
 * order pi emitted them — and so a fresh thinking burst between two tool
 * calls is its own collapsible "Thought for 12s" block instead of being
 * merged with an earlier thought.
 */
export type AssistantPart =
  | {
      kind: "thinking";
      id: string;
      text: string;
      startedAt: number;
      endedAt?: number;
    }
  | {
      kind: "text";
      id: string;
      text: string;
    }
  | {
      kind: "tool";
      id: string; // toolCallId — same as the ToolCall it references
      call: ToolCall;
    };

export interface AssistantMessage {
  kind: "assistant";
  id: string;
  /**
   * Ordered parts the message is composed of. Source of truth for rendering.
   * `text`, `thinking`, `toolCalls` below are kept as derived convenience
   * accessors for legacy code paths (token totals, write-call lookup, etc.)
   * but the UI iterates `parts`.
   */
  parts: AssistantPart[];
  text: string;        // accumulated text deltas across all text parts
  thinking: string;    // accumulated thinking deltas across all thinking parts
  toolCalls: ToolCall[]; // mirror of all "tool" parts, in order
  done: boolean;
  usage?: {
    input: number;
    output: number;
    cacheRead: number;
    cacheWrite: number;
    cost: number;
  };
  error?: string;
}

export type ChatMessage = UserMessage | AssistantMessage;
