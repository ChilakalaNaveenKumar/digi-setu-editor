/**
 * Billing client (DESKTOP) — thin redirector.
 *
 * The desktop sidecar has no Stripe code (see desktop/backend/services/
 * billing.py for the full architecture write-up). All real billing
 * operations — Checkout, Customer Portal, webhooks — live on the cloud
 * backend at api.digi-setu.com and are reached through hosted pages on
 * digi-setu.com that the system browser opens for the user.
 *
 * What this module does:
 *
 *   - `getBillingStatus()`     return a synthetic { enabled: true, plans }
 *                              built from the public catalogue. Always
 *                              `enabled` because the redirect path always
 *                              works regardless of local configuration.
 *   - `getPlans()`             fetch the public plan catalogue from the
 *                              local sidecar (which mirrors the cloud's).
 *   - `cloudCheckoutUrl(plan)` URL on digi-setu.com to send the user to
 *                              for an Upgrade click. The cloud reads the
 *                              ?plan= query, creates a Stripe Checkout
 *                              session in the user's authenticated
 *                              browser context, and 302's into Stripe.
 *   - `cloudPortalUrl()`       URL on digi-setu.com that creates a
 *                              Stripe Customer Portal session and
 *                              redirects into it.
 *   - `getUsage()`             polled by the credit chip; the local
 *                              sidecar proxies api.digi-setu.com/api/usage.
 *   - `getUsageEvents()`       Activity table; same proxy.
 *   - `getByokUsage()`         local SQLite token tally for BYOK chats.
 *                              Stays local — no money flows.
 *
 * What this module deliberately does NOT do any more:
 *
 *   - Call POST /api/billing/checkout (returns 410 on the sidecar).
 *   - Call POST /api/billing/portal   (returns 410 on the sidecar).
 *   - Carry any Stripe session ids — those are minted only on the cloud
 *     inside the user's browser session.
 */

import { apiJson } from "./client";
import type { CreditSnapshot, PlanInfo } from "./types";

export interface BillingStatus {
  /** Always true on the desktop now — the redirect to digi-setu.com
   *  works regardless of whether Stripe is configured on this machine
   *  (it isn't and never will be). Kept in the response shape for
   *  parity with the web build's BillingStatus. */
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
  /** Where the snapshot came from. "cloud" = authoritative, fetched
   *  via the sidecar's proxy from api.digi-setu.com. The "offline_*"
   *  variants surface when the cloud is unreachable; the SPA can show
   *  a small "couldn't reach the cloud" hint without panicking. */
  source?: "cloud" | "offline_byok" | "offline_signed_out";
  /** Non-null when ``source`` is offline AND the cloud actually
   *  returned an error (vs. the user being signed-out). For ops, not
   *  surfaced verbatim in the UI. */
  cloud_error?: string | null;
}

interface PlansResponse {
  plans: PlanInfo[];
}

/**
 * Resolve the cloud web base for billing redirects. Same pattern as
 * lib/desktop-auth.ts:_resolveWebAuthBase — VITE override for dev,
 * hard-coded https://digi-setu.com for production builds.
 */
function _cloudWebBase(): string {
  const env = (import.meta as { env?: Record<string, string> }).env;
  const fromEnv = env?.VITE_DIGI_SETU_WEB_BASE || env?.VITE_DESKTOP_AUTH_URL;
  if (fromEnv) return fromEnv.replace(/\/+$/, "");
  return "https://digi-setu.com";
}

/** Public plan catalogue. Sidecar serves the same shape as the cloud. */
export function getPlans(): Promise<PlansResponse> {
  return apiJson("/api/plans");
}

/**
 * Synthesize the {@link BillingStatus} shape from the public plan
 * catalogue. There's no longer a server-side `enabled` flag — billing
 * IS available because we always have somewhere to send the user.
 */
export async function getBillingStatus(): Promise<BillingStatus> {
  const r = await getPlans();
  return {
    enabled: true,
    currency: "usd",
    plans: r.plans,
  };
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
  /** True when at least `limit` rows came back from the cloud — i.e.
   *  there are likely more older entries to load. Drives the "Load
   *  older" button visibility on the Activity page. Conservatively
   *  false when the cloud was unreachable (no point offering a page
   *  we can't actually fetch). */
  has_more: boolean;
  /** "cloud" when the proxy succeeded; "offline*" if the sidecar
   *  couldn't reach api.digi-setu.com. SPA renders a small banner. */
  source?: "cloud" | "offline" | "offline_signed_out";
  cloud_error?: string | null;
}

/**
 * Returns activity events for the signed-in user, newest first.
 * Sidecar forwards this from digi-setu.com — see services/cloud_api.py.
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
 * Default `limit` matches the SPA's call site (100). The proxy
 * forwards all three params verbatim.
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
 * Note: this stays local because BYOK is uncharged by us — there's
 * no money to track on the cloud. Deleting the local file blanks
 * the user's *own* activity log; it cannot grant them free
 * subscription usage.
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

/**
 * URL on digi-setu.com that triggers a Stripe Checkout for the
 * given plan. Caller (the billing store) opens this in the system
 * browser via openExternal(). The cloud route reads the `?plan=`
 * query, creates the Stripe session in the user's signed-in browser
 * context, and 302s into checkout.stripe.com.
 *
 * `?source=desktop` is a soft hint the cloud may use to (a) tag the
 * Stripe session metadata for analytics, and (b) pick a different
 * post-payment landing copy ("you can close this tab and return to
 * the desktop app" instead of "back to your dashboard").
 */
export function cloudCheckoutUrl(planId: string): string {
  const base = _cloudWebBase();
  const params = new URLSearchParams({ plan: planId, source: "desktop" });
  return `${base}/pricing?${params.toString()}`;
}

/**
 * URL on digi-setu.com that creates a Stripe Customer Portal session
 * for the signed-in user. The portal is where users change plans,
 * update cards, and cancel subscriptions — Stripe runs the entire
 * UI; we never reimplement it.
 */
export function cloudPortalUrl(): string {
  const base = _cloudWebBase();
  const params = new URLSearchParams({ source: "desktop" });
  return `${base}/account/billing?${params.toString()}`;
}
