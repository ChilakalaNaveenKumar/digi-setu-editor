/**
 * tab-claim.ts — single-tab guard for chat sessions.
 *
 * Replaces the WebSocket-layer "kick the older tab" behaviour from
 * services/session_locks.py + chat-bridge.ts. Lives entirely in the
 * browser using BroadcastChannel — the backend doesn't need to
 * know how many tabs the user has open.
 *
 * Protocol on channel `pi-session:<sid>`:
 *
 *   { kind: "claim",       at: <epoch_ms> }   broadcast on mount
 *   { kind: "reply-mine",  at: <epoch_ms> }   the current owner replies
 *   { kind: "release"                      }   broadcast on unmount/relinquish
 *   { kind: "focus"                        }   "please focus your window"
 *
 * Resolution:
 *   1. New tab broadcasts `claim`.
 *   2. Waits 150 ms for any `reply-mine`.
 *   3. If a reply comes back the new tab is the LOSER — shows a
 *      "Already open in another tab → focus there" affordance and
 *      keeps the SSE in read-only mode (no POSTs).
 *   4. Otherwise the new tab is the WINNER and starts answering
 *      `claim`s with `reply-mine` until it unmounts.
 *
 * Why 150 ms: BroadcastChannel inside one browser is ~free
 * (postMessage between same-origin tabs); 150 ms is plenty for
 * a synchronous reply and short enough that the "winner" UI
 * doesn't flicker on first load.
 */

const CLAIM_RESPONSE_TIMEOUT_MS = 150;

export type TabRole = "owner" | "passenger";

export interface TabClaimOpts {
  /** Called when our role flips. Owner tabs may post; passengers may not. */
  onRoleChange: (role: TabRole) => void;
  /** Called when an owner tab broadcasts a focus request to us. We
   *  use `window.focus()` + a tiny visual flash to draw attention. */
  onFocusRequest: () => void;
}

interface ClaimMessage {
  kind: "claim" | "reply-mine" | "release" | "focus";
  at?: number;
}

export class TabClaim {
  private bc: BroadcastChannel | null = null;
  private opts: TabClaimOpts;
  private role: TabRole = "passenger"; // start pessimistic
  private mountedAt: number;
  private claimTimer: ReturnType<typeof setTimeout> | null = null;
  private resolved = false;

  constructor(sessionId: string, opts: TabClaimOpts) {
    this.opts = opts;
    this.mountedAt = Date.now();
    if (typeof BroadcastChannel === "undefined") {
      // Safari iOS Lockdown mode and some embedded contexts strip
      // BroadcastChannel. Fall back to "winner" so chat keeps
      // working — the tradeoff is no multi-tab guard, which is
      // acceptable in degraded environments.
      this.role = "owner";
      queueMicrotask(() => this.opts.onRoleChange("owner"));
      return;
    }
    this.bc = new BroadcastChannel(`pi-session:${sessionId}`);
    this.bc.onmessage = (e: MessageEvent<ClaimMessage>) => this.handle(e.data);
    this.broadcast({ kind: "claim", at: this.mountedAt });
    this.claimTimer = setTimeout(() => {
      this.claimTimer = null;
      if (!this.resolved) {
        this.resolved = true;
        this.role = "owner";
        this.opts.onRoleChange("owner");
      }
    }, CLAIM_RESPONSE_TIMEOUT_MS);
  }

  /** Ask the existing owner to focus its window. Used by the
   *  passenger's "Open the other tab" button. */
  pingFocus(): void {
    this.broadcast({ kind: "focus" });
  }

  /** Voluntarily relinquish ownership (e.g. user closed the chat
   *  pane within this tab without unmounting). */
  release(): void {
    if (this.role === "owner") {
      this.broadcast({ kind: "release" });
      this.role = "passenger";
      this.opts.onRoleChange("passenger");
    }
  }

  destroy(): void {
    if (this.claimTimer !== null) {
      clearTimeout(this.claimTimer);
      this.claimTimer = null;
    }
    if (this.role === "owner") {
      this.broadcast({ kind: "release" });
    }
    if (this.bc) {
      this.bc.close();
      this.bc = null;
    }
  }

  get currentRole(): TabRole {
    return this.role;
  }

  // ── internals ──────────────────────────────────────────────────────
  private broadcast(msg: ClaimMessage): void {
    try {
      this.bc?.postMessage(msg);
    } catch {
      // Channel closed mid-mount — race we can ignore.
    }
  }

  private handle(msg: ClaimMessage): void {
    switch (msg.kind) {
      case "claim": {
        // Someone else just mounted. If we're the owner, announce.
        if (this.role === "owner") {
          this.broadcast({ kind: "reply-mine", at: this.mountedAt });
        }
        break;
      }
      case "reply-mine": {
        // We're the new tab; existing owner replied. We become the
        // passenger. (Or, if we somehow already became owner via
        // timeout race, defer: the older mount wins.)
        if (this.claimTimer !== null) {
          clearTimeout(this.claimTimer);
          this.claimTimer = null;
        }
        if (!this.resolved) {
          this.resolved = true;
          this.role = "passenger";
          this.opts.onRoleChange("passenger");
        } else if (this.role === "owner") {
          // Tie-break: older mount wins.
          const peerAt = msg.at ?? Number.POSITIVE_INFINITY;
          if (peerAt < this.mountedAt) {
            this.role = "passenger";
            this.opts.onRoleChange("passenger");
          }
        }
        break;
      }
      case "release": {
        // Owner stepped down. Promote ourselves and announce so
        // any further claimers know.
        if (this.role !== "owner") {
          this.role = "owner";
          this.opts.onRoleChange("owner");
          this.broadcast({ kind: "reply-mine", at: this.mountedAt });
        }
        break;
      }
      case "focus": {
        // Someone wants attention drawn to whichever tab is active.
        this.opts.onFocusRequest();
        break;
      }
    }
  }
}
