/**
 * WebSocket bridge to `/ws/sessions/{sid}`.
 *
 * Owns the actual WebSocket. Emits raw JSON events to a single dispatcher
 * callback; the chat store routes them to the right slice (chat / files /
 * terminals). Doesn't know about Pinia or Vue.
 *
 * Resilience features (kept in sync with desktop/frontend/src/ws/chat-
 * bridge.ts so both clients survive idle / sleep / network blips
 * uniformly):
 *
 *   1. **Client-side heartbeat.** Browsers do NOT send WebSocket pings
 *      automatically. Without one, NAT / Caddy idle timeouts and laptop
 *      sleep all silently kill the underlying TCP socket while the
 *      WebSocket object still claims `readyState=OPEN`. We send
 *      `{type:"ping"}` every 25 s and expect `{type:"pong"}` back
 *      within 10 s; missed pong = treat the socket as dead.
 *
 *   2. **Exponential backoff auto-reconnect** for transient closes
 *      (1006 abnormal, 1011 internal, 4503 upstream unreachable,
 *      heartbeat-miss). 1s -> 2s -> 4s -> ... capped at 15s with full
 *      jitter, max 8 attempts. Auth / capacity / rate-limit codes are
 *      NOT auto-reconnected — they need user action.
 *
 *   3. **Wake-from-sleep / online detection.** `window.online` and
 *      `document.visibilitychange -> visible` re-arm a heartbeat to
 *      catch the half-dead socket and force a reconnect if the pong
 *      doesn't come back.
 */

import { buildWebSocketUrl } from "../api/client";

export type ConnState = "idle" | "connecting" | "open" | "closed" | "error";

export interface BridgeOpts {
  sessionId: string;
  onEvent: (evt: unknown) => void;
  onState: (state: ConnState, error?: string | null) => void;
}

const HEARTBEAT_INTERVAL_MS = 25_000;
const HEARTBEAT_TIMEOUT_MS = 10_000;
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_CAP_MS = 15_000;
const RECONNECT_MAX_ATTEMPTS = 8;

export class ChatBridge {
  private ws: WebSocket | null = null;
  private opts: BridgeOpts;
  private explicitlyClosed = false;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeoutTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempt = 0;
  private wakeListenersBound = false;
  private readonly onWake = () => this.handleWakeOrOnline();
  private readonly onVisibility = () => {
    if (typeof document !== "undefined" && document.visibilityState === "visible") {
      this.handleWakeOrOnline();
    }
  };

  constructor(opts: BridgeOpts) {
    this.opts = opts;
  }

  open(): void {
    this.explicitlyClosed = false;
    this.cancelReconnect();
    this.bindWakeListeners();
    this.opts.onState("connecting");
    const path = `/ws/sessions/${encodeURIComponent(this.opts.sessionId)}`;
    void buildWebSocketUrl(path).then((url) => {
      if (this.explicitlyClosed) return;
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (_err) {
        this.opts.onState("error", "network");
        this.scheduleReconnect();
        return;
      }
      this.ws = ws;
      ws.onopen = () => {
        this.reconnectAttempt = 0;
        this.startHeartbeat();
        this.opts.onState("open");
      };
      ws.onerror = () => this.opts.onState("error", "network");
      ws.onclose = (e) => this.handleClose(e);
      ws.onmessage = (e) => this.handleMessage(e);
    });
  }

  close(): void {
    this.explicitlyClosed = true;
    this.cancelReconnect();
    this.stopHeartbeat();
    this.unbindWakeListeners();
    const ws = this.ws;
    this.ws = null;
    if (!ws) return;
    try {
      ws.close();
    } catch {
      /* already gone */
    }
  }

  send(payload: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    try {
      this.ws.send(JSON.stringify(payload));
    } catch {
      this.opts.onState("error", "network");
    }
  }

  /**
   * Swap the dispatcher callbacks without touching the underlying WS.
   * Used by the chat store to "park" a bridge when the user switches
   * tabs: events are routed to the parked snapshot's dispatcher, and
   * when the user comes back the live dispatcher is rebound. The
   * WebSocket stays connected throughout, so a long-running pi turn
   * (e.g. `pip install`) continues streaming straight into the parked
   * session's router instead of being aborted.
   *
   * Safe to call at any time — handler refs (`onopen`, `onclose`,
   * `onmessage`, `onerror`) all read `this.opts.X(...)` lazily, so a
   * mid-flight callback after rebind() will land on the new opts.
   *
   * Mirrors desktop/frontend/src/ws/chat-bridge.ts so both clients keep
   * the same multi-bridge semantics.
   */
  rebind(next: BridgeOpts): void {
    this.opts = next;
  }

  get isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private handleMessage(e: MessageEvent): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(typeof e.data === "string" ? e.data : "");
    } catch {
      return;
    }
    if (
      parsed
      && typeof parsed === "object"
      && (parsed as { type?: unknown }).type === "pong"
    ) {
      this.clearHeartbeatTimeout();
      return;
    }
    this.opts.onEvent(parsed);
  }

  private handleClose(e: CloseEvent): void {
    this.stopHeartbeat();
    if (e.code === 4401) {
      this.opts.onState("error", "session_expired");
      return;
    }
    if (e.code === 4408) {
      this.opts.onState("closed");
      return;
    }
    if (e.code === 4409) {
      const reason = e.reason ?? "";
      if (reason.startsWith("too_many_chats")) {
        this.opts.onState("error", "too_many_chats");
      } else {
        this.opts.onState("error", "session_kicked");
      }
      return;
    }
    if (e.code === 4410) {
      this.opts.onState("closed");
      return;
    }
    // 4429 = rate limit. Surface the error to the SPA but ALSO
    // schedule a reconnect — the previous version of this code gave
    // up entirely, leaving the user stuck on the banner until they
    // manually clicked Reconnect even though the per-minute refill
    // would have cleared the bucket on its own. The exponential
    // backoff biases retries toward AFTER the refill window has had
    // a chance to add tokens.
    if (e.code === 4429) {
      this.opts.onState("error", "rate_limit");
      if (!this.explicitlyClosed) this.scheduleReconnect();
      return;
    }
    if (e.code === 1006 || e.code === 1011 || e.code === 4503) {
      this.opts.onState("error", "network");
      if (!this.explicitlyClosed) this.scheduleReconnect();
      return;
    }
    if (this.explicitlyClosed) {
      this.opts.onState("closed");
      return;
    }
    this.opts.onState("error", "network");
    this.scheduleReconnect();
  }

  // ── Heartbeat ───────────────────────────────────────────────────
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => this.sendHeartbeat(), HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearHeartbeatTimeout();
  }

  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  private sendHeartbeat(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    try {
      this.ws.send(JSON.stringify({ type: "ping", t: Date.now() }));
    } catch {
      this.forceReconnect("network");
      return;
    }
    this.clearHeartbeatTimeout();
    this.heartbeatTimeoutTimer = setTimeout(
      () => this.forceReconnect("network"),
      HEARTBEAT_TIMEOUT_MS,
    );
  }

  // ── Reconnect ───────────────────────────────────────────────────
  private cancelReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect(): void {
    this.cancelReconnect();
    if (this.explicitlyClosed) return;
    if (this.reconnectAttempt >= RECONNECT_MAX_ATTEMPTS) {
      this.opts.onState("error", "network");
      return;
    }
    this.reconnectAttempt += 1;
    const exp = RECONNECT_BASE_MS * 2 ** (this.reconnectAttempt - 1);
    const capped = Math.min(exp, RECONNECT_CAP_MS);
    const jittered = Math.floor(Math.random() * capped);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reopen();
    }, jittered);
  }

  private forceReconnect(reason: string): void {
    this.opts.onState("error", reason);
    const ws = this.ws;
    this.ws = null;
    this.stopHeartbeat();
    if (ws) {
      try {
        ws.close();
      } catch {
        /* already gone */
      }
    }
    this.scheduleReconnect();
  }

  private reopen(): void {
    if (this.explicitlyClosed) return;
    const ws = this.ws;
    this.ws = null;
    if (ws && ws.readyState !== WebSocket.CLOSED) {
      try {
        ws.close();
      } catch {
        /* already gone */
      }
    }
    this.open();
  }

  // ── Wake-from-sleep / network-restored ─────────────────────────
  private bindWakeListeners(): void {
    if (this.wakeListenersBound) return;
    if (typeof window === "undefined") return;
    window.addEventListener("online", this.onWake);
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", this.onVisibility);
    }
    this.wakeListenersBound = true;
  }

  private unbindWakeListeners(): void {
    if (!this.wakeListenersBound) return;
    if (typeof window !== "undefined") {
      window.removeEventListener("online", this.onWake);
    }
    if (typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", this.onVisibility);
    }
    this.wakeListenersBound = false;
  }

  private handleWakeOrOnline(): void {
    if (this.explicitlyClosed) return;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendHeartbeat();
      return;
    }
    if (!this.reconnectTimer) {
      this.reconnectAttempt = 0;
      this.scheduleReconnect();
    }
  }
}
