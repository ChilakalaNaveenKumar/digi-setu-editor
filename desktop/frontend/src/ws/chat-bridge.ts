/**
 * WebSocket bridge to `/ws/sessions/{sid}`.
 *
 * Owns the actual WebSocket. Emits raw JSON events to a single dispatcher
 * callback; the chat store routes them to the right slice (chat / files /
 * terminals). Doesn't know about Pinia or Vue.
 */

import { buildWebSocketUrl } from "../api/client";

export type ConnState = "idle" | "connecting" | "open" | "closed" | "error";

export interface BridgeOpts {
  sessionId: string;
  onEvent: (evt: unknown) => void;
  onState: (state: ConnState, error?: string | null) => void;
}

export class ChatBridge {
  private ws: WebSocket | null = null;
  private opts: BridgeOpts;
  private explicitlyClosed = false;

  constructor(opts: BridgeOpts) {
    this.opts = opts;
  }

  open(): void {
    this.explicitlyClosed = false;
    this.opts.onState("connecting");
    // The token resolver is async, so opening is a microtask away. We
    // store the in-flight Promise as `this.ws` only after `await`
    // resolves; sends issued during the gap are silently dropped, which
    // matches the prior `readyState !== OPEN` behaviour.
    const path = `/ws/sessions/${encodeURIComponent(this.opts.sessionId)}`;
    void buildWebSocketUrl(path).then((url) => {
      if (this.explicitlyClosed) return;
      const ws = new WebSocket(url);
      this.ws = ws;
      ws.onopen = () => this.opts.onState("open");
      // Emit STABLE error codes (not English strings). The chat pane
      // / banner translates each code to a friendly localised
      // message via the `ws.error.<code>` i18n namespace. Raw English
      // like "websocket error" used to leak straight to the UI which
      // looked like a debug message escaping into the product.
      ws.onerror = () => this.opts.onState("error", "ws_error");
      ws.onclose = (e) => {
        // 4401 = "auth required"; surface it as an error so the route
        // guard can bounce the user to /login.
        if (e.code === 4401) {
          this.opts.onState("error", "ws_unauthorized");
          return;
        }
        // 4403 = forbidden (relay rejected the JWT — usually clock
        // skew or the cloud relay restarted with a new signing key
        // mid-session). Distinct from 4401 so the UI can hint at
        // "your session expired, sign in again" instead of a generic
        // "not signed in".
        if (e.code === 4403) {
          this.opts.onState("error", "ws_forbidden");
          return;
        }
        // 4408 = prompt timeout (server killed a runaway turn). The
        // chat pane already received a `_bridge_error` with code
        // "prompt_timeout" before the close — surface as a normal
        // closure so we don't double-toast.
        if (e.code === 4408) {
          this.opts.onState("closed");
          return;
        }
        // 4409 = "conflict / capacity". Two sub-cases distinguished
        // by the close `reason`:
        //   "too_many_chats:<n>/<cap>" — desktop window count hit the
        //     server's per-user concurrent-chat cap (default 5). User
        //     must close one of their other windows / tabs.
        //   anything else — a newer tab / window kicked this session.
        if (e.code === 4409) {
          const reason = e.reason ?? "";
          if (reason.startsWith("too_many_chats")) {
            this.opts.onState("error", "ws_too_many_chats");
          } else {
            this.opts.onState("error", "ws_kicked");
          }
          return;
        }
        // 4410 = client-requested abort. Backend killed the pi
        // subprocess to interrupt the in-flight turn. The SPA already
        // received a `_bridge_error` with code "aborted" before the
        // close — chat.ts watches for this state and auto-reconnects
        // so the user can keep chatting without manual intervention.
        if (e.code === 4410) {
          this.opts.onState("closed");
          return;
        }
        // 4429 = WS-level rate limit (connect/spawn bucket exhausted).
        if (e.code === 4429) {
          this.opts.onState("error", "ws_rate_limited");
          return;
        }
        // 4503 / 1011 / 1006 = upstream relay or local sidecar
        // restart. Surface as a retryable network blip so the banner
        // shows "Reconnect" instead of a scarier "session ended".
        if (e.code === 1006 || e.code === 1011 || e.code === 4503) {
          this.opts.onState("error", "ws_unreachable");
          return;
        }
        this.opts.onState(this.explicitlyClosed ? "closed" : "error", this.explicitlyClosed ? null : "ws_error");
      };
      ws.onmessage = (e) => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(typeof e.data === "string" ? e.data : "");
        } catch {
          return;
        }
        this.opts.onEvent(parsed);
      };
    });
  }

  close(): void {
    this.explicitlyClosed = true;
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
}
