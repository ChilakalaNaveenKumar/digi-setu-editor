/**
 * Test the provider→host usage normalization.
 *
 * Run with:
 *   npx tsx extensions/usage.test.ts
 *
 * Uses node:test (zero deps). The shape we're asserting is the one
 * web/backend/services/billing.py:_llm_cost_from_tokens consumes, so a
 * regression here would show up as billing drift.
 */

import { strict as assert } from "node:assert";
import { test } from "node:test";

import { normalizeAnthropicUsage, normalizeGeminiUsage } from "./usage.js";

// ── Gemini ──────────────────────────────────────────────────────────────────

test("gemini: undefined / empty meta zeros out", () => {
	const z = normalizeGeminiUsage(undefined);
	assert.deepEqual(z, { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 });
	assert.deepEqual(
		normalizeGeminiUsage({}),
		{ input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
	);
});

test("gemini: cold call (no cache) — promptTokenCount becomes input verbatim", () => {
	const r = normalizeGeminiUsage({
		promptTokenCount: 1_000,
		candidatesTokenCount: 500,
		cachedContentTokenCount: 0,
	});
	assert.equal(r.input, 1_000);
	assert.equal(r.output, 500);
	assert.equal(r.cacheRead, 0);
	assert.equal(r.cacheWrite, 0);
});

test("gemini: full cache hit — input goes to 0, cacheRead carries the load", () => {
	// This is the regression we just fixed: previously `input` was 50_000
	// AND `cacheRead` was 50_000, so the host paid full input price PLUS
	// cache-read price for the same 50k tokens. After the fix, input=0.
	const r = normalizeGeminiUsage({
		promptTokenCount: 50_000,
		candidatesTokenCount: 800,
		cachedContentTokenCount: 50_000,
	});
	assert.equal(r.input, 0);
	assert.equal(r.output, 800);
	assert.equal(r.cacheRead, 50_000);
	assert.equal(r.cacheWrite, 0);
});

test("gemini: partial cache hit — input is fresh-only, cacheRead is the cached share", () => {
	const r = normalizeGeminiUsage({
		promptTokenCount: 1_000,
		candidatesTokenCount: 500,
		cachedContentTokenCount: 600,
	});
	// 1000 total prompt - 600 cached = 400 fresh input
	assert.equal(r.input, 400);
	assert.equal(r.output, 500);
	assert.equal(r.cacheRead, 600);
	assert.equal(r.cacheWrite, 0);
});

test("gemini: reasoning models — thoughtsTokenCount folds into output", () => {
	// Gemini 3.x Pro / reasoning models report invisible reasoning tokens
	// in `thoughtsTokenCount`. They bill at output rate, so we need them
	// to land in `output`, not be silently lost.
	const r = normalizeGeminiUsage({
		promptTokenCount: 1_000,
		candidatesTokenCount: 500,
		cachedContentTokenCount: 0,
		thoughtsTokenCount: 200,
	});
	assert.equal(r.input, 1_000);
	assert.equal(r.output, 700);
	assert.equal(r.cacheRead, 0);
});

test("gemini: pathological cached > prompt — never goes negative", () => {
	// Defensive: shouldn't happen against real API responses, but if it
	// did the host's cost math would silently flip sign and over-credit.
	const r = normalizeGeminiUsage({
		promptTokenCount: 100,
		candidatesTokenCount: 0,
		cachedContentTokenCount: 9_999,
	});
	assert.equal(r.input, 0);
	assert.equal(r.cacheRead, 9_999);
});

// ── Anthropic ───────────────────────────────────────────────────────────────

test("anthropic: undefined zeros out", () => {
	assert.deepEqual(
		normalizeAnthropicUsage(undefined),
		{ input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
	);
});

test("anthropic: cache write — counted as cacheWrite, not input", () => {
	// First call against the corpus pays the cache-creation rate
	// (cache_write ≈ 1.25× input on Haiku) and that's a one-time hit.
	const r = normalizeAnthropicUsage({
		input_tokens: 250,
		output_tokens: 800,
		cache_read_input_tokens: 0,
		cache_creation_input_tokens: 50_000,
	});
	assert.equal(r.input, 250);
	assert.equal(r.output, 800);
	assert.equal(r.cacheRead, 0);
	assert.equal(r.cacheWrite, 50_000);
});

test("anthropic: cache read — input stays fresh-only, cacheRead is separate", () => {
	// Subsequent call within the 5-minute TTL pays cache_read (~10× off).
	// Note that Anthropic's `input_tokens` is ALREADY exclusive of cached
	// tokens — that's the key difference from Gemini.
	const r = normalizeAnthropicUsage({
		input_tokens: 250,
		output_tokens: 800,
		cache_read_input_tokens: 50_000,
		cache_creation_input_tokens: 0,
	});
	assert.equal(r.input, 250);
	assert.equal(r.cacheRead, 50_000);
	assert.equal(r.cacheWrite, 0);
});

// ── Cost regression: prove the fix actually removes the over-bill ───────────

test("regression: full-cache Gemini call costs 1/10 of the buggy old behaviour", () => {
	// Re-create the bug we just fixed by computing cost two ways:
	//
	//   - "buggy"  — the way the extension USED to set things up:
	//                  input := promptTokenCount,
	//                  cacheRead := cachedContentTokenCount.
	//                Cost: 50_000 × $0.50/Mtok + 50_000 × $0.05/Mtok = $0.0275
	//
	//   - "fixed"  — what normalizeGeminiUsage now produces:
	//                  input := 0, cacheRead := 50_000.
	//                Cost: 50_000 × $0.05/Mtok = $0.0025
	//
	// 11× ratio is the worst-case over-bill on a fully-cached call against
	// Gemini Flash. (Also catches any future drift in normalizeGeminiUsage.)
	const meta = {
		promptTokenCount: 50_000,
		candidatesTokenCount: 0,
		cachedContentTokenCount: 50_000,
	};
	const inputUsd = 0.5 / 1_000_000;
	const cacheUsd = 0.05 / 1_000_000;
	const outputUsd = 3.0 / 1_000_000;

	const buggy =
		meta.promptTokenCount * inputUsd +
		meta.candidatesTokenCount * outputUsd +
		meta.cachedContentTokenCount * cacheUsd;
	const fixedNorm = normalizeGeminiUsage(meta);
	const fixed =
		fixedNorm.input * inputUsd +
		fixedNorm.output * outputUsd +
		fixedNorm.cacheRead * cacheUsd +
		fixedNorm.cacheWrite * inputUsd;

	// 11× ratio: input price is 10× cache_read; the buggy path paid both.
	assert.ok(
		buggy / fixed > 10,
		`expected buggy/fixed > 10, got ${buggy / fixed} (buggy=${buggy} fixed=${fixed})`,
	);
});
