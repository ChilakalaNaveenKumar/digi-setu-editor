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
  /** True when at least `limit` rows came back — i.e. there are
   *  probably more older entries to load. Drives the "Load older"
   *  button visibility on the Activity page. */
  has_more: boolean;
}

/**
 * Returns activity events for the signed-in user, newest first.
 *
 * - `limit`  page size, capped at 500 server-side.
 * - `since`  ISO-8601 UTC. Returns ONLY events strictly after this
 *            time. Used by the Activity page to poll for new rows
 *            without re-shipping the full window every 30s.
 * - `before` ISO-8601 UTC. Returns ONLY events strictly older than
 *            this. Cursor for "Load older" — pass the timestamp of
 *            the oldest visible row to fetch the next page back in
 *            history.
 *
 * The server caps at 500 rows / page; the SPA defaults to 100 so a
 * normal Activity visit is one small payload, not a 500-row dump.
 */
export function getUsageEvents(opts: {
  limit?: number;
  since?: string;
  before?: string;
} = {}): Promise<UsageEventsResponse> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.since) params.set("since", opts.since);
  if (opts.before) params.set("before", opts.before);
  const qs = params.toString();
  return apiJson(`/api/usage/events${qs ? "?" + qs : ""}`);
}

/**
 * One row in the local BYOK ledger (~/.digi-setu/usage.sqlite). Token
 * counts only — we don't compute USD because the user pays their AI
 * provider directly and we don't know their actual rate.
 */
export interface ByokEvent {
  ts: string;
  session_id: string;
  workspace_id: string;
  provider: string;
  model_id: string;
  input_tokens: number;
  output_tokens: number;
  cache_read: number;
  cache_write: number;
}

export interface ByokSummary {
  total: {
    turns?: number;
    input_tokens?: number;
    output_tokens?: number;
    cache_read?: number;
    cache_write?: number;
  };
  per_model: Array<{
    model_id: string;
    provider: string;
    turns: number;
    input_tokens: number;
    output_tokens: number;
  }>;
}

export interface ByokUsageResponse {
  byok_active: boolean;
  events: ByokEvent[];
  summary: ByokSummary;
  limit: number;
  has_more: boolean;
}

/**
 * Fetch BYOK usage rolled up from the local SQLite ledger. The
 * response is empty (and `byok_active=false`) in web mode and in
 * desktop installs without any BYOK keys, so callers don't need to
 * branch on deployment shape.
 *
 * Pagination mirrors `getUsageEvents`: `since` for incremental
 * polling of new rows, `before` for "Load older" history. The
 * `summary` block is always full-history regardless of pagination,
 * so the rollup numbers don't change as the user pages through.
 */
export function getByokUsage(opts: {
  limit?: number;
  since?: string;
  before?: string;
} = {}): Promise<ByokUsageResponse> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.since) params.set("since", opts.since);
  if (opts.before) params.set("before", opts.before);
  const qs = params.toString();
  return apiJson(`/api/usage/byok${qs ? "?" + qs : ""}`);
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
