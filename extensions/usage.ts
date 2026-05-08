/**
 * Provider → host usage normalization.
 *
 * Each entry expresses the {input, output, cacheRead, cacheWrite} contract
 * that web/backend/services/billing.py:_llm_cost_from_tokens consumes. The
 * shape matches pi-ai's own `Usage` type so the host's cost calculator can
 * be reused verbatim for both pi's main assistant turn and any side-LLM
 * call we make from extension code.
 *
 * Lives in its own file so backend/test code can import it without pulling
 * in the whole pi extension (which has top-level side effects via
 * `pi.registerTool`).
 */

export interface NormalizedUsage {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
}

export interface GeminiUsageMetadata {
	promptTokenCount?: number;
	candidatesTokenCount?: number;
	cachedContentTokenCount?: number;
	thoughtsTokenCount?: number;
}

/**
 * Normalize Gemini's `usageMetadata` into a NormalizedUsage.
 *
 * Two Gemini-specific gotchas the naive copy gets wrong, both of which
 * the host then double-bills for:
 *
 *   1. `promptTokenCount` is INCLUSIVE of cached content. The host bills
 *      `input` at the full input rate AND `cacheRead` at the cache rate
 *      separately, so we subtract the cached share to get true fresh-
 *      input tokens. Pi-ai's google provider does the same — see
 *      node_modules/@mariozechner/pi-ai/dist/providers/google.js around
 *      the "promptTokenCount - cachedContentTokenCount" line.
 *
 *   2. Reasoning models (Gemini 3.x Pro etc.) report invisible
 *      "thinking" tokens via `thoughtsTokenCount`. They cost the
 *      output rate, so we fold them into output, mirroring pi-ai.
 *
 * `cacheWrite` is always 0 because Gemini's API doesn't expose cache-
 * creation tokens distinctly (its implicit prefix cache bills writes at
 * the input rate, which is already counted in `input`).
 */
export function normalizeGeminiUsage(
	meta: GeminiUsageMetadata | undefined,
): NormalizedUsage {
	const prompt = meta?.promptTokenCount ?? 0;
	const cached = meta?.cachedContentTokenCount ?? 0;
	const candidates = meta?.candidatesTokenCount ?? 0;
	const thoughts = meta?.thoughtsTokenCount ?? 0;
	return {
		input: Math.max(0, prompt - cached),
		output: candidates + thoughts,
		cacheRead: cached,
		cacheWrite: 0,
	};
}

export interface AnthropicUsage {
	input_tokens?: number;
	output_tokens?: number;
	cache_read_input_tokens?: number;
	cache_creation_input_tokens?: number;
}

/**
 * Normalize Anthropic's `usage` into a NormalizedUsage.
 *
 * Anthropic's `input_tokens` is already EXCLUSIVE of cache reads — the
 * SDK partitions tokens into the four buckets cleanly, so we just rename
 * fields. No subtraction needed (unlike the Gemini path).
 *
 * `cache_creation_input_tokens` covers the 5-minute ephemeral cache TTL
 * we actually use today. If we ever opt into 1-hour TTL caching the new
 * `cache_creation: { ephemeral_5m_input_tokens, ephemeral_1h_input_tokens }`
 * shape would need plumbing — pi-ai itself doesn't split those today, so
 * we'd be tackling that in tandem.
 */
export function normalizeAnthropicUsage(
	usage: AnthropicUsage | undefined,
): NormalizedUsage {
	return {
		input: usage?.input_tokens ?? 0,
		output: usage?.output_tokens ?? 0,
		cacheRead: usage?.cache_read_input_tokens ?? 0,
		cacheWrite: usage?.cache_creation_input_tokens ?? 0,
	};
}
