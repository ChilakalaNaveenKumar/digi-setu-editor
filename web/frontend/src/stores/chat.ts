/**
 * Chat lifecycle + event dispatcher (SSE transport).
 *
 * Replaces the old WebSocket store. Transport is now POST + SSE
 * (services/chat-stream.ts) and multi-tab is handled at the page
 * layer (services/tab-claim.ts), so this file no longer carries:
 *
 *   - WS reconnect / heartbeat / explicit-close state machine
 *   - parked-session bridges and snapshot restoration
 *   - "transient error grace period" flicker absorption
 *   - `_abortedAwaitingReconnect` race plumbing
 *   - `tabSuperseded` / kicked-tab handling
 *
 * What stays identical so component callsites don't have to change:
 *   - public surface (connect / disconnect / sendPrompt / abort /
 *     reconnect / sendPermissionResponse / queue API / totals…)
 *   - the `_dispatch` event reducer (router updates, billing, fs/bg
 *     fanout, permission gate, compaction state)
 *   - `lastError` / `lastErrorCode` shape used by the error card
 *
 * Compatibility shim: the bridge used to expose a 5-state union
 * `idle | connecting | open | closed | error`. ChatStream emits
 * 4 (no `error`) — this store synthesises `error` from `onError`
 * so existing UI checks (`connState === 'error'`) keep working.
 */

import { defineStore } from "pinia";
import { computed, reactive, ref, watch } from "vue";

import { fetchSessionHistory } from "../api/sessions";
import { i18n } from "../i18n";
import {
  applyEvent,
  createRouterState,
  pushUserMessage,
} from "../lib/event-router";
import { router as appRouter } from "../router";
import { ChatStream, ChatStreamError, type ChatStreamState } from "../services/chat-stream";
import type { AssistantMessage, ChatMessage, RpcEvent, ToolCall } from "../types/rpc";

import { useBillingStore } from "./billing";
import { useChatSessionStore } from "./chat-session";
import { useFilesStore } from "./files";
import { useModelsStore } from "./models";
import { usePermissionsStore, type PermissionDecision, type PermissionMode } from "./permissions";
import { useTerminalsStore } from "./terminals";
import { useWorkspaceStore } from "./workspace";

/** Public connection state (5-state for backwards compatibility). */
export type ConnState = ChatStreamState | "error";

const DEBUG_EVENTS =
  typeof window !== "undefined" && new URLSearchParams(window.location.search).has("debug");

interface SessionInfo {
  id: string;
  cwd?: string;
}

export interface PendingAttachment {
  localId: string;
  name: string;
  size: number;
  mime: string;
  path: string;
  agentPath: string;
}

export interface QueuedMessage {
  id: string;
  text: string;
  attachments: PendingAttachment[];
  createdAt: number;
}

/**
 * Translate a stable error code into a localised user-facing sentence.
 * Anything we don't have an explicit translation for collapses to
 * `errors.internal` so a raw upstream string never reaches the UI.
 */
function _localiseError(code: string | null | undefined): string {
  const c = String(code ?? "internal").trim() || "internal";
  const key = `errors.${c}`;
  if (i18n.global.te(key)) {
    return i18n.global.t(key) as string;
  }
  return i18n.global.t("errors.internal") as string;
}

export const useChatStore = defineStore("chat", () => {
  let router = createRouterState();
  const messages = ref<ChatMessage[]>([]);
  const session = ref<SessionInfo | null>(null);
  const connState = ref<ConnState>("idle");
  const isStreaming = ref(false);
  /**
   * Distinct from `isStreaming`. While the user has clicked Stop but
   * the backend hasn't confirmed yet, we sit in `isAborting`. The
   * composer keeps showing the Stop pill (now labelled "Stopping…")
   * so the user gets feedback that their click registered AND can
   * retry if needed — previously we flipped `isStreaming` to false
   * the instant the click happened, which made the pill vanish and
   * the user (correctly) concluded "Stop didn't work" when pi was
   * actually still wedged on a Vertex round-trip. Backend now has a
   * 4 s grace + force-kill escalation, so this state should resolve
   * within 4–5 s in the worst case; we add an 8 s frontend hard
   * fallback below just to make sure the UI never gets permanently
   * stuck if the abort POST itself fails.
   */
  const isAborting = ref(false);
  const lastError = ref<string | null>(null);
  const lastErrorCode = ref<string | null>(null);

  function _setError(code: string | null): void {
    if (!code) {
      lastError.value = null;
      lastErrorCode.value = null;
      return;
    }
    lastErrorCode.value = code;
    lastError.value = _localiseError(code);
  }
  function clearError(): void {
    _setError(null);
  }

  // Pi auto-compaction status (`compaction_start` / `compaction_end`
  // RPC events from pi-mono). Drives the "Summarising long history…"
  // pill and post-success badge. `null` = idle.
  interface CompactionState {
    active: boolean;
    reason: string;
    finishedAt: number | null;
    succeeded: boolean | null;
    errorMessage: string | null;
  }
  const compactionState = ref<CompactionState | null>(null);
  function dismissCompaction(): void {
    compactionState.value = null;
  }

  // Computed views consumed by ChatPane.vue. EventSource handles
  // transport-level retries silently, so "reconnecting" here just
  // means "we're in the connecting state with prior context to
  // come back to" — not a flicker-prone WS retry loop.
  const isReconnecting = computed(
    () => connState.value === "connecting" && messages.value.length > 0,
  );
  const isInitialConnecting = computed(
    () => connState.value === "connecting"
      && messages.value.length === 0
      && !lastErrorCode.value,
  );

  // Files the user attached but hasn't yet sent. The composer renders
  // chips; sendPrompt() consumes the list and prepends an "Attached
  // files:" preamble to the message body.
  const pendingAttachments = ref<PendingAttachment[]>([]);

  // Messages typed while pi was busy. The watcher below auto-fires
  // the head when isStreaming flips false.
  const queuedMessages = ref<QueuedMessage[]>([]);

  let stream: ChatStream | null = null;

  // ── session-scoped totals (monotonic display clamp) ─────────────────
  const _displayHigh = reactive({
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    cost: 0,
  });

  const totals = computed(() => {
    let input = 0,
      output = 0,
      cacheRead = 0,
      cacheWrite = 0,
      cost = 0;
    for (const m of messages.value) {
      if (m.kind !== "assistant" || !m.usage) continue;
      input += m.usage.input;
      output += m.usage.output;
      cacheRead += m.usage.cacheRead;
      cacheWrite += m.usage.cacheWrite;
      cost += m.usage.cost;
    }
    if (input > _displayHigh.input) _displayHigh.input = input;
    if (output > _displayHigh.output) _displayHigh.output = output;
    if (cacheRead > _displayHigh.cacheRead) _displayHigh.cacheRead = cacheRead;
    if (cacheWrite > _displayHigh.cacheWrite) _displayHigh.cacheWrite = cacheWrite;
    if (cost > _displayHigh.cost) _displayHigh.cost = cost;
    return {
      input: _displayHigh.input,
      output: _displayHigh.output,
      cacheRead: _displayHigh.cacheRead,
      cacheWrite: _displayHigh.cacheWrite,
      cost: _displayHigh.cost,
    };
  });

  function _resetDisplayTotals(): void {
    _displayHigh.input = 0;
    _displayHigh.output = 0;
    _displayHigh.cacheRead = 0;
    _displayHigh.cacheWrite = 0;
    _displayHigh.cost = 0;
  }

  // ── pending attachments ──────────────────────────────────────────────
  function _wrapWithAttachments(
    userText: string,
    atts: PendingAttachment[] = pendingAttachments.value,
  ): string {
    if (atts.length === 0) return userText;
    const lines = atts.map(
      (a) => `- ${a.agentPath}${a.size ? `  (${_humanSize(a.size)})` : ""}`,
    );
    const preamble =
      `I just uploaded ${atts.length} file${atts.length === 1 ? "" : "s"} ` +
      `to the workspace. Please look at ${atts.length === 1 ? "it" : "them"} ` +
      `and use ${atts.length === 1 ? "it" : "them"} when answering:\n` +
      lines.join("\n");
    const trimmed = userText.trim();
    return trimmed ? `${preamble}\n\n${trimmed}` : preamble;
  }

  function _humanSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function addPendingAttachments(items: PendingAttachment[]): void {
    if (items.length === 0) return;
    pendingAttachments.value = [...pendingAttachments.value, ...items];
  }

  function removePendingAttachment(localId: string): void {
    pendingAttachments.value = pendingAttachments.value.filter(
      (a) => a.localId !== localId,
    );
  }

  function clearPendingAttachments(): void {
    pendingAttachments.value = [];
  }

  // ── live-write mirroring ─────────────────────────────────────────────
  function _syncEditorFromWriteCall(): void {
    const last = router.messages[router.messages.length - 1];
    if (!last || last.kind !== "assistant") return;
    let latest: ToolCall | null = null;
    for (let i = last.toolCalls.length - 1; i >= 0; i--) {
      if (last.toolCalls[i].name === "write") {
        latest = last.toolCalls[i];
        break;
      }
    }
    if (!latest) return;
    useFilesStore().applyLiveWrite({
      id: latest.id,
      args: latest.args as { path?: unknown; content?: unknown } | undefined,
      status: latest.status,
      result: latest.result,
    });
  }

  // ── file-tree auto-refresh after filesystem-mutating tools ─────────
  //
  // Earlier behaviour: when the agent ran `write` / `edit` / `bash`
  // (any of which can create, delete, or move files) the FileTreePane
  // stayed stale until the user hit the manual Refresh button or
  // switched chats. New files appeared in the editor (via
  // applyLiveWrite) but were invisible in the tree, which made it
  // look like the AI hadn't actually written the file.
  //
  // New behaviour: every time a tool finishes (status flips to
  // `success` or `error`), if its name is one we know touches the
  // filesystem, schedule a refresh. We debounce (300 ms) so a turn
  // that writes 12 files in succession only fires ONE refresh after
  // the last one settles, not 12 in a row.
  const _FS_MUTATING_TOOLS = new Set(["write", "edit", "bash", "process"]);
  let _treeRefreshTimer: ReturnType<typeof setTimeout> | null = null;
  function _maybeRefreshFileTree(): void {
    const last = router.messages[router.messages.length - 1];
    if (!last || last.kind !== "assistant") return;
    // Look at the most recent tool call that JUST finished. We don't
    // walk the whole list because that'd refire every event of every
    // tool that ever ran in this turn — pricey on a long thread.
    let mutated = false;
    for (let i = last.toolCalls.length - 1; i >= 0; i--) {
      const tc = last.toolCalls[i];
      if (tc.status !== "success" && tc.status !== "error") continue;
      if (_FS_MUTATING_TOOLS.has(tc.name)) {
        mutated = true;
      }
      // Only care about the LAST finished one — earlier finished
      // calls in the same turn were already handled by an earlier
      // tick of this function.
      break;
    }
    if (!mutated) return;
    if (_treeRefreshTimer !== null) clearTimeout(_treeRefreshTimer);
    _treeRefreshTimer = setTimeout(() => {
      _treeRefreshTimer = null;
      // Lazy import dance — the files store needs the active workspace
      // id which isn't set until `connect()` has fired. If we
      // grabbed the store at module load we'd capture a stale Pinia
      // instance after HMR.
      const files = useFilesStore();
      void files.refreshTree();
    }, 300);
  }

  // ── connect / disconnect ────────────────────────────────────────────
  /**
   * Open the SSE stream for `sessionId`. Hydrate persisted history
   * BEFORE opening so users see prior turns instantly; live events
   * arriving after will only ever append.
   *
   * No more parked-session juggling — when the user switches chat
   * tabs we simply close the current stream and open a new one. The
   * BACKEND keeps the pi process alive (idle reaper kicks in after
   * 10 min) so a long tool turn the user navigated away from is
   * still progressing on the server. Coming back replays whatever
   * happened from the ring buffer.
   */
  async function connect(sessionId: string, wsid: string): Promise<void> {
    // If we're already connected to this exact session, no-op.
    if (session.value?.id === sessionId && stream && stream.isOpen) return;

    const workspace = useWorkspaceStore();
    const files = useFilesStore();
    const terminals = useTerminalsStore();

    // A "tab switch" inside the same workspace is the common case. We
    // do NOT call `disconnect()` (which blanks file tree, terminals,
    // workspace.setActive(null), the message list, …) — that's what
    // made tab switching feel like a full app refresh. Instead we
    // surgically tear down ONLY what's session-scoped: the SSE stream
    // and the per-session pending state. File tree and terminal panes
    // belong to the workspace and stay put.
    const sameWorkspace = workspace.activeId === wsid;

    if (stream) {
      stream.close();
      stream = null;
    }

    // Per-session resets (always — these are bound to a single chat).
    isStreaming.value = false;
    _setError(null);
    _resetDisplayTotals();
    queuedMessages.value = [];
    pendingAttachments.value = [];
    usePermissionsStore().clear();

    // Workspace-scoped resets (only when actually moving workspaces).
    workspace.setActive(wsid);
    if (!sameWorkspace) {
      files.resetForNewSession();
      terminals.resetForNewSession();
      void files.refreshTree();
    } else {
      // Same workspace, different chat — terminals are per-chat so we
      // do reset them, but the file tree stays as-is (it shows the
      // workspace, not the chat). Background terminal output for the
      // new chat will replay from the SSE ring on connect.
      terminals.resetForNewSession();
    }

    // Mark the session as switching but keep the OLD messages on
    // screen until the new history is fetched. We swap atomically
    // below — that's what removes the "blank flash" between tabs.
    session.value = { id: sessionId };

    let nextRouter = createRouterState();
    let nextMessages: ChatMessage[] = [];
    try {
      const { messages: hist } = await fetchSessionHistory(sessionId);
      if (hist?.length) {
        const restored = hist.map((m) => reactive(m) as ChatMessage);
        nextRouter.messages = restored;
        for (const m of restored) {
          if (m.kind !== "assistant") continue;
          (m as AssistantMessage).done = true;
          for (const tc of m.toolCalls) {
            nextRouter.toolCallIndex.set(tc.id, tc as ToolCall);
          }
        }
        nextMessages = restored;
      }
    } catch (err) {
      console.warn("[chat] history fetch failed; starting empty", err);
    }

    if (session.value?.id !== sessionId) return;

    // Atomic swap: replace router state + visible messages in a
    // single tick so Vue paints exactly one new frame.
    router = nextRouter;
    messages.value = nextMessages.slice();

    const newStream = new ChatStream({
      sessionId,
      onState: (state) => {
        if (stream !== newStream) return;
        // Map the 4-state ChatStreamState into the 5-state ConnState
        // by surfacing `error` only when an explicit error happened.
        if (state === "open") clearError();
        connState.value = state;
        if (state === "closed") isStreaming.value = false;
      },
      onError: (code) => {
        if (stream !== newStream) return;
        _setError(code);
        connState.value = "error";
        isStreaming.value = false;
      },
      onEvent: (raw) => {
        if (stream !== newStream) return;
        _dispatch(raw as RpcEvent & Record<string, unknown>);
      },
    });
    stream = newStream;
    newStream.open();
  }

  function disconnect(): void {
    if (stream) {
      stream.close();
      stream = null;
    }
    session.value = null;
    messages.value = [];
    router = createRouterState();
    isStreaming.value = false;
    _clearAbortState();
    _resetDisplayTotals();
    usePermissionsStore().clear();
    pendingAttachments.value = [];
    queuedMessages.value = [];
    useWorkspaceStore().setActive(null);
  }

  /**
   * Close + drop a specific session's stream. Currently a thin shim
   * around disconnect() since we no longer keep parked streams. Kept
   * as a public API so chat-session.ts callers don't have to change.
   */
  function closeSession(sid: string): void {
    if (session.value?.id === sid) {
      disconnect();
    }
    // Non-active sessions don't need cleanup — there's no parked
    // stream to close. The backend's idle reaper will reap pi if
    // nobody re-attaches within 10 min.
  }

  /**
   * Tear down + re-open the stream for the *same* session. Pi will
   * NOT respawn unless we send a fresh prompt — the backend keeps
   * the runtime alive across SSE drops. Used by ModelPicker to
   * pick up a model swap on the next prompt.
   */
  async function reconnect(): Promise<boolean> {
    const sid = session.value?.id;
    const wsid = useWorkspaceStore().activeId;
    if (!sid || !wsid) return false;
    if (isStreaming.value) {
      try {
        await stream?.abort();
      } catch {
        /* best effort */
      }
    }
    await connect(sid, wsid);
    return true;
  }

  // ── inbound dispatcher ──────────────────────────────────────────────
  function _dispatch(evt: RpcEvent & Record<string, unknown>): void {
    if (DEBUG_EVENTS) {
      const sub = (evt as { assistantMessageEvent?: { type?: string } })
        .assistantMessageEvent?.type;
      console.debug("[rpc]", evt.type, sub ? `(${sub})` : "", evt);
    }

    if (evt.type === "agent_start" || evt.type === "turn_start") isStreaming.value = true;
    else if (evt.type === "agent_end") {
      isStreaming.value = false;
      _clearAbortState();
    }

    if (evt.type === "compaction_start") {
      const reason = String((evt as { reason?: string }).reason || "threshold");
      compactionState.value = {
        active: true,
        reason,
        finishedAt: null,
        succeeded: null,
        errorMessage: null,
      };
      return;
    }
    if (evt.type === "compaction_end") {
      const aborted = Boolean((evt as { aborted?: boolean }).aborted);
      const errorMessage =
        typeof (evt as { errorMessage?: string }).errorMessage === "string"
          ? ((evt as { errorMessage?: string }).errorMessage as string)
          : null;
      const succeeded = !aborted && !errorMessage;
      compactionState.value = {
        active: false,
        reason: compactionState.value?.reason ?? "threshold",
        finishedAt: Date.now(),
        succeeded,
        errorMessage,
      };
      window.setTimeout(() => {
        const cs = compactionState.value;
        if (cs && cs.finishedAt && Date.now() - cs.finishedAt >= 7500) {
          compactionState.value = null;
        }
      }, 8000);
      return;
    }

    if (evt.type === "session" && session.value) {
      session.value = { id: session.value.id, cwd: String(evt.cwd ?? "") };
    }

    if (evt.type === "_session_info") {
      const model = String(evt.model ?? "");
      const modelName = String(evt.model_name ?? model);
      if (model) useModelsStore().noteSessionInfo(model, modelName);
      const rawMode = evt.permission_mode;
      if (typeof rawMode === "string" && rawMode.length > 0) {
        usePermissionsStore().setMode(rawMode);
      }
      return;
    }

    if (evt.type === "permission_request") {
      const id = String(evt.id ?? "");
      const tool = String(evt.tool ?? "tool");
      const mode = (typeof evt.mode === "string" ? evt.mode : "auto") as PermissionMode;
      if (!id) return;
      usePermissionsStore().enqueue({
        id,
        tool,
        toolCallId: typeof evt.tool_call_id === "string" ? evt.tool_call_id : undefined,
        input: (evt.input as Record<string, unknown>) ?? {},
        intent: typeof evt.intent === "string" ? evt.intent : "",
        preview: (evt.preview as { kind: "diff"; oldText: string; newText: string; filePath: string } | undefined),
        mode,
      });
      return;
    }

    if (evt.type === "_session_titled") {
      const sid = String(evt.sessionId ?? "");
      const title = String(evt.title ?? "").trim();
      if (sid && title) {
        useChatSessionStore().applyTitleUpdate(sid, title);
      }
      return;
    }

    if (evt.type === "_bridge_error") {
      const code = String(evt.code ?? "internal");
      if (evt.message) {
        // eslint-disable-next-line no-console
        console.warn(`[chat] bridge_error code=${code} (raw, suppressed in UI):`, evt.message);
      }
      _setError(code);
      if (code === "quota_exceeded") {
        useBillingStore().noteExhausted(null);
      }
      if (code === "setup_required" || code === "session_expired") {
        queueMicrotask(() => {
          void appRouter.push({ name: "login" });
        });
      }
      isStreaming.value = false;
      // fall through so applyEvent stamps the error on the bubble
    }

    if (evt.type === "_runtime_ended") {
      // Backend reaped pi (idle timeout) or pi crashed. The next
      // prompt will spawn a fresh runtime; nothing to surface.
      isStreaming.value = false;
      return;
    }

    if (evt.type === "fs_change") {
      const events = (evt.events ?? []) as Array<{
        kind: "created" | "modified" | "deleted" | "moved";
        path: string;
        is_dir: boolean;
        src?: string;
      }>;
      useFilesStore().applyFsChange(events);
      return;
    }

    if (evt.type === "bg_started" || evt.type === "bg_output" || evt.type === "bg_ended") {
      useTerminalsStore().applyBgEvent(evt);
      return;
    }

    applyEvent(router, evt);

    if (evt.type === "message_end" || evt.type === "_bridge_error") {
      const tail = router.messages[router.messages.length - 1];
      if (tail && tail.kind === "assistant" && tail.errorCode && !tail.error) {
        tail.error = _localiseError(tail.errorCode);
        if (!lastError.value) _setError(tail.errorCode);
      }
    }

    _syncEditorFromWriteCall();
    _maybeRefreshFileTree();
    messages.value = router.messages.slice();
  }

  // ── outbound ───────────────────────────────────────────────────────
  function sendPrompt(text: string): void {
    if (!stream) {
      _setError("not_connected");
      void reconnect();
      return;
    }
    const wrapped = _wrapWithAttachments(text);
    if (!wrapped.trim()) return;
    const reqId = `req-${Date.now()}`;
    // Push the user bubble + flip streaming OPTIMISTICALLY so the UI
    // feels instant. The POST resolves in <100ms typically; if it
    // fails we surface the error and roll back isStreaming. The
    // bubble itself stays — the user typed it; we don't want to
    // make their text disappear on a transient failure.
    pushUserMessage(router, wrapped, reqId);
    messages.value = [...router.messages];
    isStreaming.value = true;
    pendingAttachments.value = [];

    void (async () => {
      try {
        await stream!.sendPrompt(wrapped, reqId);
      } catch (err) {
        const code = err instanceof ChatStreamError ? err.code : "ws_send_failed";
        _setError(code);
        isStreaming.value = false;
      }
    })();
  }

  /**
   * Two-stage abort:
   *   1. Flip `isAborting` → composer shows "Stopping…" pill (still
   *      clickable but disabled), `isStreaming` stays true so the
   *      pill itself doesn't disappear.
   *   2. POST /abort, then wait for either:
   *        a) backend `agent_end` event → flips `isStreaming` false
   *           via the normal event-router path. This is the path
   *           BOTH the graceful and the force-kill cases now take —
   *           on force-kill the backend synthesises `agent_end` (plus
   *           `tool_execution_end` for every spinning tool card and
   *           a `message_end` with `stopReason: "aborted"`) so the
   *           SPA cleans up the same way it would have if pi exited
   *           normally.
   *        b) backend POST returns → belt-and-braces, we flip both
   *           flags ourselves in case the SSE stream is racing.
   *        c) 25 s elapses with no answer at all → defensive
   *           fallback, we free the UI anyway so the user can keep
   *           typing. Should be unreachable in practice — backend's
   *           worst-case grace is 20 s.
   */
  let _abortFallbackTimer: ReturnType<typeof setTimeout> | null = null;
  function _clearAbortState(): void {
    if (_abortFallbackTimer !== null) {
      clearTimeout(_abortFallbackTimer);
      _abortFallbackTimer = null;
    }
    isAborting.value = false;
  }
  function abort(): void {
    // Idempotent — repeat clicks on the Stopping pill are no-ops.
    if (isAborting.value) return;
    if (!isStreaming.value && !stream) return;
    isAborting.value = true;
    if (!stream) {
      isStreaming.value = false;
      _clearAbortState();
      return;
    }
    void stream
      .abort()
      .then(() => {
        // Backend abort returned. Either it was a clean (graceful)
        // abort — pi emitted `agent_end`, `isStreaming` already
        // flipped, harmless — OR it took the slow path (20 s
        // grace + force-kill). On the slow path we now synthesise
        // `agent_end` server-side after SIGKILL, so the SSE event
        // still flips `isStreaming` for us. This block is the
        // belt-and-braces clear for both paths.
        isStreaming.value = false;
        _clearAbortState();
      })
      .catch(() => {
        // Network error on the abort POST itself — free the UI
        // anyway, the user shouldn't be trapped.
        isStreaming.value = false;
        _clearAbortState();
      });

    // 25 s defensive fallback. Sized to exceed the backend's 20 s
    // graceful-abort grace by a comfortable margin so we never hide
    // the "Stopping…" pill before the backend has a chance to
    // complete the abort cleanly (which can legitimately take 5-15 s
    // during a parallel `subagent` fan-out + slow Vertex stream).
    // Previously 8 s — that fired DURING the grace window, kicking
    // the user back to a typable state while pi was still cleaning
    // up; the next prompt would race the half-finished turn and
    // produce the "main agent cut off after refresh" symptom the
    // user reported on 2026-05-16.
    _abortFallbackTimer = setTimeout(() => {
      if (isAborting.value) {
        isStreaming.value = false;
        _clearAbortState();
      }
    }, 25000);
  }

  // ── queue API ────────────────────────────────────────────────────────
  function _sendQueuedItem(item: QueuedMessage): void {
    if (!stream) {
      _setError("not_connected");
      void reconnect();
      return;
    }
    const body = _wrapWithAttachments(item.text, item.attachments);
    if (!body.trim()) return;
    const reqId = `req-${Date.now()}`;
    pushUserMessage(router, body, reqId);
    messages.value = [...router.messages];
    isStreaming.value = true;
    void (async () => {
      try {
        await stream!.sendPrompt(body, reqId);
      } catch (err) {
        const code = err instanceof ChatStreamError ? err.code : "ws_send_failed";
        _setError(code);
        isStreaming.value = false;
      }
    })();
  }

  function enqueueMessage(text: string): string | null {
    const trimmed = text.trim();
    if (!trimmed && pendingAttachments.value.length === 0) return null;
    const item: QueuedMessage = {
      id: `q-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      text: trimmed,
      attachments: pendingAttachments.value.slice(),
      createdAt: Date.now(),
    };
    queuedMessages.value = [...queuedMessages.value, item];
    pendingAttachments.value = [];
    return item.id;
  }

  function removeQueued(id: string): void {
    queuedMessages.value = queuedMessages.value.filter((q) => q.id !== id);
  }

  function editQueued(id: string, text: string): void {
    queuedMessages.value = queuedMessages.value.map((q) =>
      q.id === id ? { ...q, text } : q,
    );
  }

  /**
   * Force a queued item to run *now*: aborts the in-flight pi turn
   * (if any), removes the item from the queue, and dispatches it.
   *
   * Unlike the old WS path, abort here does NOT tear down the
   * connection — the backend just signals pi to drop its current
   * turn and stays ready for the next prompt. So we only have to
   * wait for `isStreaming` to flip false before sending.
   */
  async function pushQueued(id: string): Promise<void> {
    const item = queuedMessages.value.find((q) => q.id === id);
    if (!item) return;
    queuedMessages.value = queuedMessages.value.filter((q) => q.id !== id);
    if (isStreaming.value) {
      abort();
      const start = Date.now();
      while (isStreaming.value && Date.now() - start < 6000) {
        await new Promise((r) => setTimeout(r, 50));
      }
    }
    _sendQueuedItem(item);
  }

  function clearQueue(): void {
    queuedMessages.value = [];
  }

  // Auto-flush: when the in-flight turn ends and the queue has
  // items, fire the head.
  watch(
    isStreaming,
    (busy, wasBusy) => {
      if (busy || !wasBusy) return;
      if (queuedMessages.value.length === 0) return;
      const [head, ...rest] = queuedMessages.value;
      queuedMessages.value = rest;
      _sendQueuedItem(head);
    },
    { flush: "post" },
  );

  // Auto-flush: when the SSE transport flips back to `open` (after a
  // reconnect blip) and the user enqueued something while it was
  // down, fire the head. Without this, anything typed during a brief
  // network hiccup would sit in the queue strip forever waiting for
  // a "pi turn end" that never came (because no turn ever started).
  // The isStreaming watcher above handles the "send while pi is
  // busy" path; this one handles "send while transport is reconnecting".
  watch(
    connState,
    (now, prev) => {
      if (now !== "open" || prev === "open") return;
      if (isStreaming.value) return;
      if (queuedMessages.value.length === 0) return;
      const [head, ...rest] = queuedMessages.value;
      queuedMessages.value = rest;
      _sendQueuedItem(head);
    },
    { flush: "post" },
  );

  /** Reply to a permission_request — POST goes via the stream client. */
  function sendPermissionResponse(id: string, decision: PermissionDecision): void {
    if (!stream) return;
    // The old WS sent { decision } as a string ("allow_once" /
    // "allow_session" / "deny_once" / "deny_session"). The new SSE
    // protocol takes a boolean `granted`; allow_* → true, deny_* →
    // false. session-vs-once is local UI state (the permission
    // store remembers it for subsequent prompts) so the backend
    // only needs the binary answer.
    const granted = decision.startsWith("allow");
    void stream.answerPermission(id, granted).catch(() => {
      // pi-side ctx.ui.select() will time out and resolve to deny
      // if our POST never lands — safe default, no UI surface.
    });
  }

  function focusToolCall(toolCallId: string): void {
    for (const m of messages.value) {
      if (m.kind !== "assistant") continue;
      const tc = m.toolCalls.find((c) => c.id === toolCallId);
      if (!tc) continue;
      useFilesStore().focusLiveWriteCall({
        id: tc.id,
        name: tc.name,
        args: tc.args as { path?: unknown; content?: unknown } | undefined,
        status: tc.status,
        result: tc.result,
      });
      return;
    }
  }

  return {
    messages,
    session,
    connState,
    isStreaming,
    isAborting,
    lastError,
    lastErrorCode,
    clearError,
    isReconnecting,
    isInitialConnecting,
    compactionState,
    dismissCompaction,
    totals,
    pendingAttachments,
    queuedMessages,
    connect,
    disconnect,
    closeSession,
    reconnect,
    sendPrompt,
    enqueueMessage,
    removeQueued,
    editQueued,
    pushQueued,
    clearQueue,
    sendPermissionResponse,
    abort,
    focusToolCall,
    addPendingAttachments,
    removePendingAttachment,
    clearPendingAttachments,
  };
});
