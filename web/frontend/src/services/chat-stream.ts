/**
 * chat-stream.ts — thin SSE client for the chat protocol.
 *
 * Replaces the old WebSocket transport. We deliberately keep this file small:
 *
 *   - No reconnect state machine: EventSource auto-reconnects on
 *     transport errors and sends `Last-Event-ID` automatically.
 *   - No heartbeat plumbing: the server emits `:keepalive\n\n`
 *     comments every 20s; the browser consumes them silently.
 *   - No multi-tab kick: the page-level BroadcastChannel guard
 *     (services/tab-claim.ts) prevents two tabs from both pushing
 *     prompts; multiple SSE READERS on the same session are
 *     harmless (the ring buffer fans out to all consumers).
 *
 * Send actions are plain `fetch` POSTs — they carry the user's
 * Clerk session cookie automatically (or a bearer if the SPA put
 * one on `window.__pi_token` for the desktop relay path).
 */

import type { RpcEvent } from "../types/rpc";

export type ChatStreamState =
  | "idle"        // no stream open
  | "connecting"  // EventSource initial open
  | "open"        // stream alive
  | "closed";     // user-driven close (NOT the same as a transport blip;
                  // EventSource self-heals those without firing this).

export interface ChatStreamOpts {
  sessionId: string;
  /** Called for each event arriving on the stream. */
  onEvent: (evt: RpcEvent & Record<string, unknown>) => void;
  /** State transitions for the UI's connection pill. */
  onState: (state: ChatStreamState) => void;
  /** Hard, surface-to-card errors. Soft hiccups don't fire this — the
   *  browser will silently reconnect via EventSource and we see another
   *  `open`. Only errors that EventSource can't recover from (auth
   *  rejected, network gone for >30s, server-side close) reach here.
   */
  onError: (code: string, message?: string) => void;
}

/** How long EventSource is allowed to be in `connecting` before we
 *  surface an error to the user. The browser will keep retrying
 *  silently for hours otherwise — bad UX. */
const CONNECTING_GRACE_MS = 8000;

export class ChatStream {
  private es: EventSource | null = null;
  private opts: ChatStreamOpts;
  private connectingTimer: ReturnType<typeof setTimeout> | null = null;
  private surfacedError = false;

  constructor(opts: ChatStreamOpts) {
    this.opts = opts;
  }

  /** Open the stream. Idempotent — calling twice closes the first. */
  open(): void {
    this.close();
    this.surfacedError = false;
    this.opts.onState("connecting");
    this.armConnectingTimer();

    const url = `/api/sessions/${encodeURIComponent(this.opts.sessionId)}/stream`;
    // `withCredentials: true` ensures the Clerk session cookie is sent
    // even on cross-origin dev (vite 5173 → uvicorn 8000). Same-origin
    // prod doesn't need it but it's harmless.
    const es = new EventSource(url, { withCredentials: true });
    this.es = es;

    es.onopen = () => {
      this.surfacedError = false;
      this.clearConnectingTimer();
      this.opts.onState("open");
    };

    // EventSource fires `onerror` on every transient hiccup AND on
    // permanent failures (auth 401). We can't tell them apart from
    // the event alone — but we can use `es.readyState`:
    //   0 (CONNECTING) → browser is reconnecting; let it.
    //   2 (CLOSED)     → permanent; surface an error.
    es.onerror = () => {
      const state = es.readyState;
      if (state === EventSource.CLOSED) {
        // Auth rejection or server-side close. Surface and stop.
        if (!this.surfacedError) {
          this.surfacedError = true;
          this.opts.onError("network");
        }
        this.opts.onState("closed");
        this.clearConnectingTimer();
        this.es = null;
        return;
      }
      // CONNECTING: browser will retry. Re-arm the grace timer
      // so a flap that won't recover within 8s surfaces.
      this.opts.onState("connecting");
      this.armConnectingTimer();
    };

    // The server omits the SSE `event:` field deliberately so EVERY
    // event lands on onmessage. The dispatcher in chat.ts then
    // routes by the JSON payload's `type` field. (See the footgun
    // note in routes/chat_sse.py:_format_sse for why.)
    es.onmessage = (e: MessageEvent<string>) => {
      this.handlePayload(e.data);
    };
  }

  /** Tear down the EventSource. Safe to call multiple times. */
  close(): void {
    this.clearConnectingTimer();
    if (this.es) {
      this.es.close();
      this.es = null;
      this.opts.onState("closed");
    }
  }

  // ── outgoing actions ──────────────────────────────────────────────
  /** Send a prompt. Returns the server-assigned request_id on success.
   *  Throws on non-2xx so the caller can surface an error toast.
   */
  async sendPrompt(message: string, requestId?: string): Promise<string> {
    const r = await this.post(`/prompt`, { message, request_id: requestId });
    return String((r as { request_id?: string }).request_id ?? "");
  }

  async abort(): Promise<void> {
    await this.post(`/abort`, {});
  }

  async answerPermission(promptId: string, granted: boolean): Promise<void> {
    await this.post(`/permission`, { prompt_id: promptId, granted });
  }

  // ── private ───────────────────────────────────────────────────────
  private async post(suffix: string, body: unknown): Promise<unknown> {
    const url = `/api/sessions/${encodeURIComponent(this.opts.sessionId)}${suffix}`;
    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...maybeBearer(),
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      const code = (detail as { detail?: { code?: string } }).detail?.code
        ?? (detail as { code?: string }).code
        ?? `http_${res.status}`;
      const message = (detail as { detail?: { message?: string } }).detail?.message
        ?? (detail as { message?: string }).message;
      throw new ChatStreamError(code, message ?? `HTTP ${res.status}`);
    }
    return res.json();
  }

  private handlePayload(raw: string): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      // Non-JSON line on an SSE channel — likely a proxy injecting
      // junk. Surface as a soft warning, don't break the stream.
      // eslint-disable-next-line no-console
      console.warn("[chat-stream] non-JSON SSE payload:", raw);
      return;
    }
    if (
      parsed
      && typeof parsed === "object"
      && (parsed as { type?: unknown }).type === "_dropped_events"
    ) {
      // Resume gap — we lagged so far that the ring buffer dropped
      // events. Surface as a non-fatal warning and let chat.ts
      // re-fetch history to re-sync.
      const from = Number((parsed as { from?: number }).from ?? 0);
      const to = Number((parsed as { to?: number }).to ?? 0);
      // eslint-disable-next-line no-console
      console.warn(`[chat-stream] dropped events ${from}..${to}; refetching history`);
      this.opts.onError("dropped_events");
      return;
    }
    this.opts.onEvent(parsed as RpcEvent & Record<string, unknown>);
  }

  private armConnectingTimer(): void {
    this.clearConnectingTimer();
    this.connectingTimer = setTimeout(() => {
      this.connectingTimer = null;
      if (
        this.es
        && this.es.readyState === EventSource.CONNECTING
        && !this.surfacedError
      ) {
        this.surfacedError = true;
        this.opts.onError("network");
      }
    }, CONNECTING_GRACE_MS);
  }

  private clearConnectingTimer(): void {
    if (this.connectingTimer !== null) {
      clearTimeout(this.connectingTimer);
      this.connectingTimer = null;
    }
  }

  get isOpen(): boolean {
    return this.es !== null && this.es.readyState === EventSource.OPEN;
  }
}

export class ChatStreamError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ChatStreamError";
  }
}

function maybeBearer(): Record<string, string> {
  // Same convention as lib/api.ts — the desktop sidecar sets a
  // bearer token on window for cross-origin auth. Web doesn't use
  // this; it relies on the Clerk session cookie via `credentials:
  // include`.
  const tok = (globalThis as { __pi_token?: string }).__pi_token;
  return tok ? { Authorization: `Bearer ${tok}` } : {};
}
