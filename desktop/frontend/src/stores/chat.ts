/**
 * Chat WebSocket lifecycle + message stream + cost totals.
 *
 * Also acts as the central dispatcher for inbound WS events:
 *   - pi RPC events            → router.applyEvent → messages
 *                                → files.applyLiveWrite (write call mirroring)
 *   - fs_change events         → files.applyFsChange
 *   - bg_started/output/ended  → terminals.applyBgEvent
 */

import { defineStore } from "pinia";
import { computed, reactive, ref, watch } from "vue";

import { fetchSessionHistory } from "../api/sessions";
import { i18n } from "../i18n";
import {
  applyEvent,
  createRouterState,
  pushUserMessage,
  type RouterState,
} from "../lib/event-router";
// `appRouter` here is Vue Router (for navigation); `router` later in
// this module refers to the chat-message router state from
// event-router. Aliased to avoid the name clash.
import { router as appRouter } from "../router";
import type { AssistantMessage, ChatMessage, RpcEvent, ToolCall } from "../types/rpc";
import { ChatBridge, type ConnState } from "../ws/chat-bridge";

import { useBillingStore } from "./billing";
import { useChatSessionStore } from "./chat-session";
import { useFilesStore } from "./files";
import { useModelsStore } from "./models";
import { usePermissionsStore, type PermissionDecision, type PermissionMode } from "./permissions";
import { useTerminalsStore } from "./terminals";
import { useWorkspaceStore } from "./workspace";

const DEBUG_EVENTS =
  typeof window !== "undefined" && new URLSearchParams(window.location.search).has("debug");

interface SessionInfo {
  id: string;
  cwd?: string;
}

/**
 * One file the user attached but hasn't yet sent. The fields are a
 * thin slice of `SavedAttachment` from api/attachments — only what
 * the chip strip and prompt-prefix need, plus an internal `localId`
 * so the chip's "remove" button can target the right entry without
 * relying on the backend path being unique within a tab.
 */
export interface PendingAttachment {
  localId: string;
  name: string;
  size: number;
  mime: string;
  /** Workspace-relative — used for thumbnails / file tree. */
  path: string;
  /** Agent-cwd-relative — used in the prompt prefix so pi sees it. */
  agentPath: string;
}

/**
 * One message the user typed while pi was busy with a previous turn.
 *
 * Each entry binds the text to the *attachments that were pending when
 * the user hit Enter*. We intentionally snapshot the attachments at
 * enqueue time so a user can:
 *
 *   1. attach foo.png, type "look at this", hit Enter   → queues #1
 *   2. attach bar.pdf, type "and this", hit Enter        → queues #2
 *
 * and have foo.png travel with #1 and bar.pdf with #2 when each fires
 * (instead of both messages getting both attachments). The composer
 * `pendingAttachments` ref is cleared every time we enqueue.
 */
export interface QueuedMessage {
  id: string;
  text: string;
  attachments: PendingAttachment[];
  createdAt: number;
}

export const useChatStore = defineStore("chat", () => {
  // `router` is `let` (not `const`) because the multi-bridge tab-switch
  // logic below swaps the entire RouterState when parking the current
  // session and restoring a previously-parked one. Each session keeps
  // its own router instance (messages, toolCallIndex, activeThinking,
  // activeText cursors) inside the parkedSessions map; the active
  // store always points `router` at whichever session is on screen.
  let router = createRouterState();
  const messages = ref<ChatMessage[]>([]);
  const session = ref<SessionInfo | null>(null);
  const connState = ref<ConnState>("idle");
  const isStreaming = ref(false);
  const lastError = ref<string | null>(null);
  // Set by `abort()`, cleared by the connect()-side bridge state handler
  // when the WS subsequently closes. Used to silently respawn pi after
  // a user-driven abort instead of stranding the chat in "Connection
  // closed". NOT a `ref` — only the connect/abort code paths read it,
  // and we don't want a stale render to fire reconnect twice.
  let _abortedAwaitingReconnect = false;

  // ── parked sessions (multi-bridge) ─────────────────────────────────
  // When the user switches chat tabs we *don't* close the old WS — long
  // tool turns (e.g. `pip install`) would lose their tail and the next
  // visit would spawn a fresh pi instead of resuming. Instead the bridge
  // is "parked": its dispatcher callbacks are rebound to a parked-mode
  // dispatcher that updates a per-session snapshot, the WS stays
  // connected, and pi keeps streaming straight into the snapshot's
  // router. When the user comes back, _restoreFromParked() swaps the
  // active store's state in for the snapshot and rebinds the bridge to
  // the live dispatcher — without ever interrupting the underlying WS.
  //
  // Memory cost is bounded: one bridge + one router per chat tab the
  // user has *visited this session*. disconnect() (workspace exit /
  // sign-out) closes them all.
  interface ParkedSession {
    sid: string;
    wsid: string | null;
    bridge: ChatBridge;
    router: RouterState;
    isStreaming: boolean;
    lastError: string | null;
    connState: ConnState;
    cwd: string | undefined;
    queuedMessages: QueuedMessage[];
    pendingAttachments: PendingAttachment[];
    displayHigh: {
      input: number;
      output: number;
      cacheRead: number;
      cacheWrite: number;
      cost: number;
    };
  }
  const parkedSessions = new Map<string, ParkedSession>();

  // Files the user attached (paperclip / paste / drop) that haven't
  // been included in a prompt yet. The composer renders one chip per
  // entry; sendPrompt() consumes the whole list and prepends an
  // "Attached files:" preamble to the message.
  //
  // Each entry mirrors the `SavedAttachment` returned by the backend
  // — we keep both the tree-path (what the file tree wants) AND the
  // agent_path (what pi wants in its next read() call).
  const pendingAttachments = ref<PendingAttachment[]>([]);

  // Messages the user typed while pi was streaming a previous turn.
  // The watcher below auto-fires the head of the queue the moment
  // isStreaming flips false. Push/delete/edit are exposed as actions
  // so QueueStrip.vue can manipulate the list before items fire.
  const queuedMessages = ref<QueuedMessage[]>([]);

  let bridge: ChatBridge | null = null;

  // ── session-scoped totals ────────────────────────────────────────────
  // Two reactive totals coexist:
  //
  //   _displayTotals  monotonic, never goes down. Re-derived from
  //                   `messages`, then clamped per-field to never
  //                   shrink below the previously-seen high-water
  //                   mark within this WS session. This is what the
  //                   chat footer renders.
  //
  // Why this matters: the previous implementation re-summed `messages`
  // on every change, so the displayed cost would visibly drop from
  // $0.20 → $0.05 whenever the message list briefly dropped a turn —
  // happens during WS reconnect / history reload / mid-stream message
  // identity churn. The data-store totals are correct in aggregate
  // (the persisted JSONL log is the source of truth), but the UI
  // bouncing makes users think they're being double-charged. Clamping
  // monotonically gives the visible total the same "only goes up"
  // behaviour they have in every other AI chat product.
  //
  // The clamp resets in `disconnect()` below so a brand-new session
  // doesn't inherit a stale high-water mark from the previous chat.
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
    // Clamp each field upward against the high-water mark.
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

  // ── pending attachments ─────────────────────────────────────────────
  /**
   * Build the user-prompt text that pi will see, including the
   * "Attached files:" preamble when the user has pending attachments.
   *
   * The exact wording matters: the agent treats it as part of the user
   * turn, so we want it to read as if a human typed it. We deliberately
   * use bullet-points with the agent_path verbatim — pi resolves those
   * paths against its cwd, so saying "workspace/uploads/foo.png" is
   * exactly what its `read` tool needs.
   *
   * Behavioural goal (per user request):
   *
   *   "after uploaded in the next message we need to send inside the
   *    user message 'uploaded x, y, z files look at them also to
   *    answer as you need'"
   *
   * The preamble does that without overriding the user's actual
   * question; their text comes second, separated by a blank line.
   */
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
  /**
   * After every WS message, find the most recent `write` tool call on
   * the latest assistant turn and push its current state to the files
   * store so the editor can stream it.
   */
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

  // ── connect / disconnect ────────────────────────────────────────────
  /**
   * Open the chat WS for `sessionId`, scoped to `wsid`. Both must be
   * provided: the WS connection key is sessionId, but every REST call
   * the UI makes is workspace-scoped.
   *
   * Resume order is important — we hydrate the persisted message log
   * BEFORE opening the WS so users see their old turns instantly. Live
   * events that arrive after will only ever append a new assistant
   * message at the end, so there's no risk of clobbering the historical
   * tail.
   */
  async function connect(sessionId: string, wsid: string): Promise<void> {
    // Consume any pending "auto-reconnect after abort" intent that hasn't
    // been picked up yet. We're already in connect() — by definition a
    // reconnect is happening (whether kicked off by abort, the model
    // picker, or an explicit reconnect()), so the flag's job is done.
    // Clearing here also defuses a race where the OLD bridge's async
    // `onclose` arrives after disconnect() and re-reads the flag; without
    // this clear that callback can fire a phantom second reconnect()
    // mid-swap, which manifests as "pi crashed" + needs-browser-refresh
    // when the user changes models during a streaming turn.
    _abortedAwaitingReconnect = false;

    // Decide what to do with the *currently* active session before we
    // touch any state for the incoming one:
    //
    //   1. Same session (refresh / model swap)  → full teardown + fresh
    //      reconnect, exactly like the previous single-bridge code did.
    //   2. Different session, with a live bridge → park it. The bridge's
    //      WS stays open, its dispatcher is rebound to a parked-mode
    //      stub that updates the parked snapshot, and a long pi turn
    //      keeps streaming. We DO NOT close it.
    //   3. No prior session                      → nothing to park.
    const switchingToDifferent =
      session.value !== null && session.value.id !== sessionId && bridge !== null;
    if (switchingToDifferent) {
      _parkCurrent();
    } else {
      // Same-session refresh OR first-ever connect — drop everything.
      disconnect();
    }

    // Reset per-session active state. Even if we're about to restore from
    // a parked snapshot, having a clean slate first prevents a flicker
    // where the previous session's messages briefly bleed onto the new
    // tab.
    router = createRouterState();
    messages.value = [];
    session.value = { id: sessionId };
    isStreaming.value = false;
    lastError.value = null;
    _resetDisplayTotals();
    queuedMessages.value = [];
    pendingAttachments.value = [];

    const workspace = useWorkspaceStore();
    const files = useFilesStore();
    const terminals = useTerminalsStore();

    workspace.setActive(wsid);
    files.resetForNewSession();
    terminals.resetForNewSession();

    void files.refreshTree();

    // If we visited this session earlier in the workspace lifetime and
    // its bridge is parked, restore from the snapshot — pi is still
    // streaming there and may have advanced since we left.
    const parked = parkedSessions.get(sessionId);
    if (parked) {
      parkedSessions.delete(sessionId);
      _restoreFromParked(parked);
      return;
    }

    try {
      const { messages: hist } = await fetchSessionHistory(sessionId);
      if (hist?.length) _hydrateHistory(hist);
    } catch (err) {
      console.warn("[chat] history fetch failed; starting empty", err);
    }

    // Bail out if a newer connect() raced past us while history was loading.
    if (session.value?.id !== sessionId) return;

    // Bind the bridge identity into the onState closure so a dying old
    // bridge (whose ws.onclose fires asynchronously after we've already
    // moved on to a new bridge) cannot mutate the active session's UI
    // state or re-trigger reconnect. This is a belt-and-suspenders guard
    // on top of the flag-clear above.
    const newBridge = new ChatBridge({
      sessionId,
      onState: (state, error) => {
        if (bridge !== newBridge) return;
        connState.value = state;
        if (state === "error" && error) lastError.value = error;
        if (state === "closed" || state === "error") isStreaming.value = false;
        // After a client-driven abort the backend closes the WS with code
        // 4410, which the bridge surfaces as a normal "closed" state. We
        // set `_abortedAwaitingReconnect` in `abort()` so we can tell
        // *this* close apart from a real disconnect (network blip, tab
        // backgrounded, server crash) and silently respawn pi instead of
        // showing the "Connection closed" banner. Without this the user
        // would have to click the model picker to reconnect after every
        // abort, which defeats the purpose of having a stop button.
        if (state === "closed" && _abortedAwaitingReconnect) {
          _abortedAwaitingReconnect = false;
          void reconnect();
        }
      },
      onEvent: (raw) => {
        if (bridge !== newBridge) return;
        _dispatch(raw as RpcEvent & Record<string, unknown>);
      },
    });
    bridge = newBridge;
    newBridge.open();
  }

  // ── parked-session helpers (multi-bridge) ──────────────────────────
  /**
   * Move the *currently* active session into the parked map. The
   * underlying WebSocket is NOT closed — pi keeps streaming into the
   * parked router so a long-running tool call (e.g. `pip install`) is
   * preserved across the tab switch. `bridge` is cleared so the caller
   * can immediately install a new active bridge.
   */
  function _parkCurrent(): void {
    if (!bridge || !session.value) return;
    const sid = session.value.id;
    const wsid = useWorkspaceStore().activeId;
    const parked: ParkedSession = {
      sid,
      wsid,
      bridge,
      router,
      isStreaming: isStreaming.value,
      lastError: lastError.value,
      connState: connState.value,
      cwd: session.value.cwd,
      queuedMessages: queuedMessages.value.slice(),
      pendingAttachments: pendingAttachments.value.slice(),
      displayHigh: {
        input: _displayHigh.input,
        output: _displayHigh.output,
        cacheRead: _displayHigh.cacheRead,
        cacheWrite: _displayHigh.cacheWrite,
        cost: _displayHigh.cost,
      },
    };

    // Rebind to the parked-mode dispatcher BEFORE we move the bridge
    // into the map; otherwise an event arriving in the rebind/move
    // window would still hit the live dispatcher and mutate the new
    // active session's state.
    bridge.rebind({
      sessionId: sid,
      onState: (state, error) => {
        parked.connState = state;
        if (state === "error" && error) parked.lastError = error;
        if (state === "closed" || state === "error") parked.isStreaming = false;
      },
      onEvent: (raw) => {
        _dispatchParked(parked, raw as RpcEvent & Record<string, unknown>);
      },
    });

    parkedSessions.set(sid, parked);
    bridge = null;
  }

  /**
   * Restore a previously-parked session: swap its router back into the
   * active store, repopulate the visible refs from the snapshot, and
   * rebind the bridge's dispatcher to the live one. The WS itself was
   * never closed, so any progress pi made while we were away is already
   * sitting in `parked.router.messages`.
   */
  function _restoreFromParked(parked: ParkedSession): void {
    router = parked.router;
    messages.value = router.messages.slice();
    session.value = { id: parked.sid, cwd: parked.cwd };
    isStreaming.value = parked.isStreaming;
    lastError.value = parked.lastError;
    connState.value = parked.connState;

    queuedMessages.value = parked.queuedMessages;
    pendingAttachments.value = parked.pendingAttachments;

    _displayHigh.input = parked.displayHigh.input;
    _displayHigh.output = parked.displayHigh.output;
    _displayHigh.cacheRead = parked.displayHigh.cacheRead;
    _displayHigh.cacheWrite = parked.displayHigh.cacheWrite;
    _displayHigh.cost = parked.displayHigh.cost;

    const restoredBridge = parked.bridge;
    bridge = restoredBridge;

    restoredBridge.rebind({
      sessionId: parked.sid,
      onState: (state, error) => {
        if (bridge !== restoredBridge) return;
        connState.value = state;
        if (state === "error" && error) lastError.value = error;
        if (state === "closed" || state === "error") isStreaming.value = false;
        if (state === "closed" && _abortedAwaitingReconnect) {
          _abortedAwaitingReconnect = false;
          void reconnect();
        }
      },
      onEvent: (raw) => {
        if (bridge !== restoredBridge) return;
        _dispatch(raw as RpcEvent & Record<string, unknown>);
      },
    });
  }

  /**
   * Parked-mode event dispatcher. Mirrors the live `_dispatch` but:
   *   - applies router events to the parked snapshot, not the active one;
   *   - silently drops events whose side-effects target stores that
   *     are scoped to the *active* workspace (fs_change, bg_*, permission
   *     prompts, _session_info). The user will see the up-to-date result
   *     when they switch back; surfacing them now would mutate state
   *     belonging to the wrong tab.
   */
  function _dispatchParked(
    parked: ParkedSession,
    evt: RpcEvent & Record<string, unknown>,
  ): void {
    if (DEBUG_EVENTS) {
      console.debug("[parked rpc]", parked.sid, evt.type, evt);
    }

    if (evt.type === "agent_start" || evt.type === "turn_start") {
      parked.isStreaming = true;
    } else if (evt.type === "agent_end") {
      parked.isStreaming = false;
    }

    if (evt.type === "session") {
      parked.cwd = String(evt.cwd ?? "");
      return;
    }
    // Model-pin / permission-mode info is global to the active store
    // and doesn't apply to a backgrounded tab.
    if (evt.type === "_session_info") return;

    // Background-tab permission prompts can't be answered (the modal
    // belongs to the foreground session). pi will time out the
    // ctx.ui.select() call on its own and the tool will resolve to deny,
    // which is the safe default.
    if (evt.type === "permission_request") return;

    // Title updates ARE safe to apply globally — the chat-session store
    // is keyed by sid, so we want the picker to show the polished title
    // immediately even if the user is viewing a different chat.
    if (evt.type === "_session_titled") {
      const sid = String(evt.sessionId ?? "");
      const title = String(evt.title ?? "").trim();
      if (sid && title) useChatSessionStore().applyTitleUpdate(sid, title);
      return;
    }

    if (evt.type === "_bridge_error") {
      const code = String(evt.code ?? "internal");
      parked.lastError = _localiseError(code);
      parked.isStreaming = false;
      return;
    }

    // fs / background-terminal events belong to the active workspace
    // only — applying them while parked would corrupt the foreground
    // tab's file tree and terminal panes.
    if (evt.type === "fs_change") return;
    if (evt.type === "bg_started" || evt.type === "bg_output" || evt.type === "bg_ended") {
      return;
    }

    applyEvent(parked.router, evt);

    const tail = parked.router.messages[parked.router.messages.length - 1];
    if (tail && tail.kind === "assistant" && tail.errorCode && !tail.error) {
      tail.error = _localiseError(tail.errorCode);
    }
    if (evt.type === "message_end" && !parked.lastError) {
      if (tail && tail.kind === "assistant" && tail.error) {
        parked.lastError = tail.error;
        parked.isStreaming = false;
      }
    }
  }

  /**
   * Replay a server-projected ChatMessage[] into router state so the UI
   * paints prior turns. Each entry is wrapped in `reactive()` so Vue
   * tracks any post-load mutation (e.g. a tool result attached after the
   * assistant message; usage updated). We also re-index every ToolCall
   * by id so the live router can still look them up — though in practice
   * historical and live tool ids never collide.
   */
  function _hydrateHistory(hist: ChatMessage[]): void {
    const restored = hist.map((m) => reactive(m) as ChatMessage);
    router.messages = restored;
    for (const m of restored) {
      if (m.kind !== "assistant") continue;
      for (const tc of m.toolCalls) router.toolCallIndex.set(tc.id, tc as ToolCall);
    }
    // Mark every restored assistant turn as complete — there are no
    // open thinking/text channels to attach further deltas to.
    for (const m of restored) {
      if (m.kind === "assistant") (m as AssistantMessage).done = true;
    }
    messages.value = restored.slice();
  }

  function disconnect(): void {
    // An explicit teardown supersedes any pending abort-reconnect intent.
    // Without this, navigating to a new session immediately after clicking
    // stop could let the dying bridge's onclose schedule a reconnect to
    // the *previous* session id.
    _abortedAwaitingReconnect = false;
    if (bridge) {
      bridge.close();
      bridge = null;
    }
    // Close every parked bridge too — disconnect() is called on workspace
    // exit / sign-out / Workspace.vue unmount, which means the user is
    // leaving the entire chat surface. Leaving parked WSs open would
    // pile up zombie pi processes on the backend.
    for (const p of parkedSessions.values()) {
      try {
        p.bridge.close();
      } catch {
        /* already gone */
      }
    }
    parkedSessions.clear();
    session.value = null;
    messages.value = [];
    router = createRouterState();
    isStreaming.value = false;
    // Reset the monotonic-totals high-water mark so a brand-new chat
    // doesn't inherit the previous chat's cost. The persisted JSONL
    // log remains the source of truth for per-session accounting.
    _resetDisplayTotals();
    // Discard any unanswered permission prompts — they were tied to the
    // pi process we're tearing down. If we left them sitting, the user
    // would see a stale modal in the next session.
    usePermissionsStore().clear();
    // Drop pending attachment chips. They were uploaded into a specific
    // workspace; carrying them across to a new session would point at
    // files that don't exist (and worse, leak metadata across users on
    // shared machines). Files on disk are kept — only the chat's
    // in-memory list is cleared.
    pendingAttachments.value = [];
    // Drop queued messages along with the WS — they were typed for *this*
    // workspace's pi process. Carrying them across to a new session
    // would silently fire prompts in a different chat once the user
    // reconnected.
    queuedMessages.value = [];
    useWorkspaceStore().setActive(null);
  }

  /**
   * Close + drop a specific session's WS. Called from chat-session when
   * the user deletes a chat: without this, the parked bridge would keep
   * its WS open (heartbeat + auto-reconnect) and pin a pi process on
   * the backend forever. Safe to call for the active session too — it
   * just delegates to disconnect() so the rest of the cleanup
   * (workspace teardown, queue drop, etc.) runs uniformly.
   */
  function closeSession(sid: string): void {
    if (session.value?.id === sid) {
      disconnect();
      return;
    }
    const parked = parkedSessions.get(sid);
    if (!parked) return;
    parkedSessions.delete(sid);
    try {
      parked.bridge.close();
    } catch {
      /* already gone */
    }
  }

  /**
   * Tear down the WS and re-open it for the *same* session + workspace.
   * Pi will respawn fresh, picking up whatever the registry has for the
   * session right now (model pin, permission mode, etc.) — that's what
   * makes a model swap take effect immediately instead of "on the next
   * prompt after some other respawn".
   *
   * Returns false if there's no live connection to recycle (callers can
   * skip silently in that case).
   */
  async function reconnect(): Promise<boolean> {
    const sid = session.value?.id;
    const wsid = useWorkspaceStore().activeId;
    if (!sid || !wsid) return false;
    // connect() already calls disconnect() first, so there's no double-
    // teardown here. If pi is mid-stream we abort first so the close
    // handshake isn't racing a queued tool call.
    if (isStreaming.value) abort();
    await connect(sid, wsid);
    return true;
  }

  /**
   * Re-open the WS against a freshly respawned sidecar. Called by the
   * Tauri-side watchdog handler in `main.ts` when the sidecar exits
   * and comes back on a (potentially different) port.
   *
   * The flow is intentionally minimal: the API client already had its
   * base URL rebound by `setApiBase()` BEFORE we get here, so this
   * just needs to drop the dead bridge and re-open. We don't surface
   * a toast — the existing chat-error banner already shows
   * "ws_unreachable" while the sidecar is down, and replacing it
   * with a more granular "Backend restarted, reconnecting" event
   * would just add noise during the most-stressful 1-2 seconds.
   */
  function reanchorBridge(): void {
    if (!session.value?.id) return;
    void reconnect();
  }

  // ── inbound dispatcher ──────────────────────────────────────────────
  function _dispatch(evt: RpcEvent & Record<string, unknown>): void {
    if (DEBUG_EVENTS) {
      const sub = (evt as { assistantMessageEvent?: { type?: string } })
        .assistantMessageEvent?.type;
      console.debug("[rpc]", evt.type, sub ? `(${sub})` : "", evt);
    }

    if (evt.type === "agent_start" || evt.type === "turn_start") isStreaming.value = true;
    else if (evt.type === "agent_end") isStreaming.value = false;

    if (evt.type === "session" && session.value) {
      session.value = { id: session.value.id, cwd: String(evt.cwd ?? "") };
    }

    // Backend tells us which model the spawned pi actually loaded
    // (may differ from what we requested if the user downgraded).
    if (evt.type === "_session_info") {
      const model = String(evt.model ?? "");
      const modelName = String(evt.model_name ?? model);
      if (model) useModelsStore().noteSessionInfo(model, modelName);
      // Permission mode arrives over the wire as either a canonical ID
      // (auto / ask / cautious) or a legacy alias (approve_risky /
      // approve_all). The store's setMode() normalizes both.
      const rawMode = evt.permission_mode;
      if (typeof rawMode === "string" && rawMode.length > 0) {
        usePermissionsStore().setMode(rawMode);
      }
      return;
    }

    // Permission gate. The backend rewrites the pi extension's
    // ctx.ui.select() call into this event; we surface it via the
    // permissions store so <PermissionPrompt /> can render the modal.
    if (evt.type === "permission_request") {
      const id = String(evt.id ?? "");
      const tool = String(evt.tool ?? "tool");
      // The store normalizes legacy aliases (approve_risky → ask, etc).
      const mode = (typeof evt.mode === "string" ? evt.mode : "ask") as PermissionMode;
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

    // Background LLM-generated session title landed. We update the
    // chat-session store in place so the picker / brand header reflect
    // the polished title without waiting for a refresh. The backend
    // already CAS-checked against the heuristic title, so by the time
    // we get here, the new title is durable in the registry.
    if (evt.type === "_session_titled") {
      const sid = String(evt.sessionId ?? "");
      const title = String(evt.title ?? "").trim();
      if (sid && title) {
        useChatSessionStore().applyTitleUpdate(sid, title);
      }
      return;
    }

    // Inline server-side errors arrive as `_bridge_error` with a stable
    // `code` discriminator. The backend never sends raw exceptions or
    // file paths — every UI string comes from the i18n table here.
    //
    // Special routing:
    //   - `setup_required` / `session_expired`  → bounce to /login;
    //     the user has nothing to do on the chat surface until they
    //     resolve auth.
    //   - `quota_exceeded` → also flips the billing store flag so the
    //     upgrade modal pops without waiting for the next /api/usage
    //     poll.
    //   - everything else surfaces in the bottom banner only.
    if (evt.type === "_bridge_error") {
      const code = String(evt.code ?? "internal");
      // Always look up via i18n, NEVER fall back to evt.message.
      // The backend's English message is human-readable but it's
      // still server-side language ("Cloud relay rejected the
      // connection (HTTP 403)") that we don't want surfacing to
      // end users. _localiseError falls back to the generic
      // "Something went wrong" if the code has no entry yet —
      // that's a strictly better UX than leaking raw text.
      const localised = _localiseError(code);
      lastError.value = localised;

      if (code === "quota_exceeded") {
        useBillingStore().noteExhausted(null);
      }
      if (code === "setup_required" || code === "session_expired") {
        // Bounce to the Welcome screen — the user can't make progress
        // here until they sign in or add a key. queueMicrotask defers
        // the navigation past the current event handler so the WS
        // teardown fires in order.
        queueMicrotask(() => {
          void appRouter.push({ name: "login" });
        });
      }

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
    _syncEditorFromWriteCall();
    messages.value = router.messages.slice();

    // Localise any error the router just stamped, so both the
    // assistant bubble AND the bottom banner render friendly text
    // instead of a raw provider/HTTP string. The router only stamps
    // `errorCode` (a stable category like "provider_rate_limit",
    // "provider_usage_policy", …); this helper looks up the
    // matching `errors.<code>` i18n key and falls back to the
    // generic `errors.internal` ("Something went wrong. Please try
    // again.") for any unknown / unmatched code.
    //
    // Important contract for future contributors: NEVER set
    // `asst.error = <raw provider text>`. The chat UI renders
    // `asst.error` verbatim, so anything that lands there will hit
    // the user's screen. Always go through `errorCode` + this
    // helper.
    const tailMsg = router.messages[router.messages.length - 1];
    if (
      tailMsg &&
      tailMsg.kind === "assistant" &&
      tailMsg.errorCode &&
      !tailMsg.error
    ) {
      tailMsg.error = _localiseError(tailMsg.errorCode);
    }

    // Mirror the now-localised error to the bottom banner so the
    // failure is visible no matter where the user is scrolled.
    // Skip if a previous tick already populated lastError — the
    // _bridge_error path sets it in its own branch above.
    if (evt.type === "message_end" && !lastError.value) {
      if (tailMsg && tailMsg.kind === "assistant" && tailMsg.error) {
        lastError.value = tailMsg.error;
        isStreaming.value = false;
      }
    }
  }

  /**
   * Map a stable error code (provider_rate_limit, provider_usage_policy,
   * relay_unauthenticated, etc.) to a friendly localised string.
   * Falls back to the generic `errors.internal` when the code has no
   * dedicated translation, so the user never sees a raw category
   * name like "provider_error" leak into the chat.
   */
  function _localiseError(code: string): string {
    const key = `errors.${code}`;
    if (i18n.global.te(key)) {
      return i18n.global.t(key) as string;
    }
    return i18n.global.t("errors.internal") as string;
  }

  // ── outbound ───────────────────────────────────────────────────────
  function sendPrompt(text: string): void {
    if (!bridge || !bridge.isOpen) {
      lastError.value = "Not connected";
      return;
    }
    // Wrap with attachments if any are pending. The wrapping is done
    // INSIDE sendPrompt (rather than in the composer) so every entry
    // point — Enter key, click handler, future programmatic resends —
    // gets the same treatment without duplicating logic.
    const wrapped = _wrapWithAttachments(text);
    if (!wrapped.trim()) return;
    const reqId = `req-${Date.now()}`;
    pushUserMessage(router, wrapped, reqId);
    messages.value = [...router.messages];
    bridge.send({ id: reqId, type: "prompt", message: wrapped });
    isStreaming.value = true;
    // Attachments are one-shot: cleared after the prompt that included
    // them is sent. The agent's `read` call against the path will work
    // forever; we just don't want to keep echoing the prefix.
    pendingAttachments.value = [];
  }

  function abort(): void {
    if (!bridge || !bridge.isOpen) return;
    // Arm the auto-reconnect flag *before* we send the frame. The
    // backend closes the WS very fast (the abort handler sends one
    // bridge_error then returns, killing pi inline), so by the time
    // we hit the next microtask the close handler may already have
    // fired. Setting the flag first guarantees the connect() callback
    // sees it.
    _abortedAwaitingReconnect = true;
    bridge.send({ type: "abort" });
  }

  // ── queue API ────────────────────────────────────────────────────────
  //
  // `_sendQueuedItem` is the private dispatcher that turns a QueuedMessage
  // into an actual bridge.send. It deliberately does NOT re-wrap the text
  // with the live `pendingAttachments` ref — the queued item carries its
  // own attachment snapshot already. This is what lets two queued
  // messages have different attachment lists without leaking.
  function _sendQueuedItem(item: QueuedMessage): void {
    if (!bridge || !bridge.isOpen) {
      lastError.value = "Not connected";
      return;
    }
    const body = _wrapWithAttachments(item.text, item.attachments);
    if (!body.trim()) return;
    const reqId = `req-${Date.now()}`;
    pushUserMessage(router, body, reqId);
    messages.value = [...router.messages];
    bridge.send({ id: reqId, type: "prompt", message: body });
    isStreaming.value = true;
  }

  /**
   * Add the current composer state (text + the live `pendingAttachments`
   * snapshot) to the queue. The composer clears its own textarea; we
   * clear the attachment chips here so a follow-up "attach + queue"
   * starts fresh. Returns the new entry's id so the UI can scroll to it
   * or open the queue tray.
   */
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
   * Force a queued item to run *now*: aborts the in-flight pi turn (if
   * any), removes the item from the queue, and dispatches it. The
   * auto-flush watcher will pick up subsequent items normally once pi
   * tears down its current run and isStreaming flips false.
   *
   * NOTE: we abort first, then send AFTER a microtask so the bridge has
   * a chance to flush the abort frame before the new prompt frame. In
   * practice both go through the same WS write queue and are ordered,
   * but the explicit `await Promise.resolve()` keeps it readable.
   */
  async function pushQueued(id: string): Promise<void> {
    const item = queuedMessages.value.find((q) => q.id === id);
    if (!item) return;
    queuedMessages.value = queuedMessages.value.filter((q) => q.id !== id);
    if (isStreaming.value) {
      abort();
      // Wait for the backend to flip isStreaming false (via _bridge_error
      // 'aborted' or agent_end) AND for the bridge to come back online.
      // The abort path now genuinely tears down the WS (close code 4410)
      // and auto-reconnects, so we have to wait for connState to settle
      // back to "open" or our `bridge.send()` would land on the closed
      // socket and disappear. Time out after 6s and try anyway — the
      // bridge will surface an error if the abort/reconnect genuinely
      // failed.
      const start = Date.now();
      while (
        (isStreaming.value || connState.value !== "open") &&
        Date.now() - start < 6000
      ) {
        await new Promise((r) => setTimeout(r, 50));
      }
    }
    _sendQueuedItem(item);
  }

  function clearQueue(): void {
    queuedMessages.value = [];
  }

  // Auto-flush: when the in-flight turn ends and the queue has items,
  // fire the head. Vue's watch fires after isStreaming changes, so the
  // backend has already settled. We use { flush: "post" } to avoid
  // racing with the same tick's _dispatch updates.
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

  /** Send the user's reply to a permission_request. The store layer handles
   * dequeueing in <PermissionPrompt />; we just forward over the wire. If
   * the bridge is gone (rare race during reconnect) we drop silently — the
   * pi-side ctx.ui.select() will time out and resolve to deny, which is
   * the safe default. */
  function sendPermissionResponse(id: string, decision: PermissionDecision): void {
    if (!bridge || !bridge.isOpen) return;
    bridge.send({ id, type: "permission_response", decision });
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
    lastError,
    totals,
    pendingAttachments,
    queuedMessages,
    connect,
    disconnect,
    closeSession,
    reconnect,
    reanchorBridge,
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
