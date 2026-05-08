/**
 * Stripe-backed billing client.
 *
 * Three flows the SPA exercises:
 *   - `getStatus()`           on app boot, to know whether to render
 *                              Upgrade buttons or a "billing not
 *                              configured in this build" notice.
 *   - `startCheckout(plan)`   redirect into Stripe Checkout when the
 *                              user clicks Upgrade.
 *   - `openPortal()`          redirect into the Stripe Customer Portal
 *                              for plan changes / cancellations / card
 *                              updates. We never reimplement that UI.
 *   - `getUsage()`            polled by the credit chip; returns the
 *                              user's monthly $ spend + plan tier.
 */

import { apiJson, apiPost } from "./client";
import type { CreditSnapshot, PlanInfo } from "./types";

export interface BillingStatus {
  enabled: boolean;
  currency: "usd";
  plans: PlanInfo[];
}

export interface UsageResponse {
  rate_limits: {
    day: string;
    tokens_used: number;
    tokens_budget: number;
    messages_today: number;
    limits: Record<string, { capacity: number; refill_per_sec: number }>;
  };
  credit: CreditSnapshot;
}

export function getBillingStatus(): Promise<BillingStatus> {
  return apiJson("/api/billing/status");
}

export function getUsage(): Promise<UsageResponse> {
  return apiJson("/api/usage");
}

/**
 * One row in the usage activity log. Each entry corresponds to a
 * single billable LLM call — either the parent chat turn or a sub-
 * LLM call made inside a tool body (search_docs, web_search, …).
 */
export interface UsageEvent {
  /** ISO-8601 UTC, millisecond precision. */
  ts: string;
  /** "chat" for the parent assistant turn, "tool" for sub-LLM calls. */
  source: "chat" | "tool";
  /** Tool name when `source === "tool"`. Null for chat turns. */
  tool: string | null;
  /** Model id (e.g. "claude-haiku-4-5"). Null only on legacy events. */
  model: string | null;
  /** The chat session this event belongs to. Null if it pre-dates
   *  per-session attribution. */
  session_id: string | null;
  workspace_id: string | null;
  /** Four-class token counts, matching pi's usage payload. */
  tokens: {
    input: number;
    output: number;
    cacheRead: number;
    cacheWrite: number;
  };
  /** Total $ charged for this event (already includes VM amortisation
   *  + infra markup). 0 for free-tier turns or events that pi
   *  reported without cost data. */
  cost_usd: number;
  /** Optional split: llm_usd + vm_usd + margin_usd ≈ total_usd. Not
   *  every event ships breakdown (older callers omitted it). */
  breakdown: {
    llm_usd?: number;
    vm_usd?: number;
    margin_usd?: number;
    total_usd?: number;
  } | null;
}

export interface UsageEventsResponse {
  events: UsageEvent[];
  limit: number;
}

/**
 * Returns the most recent activity events for the signed-in user,
 * newest first. The server keeps a 500-event ring per user; older
 * entries fall off silently. Use `since` (ISO-8601 UTC) to poll
 * incrementally.
 */
export function getUsageEvents(opts: {
  limit?: number;
  since?: string;
} = {}): Promise<UsageEventsResponse> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.since) params.set("since", opts.since);
  const qs = params.toString();
  return apiJson(`/api/usage/events${qs ? "?" + qs : ""}`);
}

export interface CheckoutResponse {
  url: string;
  session_id: string;
}

export function startCheckout(planId: string, returnUrl?: string): Promise<CheckoutResponse> {
  return apiPost("/api/billing/checkout", { plan_id: planId, return_url: returnUrl });
}

export function openPortal(returnUrl?: string): Promise<{ url: string }> {
  return apiPost("/api/billing/portal", { return_url: returnUrl });
}
