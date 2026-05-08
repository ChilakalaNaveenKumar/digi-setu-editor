/**
 * Live provider probe — calls the real Vertex APIs the way search_docs /
 * web_search do internally, captures the raw usage payload, and emits one
 * JSON object per call to stdout.
 *
 * Why a separate driver instead of asking pi to call search_docs? Because
 * the LLM gets to decide whether to actually USE the tool, which makes a
 * cost-verification test flaky. Here we drive the underlying SDK calls
 * directly so the test is deterministic AND we can compare normalize()
 * output against the raw provider response.
 *
 * The companion Python script (scripts/live_cost_check.py) then runs each
 * captured usage through web/backend/services/billing.py:estimate_prompt_cost
 * to verify the dollar figure matches what we'd actually bill the user.
 *
 * Usage:
 *   source scripts/env.sh
 *   npx tsx scripts/live_provider_probe.ts > /tmp/probe.jsonl
 *
 * Each line is a JSON object:
 *   { call: "...", provider: "...", model: "...", raw: {...}, normalized: {...}, usage_for_billing: {...} }
 *
 * Cost: ~$0.01–0.05 per run (one Anthropic Haiku call + one Gemini Flash
 * call + one Gemini Flash Lite call against tiny corpora).
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { AnthropicVertex } from "@anthropic-ai/vertex-sdk";
import { GoogleGenAI } from "@google/genai";

import {
	normalizeAnthropicUsage,
	normalizeGeminiUsage,
} from "../extensions/usage.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");

function emit(line: object) {
	process.stdout.write(JSON.stringify(line) + "\n");
}

async function loadSmallCorpus(): Promise<string> {
	// fletcher is one of the smaller indexed corpora (~5–10k tokens) and
	// has predictable content, so two back-to-back calls should reliably
	// hit cache the second time round.
	const guidesRoot = path.join(REPO_ROOT, "guides");
	const filePath = path.join(guidesRoot, "fletcher.txt");
	try {
		const txt = await fs.readFile(filePath, "utf8");
		return txt;
	} catch {
		// Fallback: synthetic corpus that's still big enough for cache
		// thresholds (Anthropic requires ≥1024 tokens to cache).
		return "Fletcher diagrams.\n\n".repeat(2000);
	}
}

// ── 1. Anthropic Vertex (search_docs Haiku path) ────────────────────────────

async function probeAnthropic(): Promise<void> {
	const project = process.env.GOOGLE_CLOUD_PROJECT;
	if (!project) throw new Error("GOOGLE_CLOUD_PROJECT not set; source scripts/env.sh");
	const ant = new AnthropicVertex({
		projectId: project,
		region: process.env.PI_VERTEX_ANTHROPIC_LOCATION ?? "global",
	});
	const corpus = await loadSmallCorpus();
	const persona = "You are a Typst documentation responder. Answer concisely.";
	const baseQuery = "How do I create a node in fletcher? Give the exact import line.";

	// Two back-to-back calls so we can verify cache_creation on the first
	// and cache_read on the second.
	for (const callIdx of [1, 2] as const) {
		const blocks = [
			{
				type: "text" as const,
				text: `Fletcher corpus follows. Read what you need; ignore the rest.\n\n${corpus}`,
				cache_control: { type: "ephemeral" as const },
			},
			{
				type: "text" as const,
				text: `User query: ${baseQuery}`,
			},
		];
		const t0 = Date.now();
		const res = await ant.messages.create({
			model: "claude-haiku-4-5",
			max_tokens: 256,
			temperature: 0.0,
			system: persona,
			messages: [{ role: "user", content: blocks }],
		});
		const elapsedMs = Date.now() - t0;
		// biome-ignore lint/suspicious/noExplicitAny: cache_* fields not on typed Usage yet
		const u = res.usage as any;
		const raw = {
			input_tokens: u?.input_tokens ?? 0,
			output_tokens: u?.output_tokens ?? 0,
			cache_read_input_tokens: u?.cache_read_input_tokens ?? 0,
			cache_creation_input_tokens: u?.cache_creation_input_tokens ?? 0,
		};
		const norm = normalizeAnthropicUsage(raw);
		emit({
			call: `anthropic_haiku_call_${callIdx}`,
			provider: "anthropic-vertex",
			model: "claude-haiku-4-5",
			elapsed_ms: elapsedMs,
			raw,
			normalized: norm,
			// What chat_ws.py would actually feed to estimate_prompt_cost:
			usage_for_billing: { ...norm, model: "claude-haiku-4-5" },
		});
	}
}

// ── 2. Gemini grounded search (web_search 2.5 path) ────────────────────────

async function probeGeminiWebSearch(): Promise<void> {
	const project = process.env.GOOGLE_CLOUD_PROJECT;
	if (!project) throw new Error("GOOGLE_CLOUD_PROJECT not set");
	const client = new GoogleGenAI({
		vertexai: true,
		project,
		location: process.env.GOOGLE_CLOUD_LOCATION ?? "global",
	});
	const t0 = Date.now();
	const res = await client.models.generateContent({
		model: "gemini-2.5-flash",
		contents: "Who wrote The Pragmatic Programmer? One sentence.",
		config: {
			temperature: 0.0,
			maxOutputTokens: 200,
			tools: [{ googleSearch: {} }],
		},
	});
	const elapsedMs = Date.now() - t0;
	const meta = res.usageMetadata ?? {};
	const raw = {
		promptTokenCount: meta.promptTokenCount ?? 0,
		candidatesTokenCount: meta.candidatesTokenCount ?? 0,
		cachedContentTokenCount: meta.cachedContentTokenCount ?? 0,
		thoughtsTokenCount: meta.thoughtsTokenCount ?? 0,
		totalTokenCount: meta.totalTokenCount ?? 0,
	};
	const norm = normalizeGeminiUsage(meta);
	emit({
		call: "gemini_flash_web_search",
		provider: "google-vertex",
		model: "gemini-2.5-flash",
		elapsed_ms: elapsedMs,
		raw,
		normalized: norm,
		usage_for_billing: { ...norm, model: "gemini-2.5-flash" },
	});
}

async function main() {
	process.stderr.write("[probe] anthropic haiku x2 (cache write + cache read)…\n");
	await probeAnthropic();
	process.stderr.write("[probe] gemini-2.5-flash + googleSearch (web_search path)…\n");
	await probeGeminiWebSearch();
	process.stderr.write("[probe] done\n");
}

main().catch((err) => {
	process.stderr.write(`[probe] FAILED: ${err?.stack || err}\n`);
	process.exit(1);
});
