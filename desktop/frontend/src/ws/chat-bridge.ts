/**
 * WebSocket bridge to `/ws/sessions/{sid}`.
 *
 * Owns the actual WebSocket. Emits raw JSON events to a single dispatcher
 * callback; the chat store routes them to the right slice (chat / files /
 * terminals). Doesn't know about Pinia or Vue.
 *
 * Resilience features (added after the recurring "Lost connection to chat
 * backend" idle bug — Mac sleep / NAT / Caddy idle timeouts all silently
 * kill the underlying TCP socket while the WebSocket object still reports
 * `readyState=OPEN` until the next send fails):
 *
 *   1. **Client-side heartbeat.** Browsers do NOT send WebSocket pings;
 *      RFC 6455 leaves that to the server. Without an application-level
 *      ping the connection looks alive locally even after every middlebox
 *      between us and the sidecar has reaped it. We send `{type:"ping"}`
 *      every 25 s and expect a `{type:"pong"}` back within 10 s. If the
 *      pong is missing we treat it as dead and trigger reconnect.
 *
 *   2. **Exponential backoff auto-reconnect.** After a "should be
 *      transient" close (1006 abnormal, 1011 internal, 4503 unreachable,
 *      heartbeat-miss), schedule a reconnect at 1s -> 2s -> 4s -> 8s
 *      capped at 15s with full jitter. We do NOT auto-reconnect on
 *      explicit user closes (`close()`), 4401/4403 (auth — needs sign-in),
 *      4408 (prompt timeout — already handled), 4409 (kicked / capacity —
 *      reconnecting would just re-trigger the cap), or 4429 (rate limit
 *      bucket — backing off in code would race the bucket refill).
 *
 *   3. **Wake-from-sleep detection.** macOS / Windows put every TCP
 *      socket into a half-dead state on resume; the OS doesn't deliver a
 *      close event because the socket "looked fine" before sleep. We
 *      listen for `online` and `visibilitychange -> visible` and force
 *      a reconnect if the bridge thinks it's open but the underlying
 *      socket is actually dead (verified with a synchronous send-empty
 *      `ping` that catches readyState drift).
 *
 * The state machine the dispatcher sees stays unchanged — the bridge
 * just re-enters `connecting` -> `open` automatically.
 */

import { buildWebSocketUrl, getApiBase } from "../api/client";
import { isDesktop, restartSidecar } from "../lib/native-bridge";

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

// Health-probe budget when the bridge gives up. We only run this on
// desktop — web's backend is managed externally (load balancer +
// supervisor) so escalating to a "force restart" doesn't make sense.
const HEALTH_PROBE_TIMEOUT_MS = 3_000;

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
        // Construction itself can throw on malformed URLs / CSP violations.
        // Treat as a transient network error and retry with backoff so we
        // don't leave the user stuck staring at "connecting…".
        this.opts.onState("error", "ws_unreachable");
        this.scheduleReconnect();
        return;
      }
      this.ws = ws;
      ws.onopen = () => {
        this.reconnectAttempt = 0;
        this.startHeartbeat();
        this.opts.onState("open");
      };
      ws.onerror = () => this.opts.onState("error", "ws_error");
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
      this.opts.onState("error", "ws_send_failed");
    }
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
    // Heartbeat reply — never leaks to the chat dispatcher.
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
    // 4401 = "auth required"; surface it as an error so the route
    // guard can bounce the user to /login. NOT auto-reconnected —
    // the JWT is the problem; reconnecting would loop.
    if (e.code === 4401) {
      this.opts.onState("error", "ws_unauthorized");
      return;
    }
    if (e.code === 4403) {
      this.opts.onState("error", "ws_forbidden");
      return;
    }
    // 4408 = prompt timeout. Already surfaced via _bridge_error.
    if (e.code === 4408) {
      this.opts.onState("closed");
      return;
    }
    // 4409 = "conflict / capacity". Two sub-cases distinguished
    // by the close `reason`. Neither is auto-reconnectable —
    // closing another tab / waiting is the only fix.
    if (e.code === 4409) {
      const reason = e.reason ?? "";
      if (reason.startsWith("too_many_chats")) {
        this.opts.onState("error", "ws_too_many_chats");
      } else {
        this.opts.onState("error", "ws_kicked");
      }
      return;
    }
    // 4410 = client-requested abort. Closed cleanly.
    if (e.code === 4410) {
      this.opts.onState("closed");
      return;
    }
    // 4429 = rate limit. We surface the error so the SPA can show
    // "you're connecting too fast" but ALSO schedule a longer-than-
    // usual reconnect. The previous version of this code gave up
    // entirely, which left the user stuck on the error banner until
    // they manually clicked Reconnect — even though the bucket
    // refill would have cleared the limit on its own within a
    // minute. The reconnect schedule below uses the existing
    // exponential backoff (1, 2, 4, 8, 15, 15, 15, 15s) which
    // biases us toward retrying AFTER the per-minute refill window
    // has had a chance to add tokens.
    if (e.code === 4429) {
      this.opts.onState("error", "ws_rate_limited");
      if (!this.explicitlyClosed) this.scheduleReconnect();
      return;
    }
    // Transient: 1006 abnormal close (Mac sleep, network drop),
    // 1011 internal server error, 4503 upstream unreachable. These
    // are the codes we auto-reconnect for.
    if (e.code === 1006 || e.code === 1011 || e.code === 4503) {
      this.opts.onState("error", "ws_unreachable");
      if (!this.explicitlyClosed) this.scheduleReconnect();
      return;
    }
    if (this.explicitlyClosed) {
      this.opts.onState("closed");
      return;
    }
    // Anything else (including a normal 1000) when we didn't ask to
    // close: surface as a generic error and try to reconnect. We
    // err on the side of resilience — the worst case is one extra
    // reconnect attempt, the alternative is a frozen UI.
    this.opts.onState("error", "ws_error");
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
      // Send threw → socket is dead even though readyState lied.
      this.forceReconnect("ws_unreachable");
      return;
    }
    this.clearHeartbeatTimeout();
    this.heartbeatTimeoutTimer = setTimeout(
      () => this.forceReconnect("ws_unreachable"),
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
      this.opts.onState("error", "ws_unreachable");
      // Last-resort self-heal: the WS layer has tried 8 times in 30
      // seconds and the backend isn't answering. The most likely
      // cause is a wedged/crashed sidecar. On desktop we can ask
      // Tauri's watchdog to nuke and respawn; the watchdog will
      // emit `backend-restarted` with the new port and main.ts
      // will trigger a fresh reconnect via `reanchorBridge`.
      // We DON'T call this on web: the cloud backend is managed by
      // a process supervisor + load balancer, "restart it from the
      // browser" isn't an option.
      void this.escalateToSidecarRestart();
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

  /**
   * Probe `/healthz` directly. If it answers, the WS layer was the
   * problem (auth glitch, port confused, browser cache), not the
   * sidecar — let the user click Reconnect manually. If it times
   * out / errors, the sidecar is actually down; ask Tauri to
   * respawn it.
   *
   * We cap at one escalation per bridge instance — repeated automatic
   * restarts within a session would mask a deeper problem (e.g. a
   * panic on every boot) and look like a flapping app to the user.
   */
  private hasEscalated = false;
  private async escalateToSidecarRestart(): Promise<void> {
    if (this.hasEscalated) return;
    if (!isDesktop()) return;
    this.hasEscalated = true;

    const base = getApiBase();
    if (!base) return;

    const healthy = await this.probeHealthz(base);
    if (healthy) {
      console.warn(
        "[chat-bridge] WS unreachable but /healthz answered; not escalating to sidecar restart",
      );
      return;
    }

    console.warn(
      "[chat-bridge] WS + /healthz both dead; asking Tauri watchdog to respawn the sidecar",
    );
    try {
      await restartSidecar();
    } catch (exc) {
      console.error("[chat-bridge] restartSidecar IPC failed", exc);
    }
  }

  private async probeHealthz(base: string): Promise<boolean> {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), HEALTH_PROBE_TIMEOUT_MS);
    try {
      const r = await fetch(`${base}/healthz`, {
        method: "GET",
        signal: ctrl.signal,
        cache: "no-store",
      });
      return r.ok;
    } catch {
      return false;
    } finally {
      clearTimeout(t);
    }
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
    // The OS told us we woke / came back online. We can't trust
    // the socket's readyState (it lies after sleep) — kick a fresh
    // heartbeat. If the pong doesn't come back in time, the timeout
    // will trigger forceReconnect.
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendHeartbeat();
      return;
    }
    // Socket closed / closing — make sure a reconnect is queued.
    if (!this.reconnectTimer) {
      this.reconnectAttempt = 0;
      this.scheduleReconnect();
    }
  }
}
