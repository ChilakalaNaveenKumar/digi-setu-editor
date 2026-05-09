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
      // The `error` payload here is a STABLE CODE (matches an
      // `errors.<code>` i18n key), never a raw English string. The
      // chat store is responsible for translating it. This keeps the
      // bridge transport-agnostic and prevents English from sneaking
      // into non-English locales.
      ws.onerror = () => this.opts.onState("error", "network");
      ws.onclose = (e) => {
        // 4401 = "auth required"; surface it as an error so the route
        // guard can bounce the user to /login.
        if (e.code === 4401) {
          this.opts.onState("error", "session_expired");
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
        // 4409 = "conflict / capacity". Two distinct sub-cases the
        // server differentiates via the close `reason` field:
        //   reason starts with "too_many_chats" -> the per-user
        //     concurrent-chat cap is hit; user has to close one of
        //     their other open chats before this one can connect.
        //   anything else -> "kicked by a newer tab". Same session
        //     id was opened somewhere else; we lose.
        // Both go through the same banner pipeline but with different
        // copy + actions, so we propagate them as distinct error codes.
        if (e.code === 4409) {
          const reason = e.reason ?? "";
          if (reason.startsWith("too_many_chats")) {
            this.opts.onState("error", "too_many_chats");
          } else {
            this.opts.onState("error", "session_kicked");
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
          this.opts.onState("error", "rate_limit");
          return;
        }
        this.opts.onState(
          this.explicitlyClosed ? "closed" : "error",
          this.explicitlyClosed ? null : "network",
        );
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
      this.opts.onState("error", "network");
    }
  }

  get isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
