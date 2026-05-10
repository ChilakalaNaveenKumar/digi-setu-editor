/**
 * Typst tools for pi-coding-agent.
 *
 * Compile / render / inspect happens via pi's built-in `bash` tool — no wrapper.
 * The system prompt teaches the recipes (compile, render PNG, then `read` the
 * PNG to look at the actual page).
 *
 * Tools registered here are only the things bash CAN'T do — i.e. side-LLM calls
 * and network access:
 *   - search_docs    → routes a brief to a Flash-Lite responder loaded with the
 *                       full corpus for one indexed package (typst | cetz |
 *                       fletcher | quill | codly | circuiteria | touying).
 *   - web_search     → grounded Google Search via Gemini's first-party
 *                       `googleSearch` tool. Returns synthesised answer + cited
 *                       URLs. For anything outside the indexed docs corpus.
 *   - open_url       → raw fetch of one URL, HTML stripped to plain markdown-ish
 *                       text. The agent's way to actually read a cited source
 *                       (or any link the user pasted) end-to-end.
 *   - list_fonts     → wraps `typst fonts` with optional substring filter; kept
 *                       only because it's the one shell call the agent makes on
 *                       basically every doc and trace clarity matters.
 *   - list_packages  → returns the pinned import lines.
 *
 * Auth: uses Google Vertex AI via Application Default Credentials. Make sure
 *   GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are set in the environment
 *   and `gcloud auth application-default login` has been run.
 */

import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { GoogleGenAI } from "@google/genai";
import { AnthropicVertex } from "@anthropic-ai/vertex-sdk";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";

import { normalizeAnthropicUsage, normalizeGeminiUsage } from "./usage.js";

const exec = promisify(execFile);

// ── Corpus configuration ────────────────────────────────────────────────────

interface PackageSpec {
	key: string;
	prefix: string;
	label: string;
	blurb: string;
}

const PACKAGES: PackageSpec[] = [
	{
		key: "cetz",
		prefix: "guides/cetz/",
		label: "CeTZ",
		blurb: "vector drawing — `canvas`, `draw`, `line`, `circle`, `content`, `decorations`",
	},
	{
		key: "fletcher",
		prefix: "guides/fletcher/",
		label: "Fletcher",
		blurb: "diagrams over CeTZ — `diagram`, `node`, `edge`, marks, layout",
	},
	{
		key: "quill",
		prefix: "guides/quill/",
		label: "Quill",
		blurb: "quantum circuit diagrams — `quantum-circuit`, `gate`, `ctrl`, `mqgate`, `meter`",
	},
	{
		key: "codly",
		prefix: "guides/codly/",
		label: "Codly",
		blurb: "code-block styling — `codly()`, `codly-init`, line numbers, language pills, highlights",
	},
	{
		key: "circuiteria",
		prefix: "guides/circuiteria/",
		label: "Circuiteria",
		blurb: "block circuit diagrams — `element.block/alu/multiplexer`, `wire.direct/zigzag/dodge`, gates",
	},
	{
		key: "touying",
		prefix: "guides/touying/",
		label: "Touying",
		blurb: "slide framework — themes, slide envelopes, `#pause`, `#meanwhile`, `only`/`uncover`",
	},
];

const PACKAGE_BY_KEY = new Map(PACKAGES.map((p) => [p.key, p]));
const VALID_CORPORA = new Set<string>(["typst", ...PACKAGES.map((p) => p.key)]);

// Default to Gemini 3 Flash because the core Typst corpus is ~210k tokens,
// past Haiku 4.5's 200k window. Operators can still pin Haiku via
// PI_TYPST_ROUTER_MODEL=claude-haiku-4-5 if they only ever query third-party
// packages (cetz/codly/fletcher/…), all of which fit comfortably in 200k.
const ROUTER_MODEL = process.env.PI_TYPST_ROUTER_MODEL ?? "gemini-3-flash-preview";

// Anthropic-on-Vertex region for the search_docs responder. Default "global"
// because Claude Haiku 4.5 is GA there. Override via PI_VERTEX_ANTHROPIC_LOCATION.
const ANTHROPIC_VERTEX_LOCATION = process.env.PI_VERTEX_ANTHROPIC_LOCATION ?? "global";

// Detect whether ROUTER_MODEL is a Claude model → use Anthropic Vertex SDK and
// emit cache_control on the corpus block so back-to-back lookups on the same
// package read from cache (~90% off) instead of paying full freight every call.
const ROUTER_IS_ANTHROPIC = /^claude-/.test(ROUTER_MODEL);

// Grounded Google Search runs through here. 2.5-flash bills grounding per
// *prompt* (cheap & predictable). The 3.x series bills per *query* and Gemini
// often fans one brief out into 4-5 separate searches → costs explode.
// Override via PI_TYPST_WEB_SEARCH_MODEL if your Vertex IAM only allows a
// different SKU.
const WEB_SEARCH_MODEL = process.env.PI_TYPST_WEB_SEARCH_MODEL ?? "gemini-2.5-flash";

// Hard caps for fetched URL bodies so a single call can't blow up the agent's
// context. Generous enough to keep most articles in one piece.
const OPEN_URL_MAX_BYTES = 1_500_000; // network read
const OPEN_URL_MAX_CHARS = 30_000;    // post-strip text returned to the agent
const OPEN_URL_TIMEOUT_MS = 20_000;

// ── Corpus loader (lazy, in-memory cache) ───────────────────────────────────

// Vendored upstream source folders live alongside the curated docs, named
// `<pkg>-<semver>/` (e.g. `typst-0.14.2/`, `cetz-0.5.0/`, `quill-0.7.2/`).
// Those trees are kept on disk so the AI can `read`/`grep` them as a
// source-of-truth oracle (see RULE 0.5 in .pi/APPEND_SYSTEM.md), but they
// must NOT be swept into the `search_docs` corpus — they contain hundreds
// of test files, upstream docs, and examples that would (a) bloat the
// `typst` bucket past Gemini Flash's 1M-token context window and
// (b) cross-contaminate it with off-package content (cetz tests landing
// in the typst corpus, etc.).
//
// Match any top-level guides subdirectory whose name ends in a semver
// triple — that's the convention the vendoring script uses, distinct from
// the curated docs folders (`cetz/`, `codly/`, `quill/`, `reference/`, …)
// which never carry a version suffix.
const VENDORED_SOURCE_DIR_RE = /-\d+\.\d+\.\d+$/;

let corpusCache: Map<string, string> | null = null;

async function loadCorpus(guidesRoot: string): Promise<Map<string, string>> {
	if (corpusCache) return corpusCache;

	const dump = new Map<string, string>();

	async function walk(dir: string): Promise<string[]> {
		const out: string[] = [];
		const entries = await fs.readdir(dir, { withFileTypes: true });
		for (const e of entries) {
			const full = path.join(dir, e.name);
			if (e.isDirectory()) {
				if (VENDORED_SOURCE_DIR_RE.test(e.name)) continue;
				out.push(...(await walk(full)));
			} else if (e.isFile() && (e.name.endsWith(".md") || e.name.endsWith(".typ"))) {
				out.push(full);
			}
		}
		return out;
	}

	const files = await walk(guidesRoot);

	const buckets = new Map<string, string[]>();
	buckets.set("typst", []);
	for (const p of PACKAGES) buckets.set(p.key, []);

	for (const file of files) {
		const rel = `guides/${path.relative(guidesRoot, file).replace(/\\/g, "/")}`;
		let owner = "typst";
		for (const p of PACKAGES) {
			if (rel.startsWith(p.prefix)) {
				owner = p.key;
				break;
			}
		}
		const body = await fs.readFile(file, "utf8");
		buckets.get(owner)!.push(`---\n# FILE: ${rel}\n---\n${body}\n`);
	}

	for (const [k, chunks] of buckets) dump.set(k, chunks.join("\n"));
	corpusCache = dump;
	return dump;
}

interface ResponderParts {
	persona: string;
	rules: string;
	corpus: string;
	query: string;
}

function buildResponderParts(query: string, corpusDump: string, corpus: string): ResponderParts {
	const persona =
		corpus === "typst"
			? "You're a senior Typst engineer. The user is working in core Typst (no third-party packages). The full text of every core-Typst doc and example file is in your context."
			: `You're a senior engineer who knows the ${PACKAGE_BY_KEY.get(corpus)!.label} Typst package cold. ${
					PACKAGE_BY_KEY.get(corpus)!.label
				}: ${PACKAGE_BY_KEY.get(corpus)!.blurb}. The full text of every doc and example file in that package is in your context.`;

	const rules = `Another agent will read your reply and use it to write and compile a real Typst artifact. So your reply IS the answer, not a routing memo.

Rules:
- Go deep. Don't give an overview — give a full, in-depth explanation. Cover what the relevant symbols do, what each parameter means, and how the pieces compose.
- Show 2-3 fully-formed copy-paste examples (15-60 lines each). Each example should target a different real use case, not three variations of the same thing. Walk through at least one of them inline so the reader sees why each line is there.
- Call out non-obvious behaviours, common pitfalls, parameter combinations that matter, and edge cases (units, defaults, scope, layout interactions).
- Use the exact symbol names and import lines from the corpus. If the question touches multiple packages, say which package owns each symbol.
- If the corpus genuinely doesn't cover the question, say so plainly in one line; don't invent API.
- Do NOT print a "Sources" section, a citations footer, or any list of doc paths. The agent doesn't need them.
- No preamble. No "great question". Just the answer.`;

	return { persona, rules, corpus: corpusDump, query };
}

// Legacy single-string builder kept for the Gemini path (no cache markers
// needed — Vertex Gemini handles prefix caching implicitly).
function buildResponderPrompt(query: string, corpusDump: string, corpus: string): string {
	const p = buildResponderParts(query, corpusDump, corpus);
	return `${p.persona}

${p.rules}

The user's brief:
${p.query}

The full corpus follows. Read what you need, ignore the rest.

${p.corpus}`;
}

function splitAnswerAndSources(raw: string): { answer: string; cited: string[] } {
	const idx = raw.search(/\n\s*Sources?\s*:?\s*\n/i);
	if (idx < 0) {
		const inline = [...raw.matchAll(/`?(guides\/[A-Za-z0-9_./-]+\.(?:md|typ))`?/g)].map((m) => m[1]);
		return { answer: raw.trim(), cited: [...new Set(inline)] };
	}
	const answer = raw.slice(0, idx).trim();
	const tail = raw.slice(idx).split(/\n/).slice(1);
	const cited = tail
		.map((l) => l.replace(/^[\s*\-•]+/, "").trim())
		.map((l) => l.replace(/^`|`$/g, "").trim())
		.filter((l) => /^guides\//.test(l) && /\.(md|typ)$/.test(l));
	return { answer, cited: [...new Set(cited)] };
}

// ── HTML → plain-text-ish stripper for open_url ─────────────────────────────
//
// Deliberately dependency-free. We don't need perfect markdown — we need
// something the writing agent can read end-to-end without choking on
// `<script>` blobs or 200 nested `<div>`s. The recipe:
//   1. drop entire <script>, <style>, <noscript>, <template>, <svg> blocks
//   2. drop HTML comments
//   3. block-level tags become double newlines; <br> → newline; <li> → "- "
//   4. <strong>/<b> → **…**, <em>/<i> → *…*, <code> → `…`
//   5. <a href="x">text</a> → "text (x)" so the agent sees the URL inline
//   6. strip remaining tags
//   7. decode the handful of entities that actually matter
//   8. collapse runs of blank lines
//
// Good enough for news articles, blog posts, MDN-style refs, and most static
// docs. SPA shells with no SSR'd body return a near-empty result — that's
// actually the honest answer.
function htmlToText(html: string): string {
	let s = html;
	s = s.replace(/<!--[\s\S]*?-->/g, "");
	s = s.replace(/<(script|style|noscript|template|svg)\b[^>]*>[\s\S]*?<\/\1>/gi, "");
	s = s.replace(/<a\b[^>]*?href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi, (_m, href, txt) => {
		const inner = txt.replace(/<[^>]+>/g, "").trim();
		if (!inner) return ` (${href}) `;
		if (inner === href) return ` ${href} `;
		return ` ${inner} (${href}) `;
	});
	s = s.replace(/<(strong|b)\b[^>]*>([\s\S]*?)<\/\1>/gi, "**$2**");
	s = s.replace(/<(em|i)\b[^>]*>([\s\S]*?)<\/\1>/gi, "*$2*");
	s = s.replace(/<code\b[^>]*>([\s\S]*?)<\/code>/gi, "`$1`");
	s = s.replace(/<li\b[^>]*>/gi, "\n- ");
	s = s.replace(/<\/li\s*>/gi, "");
	s = s.replace(/<br\s*\/?>/gi, "\n");
	s = s.replace(/<\/(p|div|section|article|header|footer|main|aside|nav|h[1-6]|ul|ol|tr|table|blockquote|pre)\s*>/gi, "\n\n");
	s = s.replace(/<(p|div|section|article|header|footer|main|aside|nav|h[1-6]|ul|ol|tr|table|blockquote|pre)\b[^>]*>/gi, "\n\n");
	s = s.replace(/<[^>]+>/g, "");
	s = s.replace(/&nbsp;/g, " ")
		.replace(/&amp;/g, "&")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&quot;/g, '"')
		.replace(/&#39;|&apos;/g, "'")
		.replace(/&#(\d+);/g, (_m, n) => String.fromCharCode(parseInt(n, 10)))
		.replace(/&#x([0-9a-f]+);/gi, (_m, n) => String.fromCharCode(parseInt(n, 16)));
	s = s.replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
	return s;
}

// ── Extension entry point ───────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
	const cwd = process.cwd();
	const guidesRoot = path.join(cwd, "guides");
	const project = process.env.GOOGLE_CLOUD_PROJECT;
	const location = process.env.GOOGLE_CLOUD_LOCATION ?? "us-central1";

	let genai: GoogleGenAI | null = null;
	function getGenai(): GoogleGenAI {
		if (genai) return genai;
		if (!project) {
			throw new Error(
				"GOOGLE_CLOUD_PROJECT is not set. Export it (and GOOGLE_CLOUD_LOCATION) so search_docs can call Vertex via ADC.",
			);
		}
		genai = new GoogleGenAI({
			vertexai: true,
			project,
			location,
		});
		return genai;
	}

	// Anthropic-on-Vertex client used when ROUTER_MODEL is a Claude model.
	// Same ADC the google-vertex provider uses (gcloud application-default).
	// We hold the corpus in a `cache_control: ephemeral` block so back-to-back
	// search_docs calls on the same package read from prompt cache (~90% off).
	let anthropicVertex: AnthropicVertex | null = null;
	function getAnthropicVertex(): AnthropicVertex {
		if (anthropicVertex) return anthropicVertex;
		if (!project) {
			throw new Error(
				"GOOGLE_CLOUD_PROJECT is not set. Export it (and GOOGLE_CLOUD_LOCATION) so search_docs can call Anthropic on Vertex via ADC.",
			);
		}
		anthropicVertex = new AnthropicVertex({
			projectId: project,
			region: ANTHROPIC_VERTEX_LOCATION,
		});
		return anthropicVertex;
	}

	// Compile / render lives in pi's built-in `bash` tool. The system prompt
	// teaches: `typst compile --root . main.typ main.pdf` for fast feedback,
	// `typst compile --root . --format png main.typ main-{n}.png` then `read`
	// each png to actually look at the rendered pages before declaring done.

	// ── search_docs ────────────────────────────────────────────────────────
	pi.registerTool({
		name: "search_docs",
		label: "Search Typst Docs",
		description: [
			"Ask a senior Typst engineer (running in a side LLM that already has the full doc corpus for the chosen package loaded into its context) for an in-depth, code-bearing answer.",
			"",
			"Pick the smallest relevant `package` so the responder only sees the corpus that matters:",
			"  typst        — core Typst language and stdlib (no third-party packages)",
			"  cetz         — vector drawing primitives (canvas, draw, line, etc.)",
			"  fletcher     — diagrams built on CeTZ (diagram, node, edge)",
			"  quill        — quantum circuit diagrams",
			"  codly        — code-block styling",
			"  circuiteria  — block-level circuit diagrams",
			"  touying      — slide / presentation framework with themes",
			"",
			"HOW TO WRITE `query`: the responder is NOT a search engine — it already has every doc in context. It needs detail, intent, and expectations from you. The richer your brief, the more targeted and code-specific the answer comes back. A keyword (`codly highlights`) gets a generic overview; a detailed brief gets exact paste-ready code.",
			"",
			"Pack every `query` with whichever of these apply:",
			"  - Goal — the artifact / behaviour you're producing, not just a feature name (e.g. '30-line Rust listing with lines 4-7 highlighted in muted yellow with a left bar marker').",
			"  - Concrete symbols + parameter names + the exact import line you're using.",
			"  - What you already tried AND the verbatim compiler error or wrong visual you got back.",
			"  - Constraints — page size, fonts, palette, must-not-break-pagination, must-fit-one-page, accessibility.",
			"  - Edge cases you need covered — multiple ranges, nested usage, interaction with another package, etc.",
			"  - What you want IN the answer — full pasteable snippet, parameter-by-parameter explanation, both `set` and `show` forms, etc.",
			"",
			"⚠ IMPORTANT: search_docs returns a HYPOTHESIS, not ground truth. The responder LLM synthesises from a doc corpus that may be incomplete; it can confidently invent plausible workarounds that don't match the actual language. After getting an answer, VALIDATE against the vendored source under `guides/<pkg>-<version>/src/` (or `guides/typst-0.14.2/crates/typst-library/src/` for core typst) — confirm the function exists, its parameters match, and its default behaviour matches what was claimed. Especially when the proposed answer is a workaround using `move(...)`, `box(baseline: ...)`, or a custom show rule, search the source for a first-class API in the same area BEFORE accepting it. See RULE 0.5 in the system prompt for the full validation protocol.",
			"",
			"Returns the responder's freeform markdown answer plus the doc paths it cited.",
		].join("\n"),
		promptSnippet:
			"search_docs(query, package) — responder LLM with the full corpus loaded; pass a DETAILED brief (goal + symbols + what you tried + verbatim error + constraints + what to include), NOT keywords; returns an in-depth HYPOTHESIS — validate against the vendored source under guides/<pkg>-<version>/src/ before shipping (see RULE 0.5).",
		parameters: Type.Object({
			query: Type.String({
				description:
					"Detailed natural-language brief — NOT keywords. The responder already has the full corpus in context; it doesn't search, it synthesises, so the more you tell it, the more precise the answer. Include: (a) the GOAL (the artifact / behaviour you're producing), (b) concrete SYMBOLS + parameter names + the exact import line, (c) what you TRIED and the verbatim compiler error or wrong visual, (d) CONSTRAINTS (page size / fonts / palette / pagination), (e) EDGE CASES you need covered, (f) what you want IN the answer (full snippet, parameter-by-parameter explanation, both `set` and `show` forms, etc.). Example: \"With codly 1.3.0, I'm rendering a 30-line Rust listing and need lines 4-7 highlighted in muted yellow with a left bar marker. What is the exact shape of the `highlights:` argument? Can one codly(...) call accept multiple non-contiguous ranges (4-7 AND 12-14)? I tried `highlights: ((4, 7))` and got `error: expected array of dictionaries`. Give me the full snippet plus an explanation of why each parameter is shaped that way.\"",
			}),
			package: Type.Union(
				[
					Type.Literal("typst"),
					Type.Literal("cetz"),
					Type.Literal("fletcher"),
					Type.Literal("quill"),
					Type.Literal("codly"),
					Type.Literal("circuiteria"),
					Type.Literal("touying"),
				],
				{ description: "Which corpus to load." },
			),
		}),
		execute: async (_id, params) => {
			// `usage` is the contract the host ledger expects: same field names
			// as pi's message_end.usage so estimate_prompt_cost can be reused
			// verbatim. `model` lets the ledger price it correctly per provider.
			type SearchDetails = {
				ok: boolean;
				package?: string;
				cited?: string[];
				elapsedMs?: number;
				fallback?: string;
				error?: string;
				usage?: {
					input: number;
					output: number;
					cacheRead: number;
					cacheWrite: number;
					model: string;
				};
			};
			if (!VALID_CORPORA.has(params.package)) {
				const details: SearchDetails = { ok: false, error: `invalid package ${params.package}` };
				return {
					content: [{ type: "text" as const, text: `Invalid package: ${params.package}` }],
					details,
					isError: true,
				};
			}

			// ── Remote mode (desktop cloud-relay path) ────────────────────────
			// When PI_TYPST_DOCS_REMOTE_URL is set, the corpus + LLM call live
			// on the server (see web/backend/routes/typst_docs.py). The tool
			// becomes a thin POST so we don't ship 1-2 MB of corpus over the
			// wire on every search_docs invocation, and Vertex's prefix cache
			// hits across users for ~90% off + sub-second response.
			//
			// Set by services/relay_spawn.py on the desktop sidecar; pointed
			// at the localhost JWT-injecting proxy which forwards to
			// ${PI_CLOUD_API_BASE}/v1/typst/search_docs. Empty / unset on web
			// + BYOK so the existing local-LLM path runs unchanged.
			const remoteUrl = (process.env.PI_TYPST_DOCS_REMOTE_URL ?? "").trim();
			if (remoteUrl) {
				const t0Remote = Date.now();
				try {
					const resp = await fetch(remoteUrl, {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							package: params.package,
							query: params.query,
						}),
					});
					if (!resp.ok) {
						const bodyText = await resp.text().catch(() => "");
						const details: SearchDetails = {
							ok: false,
							error: `remote search_docs failed: HTTP ${resp.status} ${bodyText.slice(0, 300)}`,
						};
						return {
							content: [{
								type: "text" as const,
								text: `search_docs failed (${params.package}): HTTP ${resp.status}`,
							}],
							details,
							isError: true,
						};
					}
					const data = (await resp.json()) as {
						answer: string;
						cited?: string[];
						elapsedMs?: number;
						model?: string;
						usage?: { input: number; output: number; cacheRead: number; cacheWrite: number };
					};
					const elapsed = data.elapsedMs ?? Date.now() - t0Remote;
					const model = data.model ?? ROUTER_MODEL;
					const usage = data.usage ?? { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
					const tokInfo = usage.cacheRead || usage.cacheWrite
						? `in=${usage.input} (cached_read=${usage.cacheRead}${usage.cacheWrite ? ` cached_write=${usage.cacheWrite}` : ""}) out=${usage.output}`
						: `in=${usage.input} out=${usage.output}`;
					const header = `Package: ${params.package} · model: ${model} · ${elapsed}ms · ${tokInfo} · remote`;
					const details: SearchDetails = {
						ok: true,
						package: params.package,
						cited: data.cited ?? [],
						elapsedMs: elapsed,
						usage: { ...usage, model },
					};
					return {
						content: [{ type: "text" as const, text: `${header}\n\n${data.answer}` }],
						details,
					};
				} catch (err: unknown) {
					const msg = err instanceof Error ? err.message : String(err);
					const details: SearchDetails = { ok: false, error: `remote: ${msg}` };
					return {
						content: [{
							type: "text" as const,
							text: `search_docs failed (${params.package}): ${msg}`,
						}],
						details,
						isError: true,
					};
				}
			}

			const t0 = Date.now();
			const dump = await loadCorpus(guidesRoot);
			const corpusText = dump.get(params.package) ?? "";
			if (!corpusText.trim()) {
				const details: SearchDetails = { ok: false, fallback: "empty corpus" };
				return {
					content: [{ type: "text" as const, text: `Empty corpus for ${params.package} (looked under ${guidesRoot})` }],
					details,
					isError: true,
				};
			}
			try {
				let raw: string;
				let cacheRead = 0;
				let cacheWrite = 0;
				let inputTok = 0;
				let outputTok = 0;

				if (ROUTER_IS_ANTHROPIC) {
					// ── Claude path: split system/persona/corpus/query and
					// mark the corpus block ephemeral so repeat lookups hit cache.
					const parts = buildResponderParts(params.query, corpusText, params.package);
					const ant = getAnthropicVertex();
					// AnthropicVertex SDK uses snake_case for cache_control under the hood.
					// We type the request loosely because the typed surface lags behind
					// what the API actually accepts (and what the Anthropic provider in
					// pi-ai already emits successfully today).
					// biome-ignore lint/suspicious/noExplicitAny: cache_control marker not in static types
					const userBlocks: any[] = [
						{
							type: "text",
							text: `The full ${params.package} corpus follows. Read what you need; ignore the rest.\n\n${parts.corpus}`,
							cache_control: { type: "ephemeral" },
						},
						{
							type: "text",
							text: `${parts.rules}\n\nThe user's brief:\n${parts.query}`,
						},
					];
					const res = await ant.messages.create({
						model: ROUTER_MODEL,
						max_tokens: 4096,
						temperature: 0.2,
						system: parts.persona,
						messages: [{ role: "user", content: userBlocks }],
					});
					raw = res.content
						.filter((b) => b.type === "text")
						.map((b) => (b as { text: string }).text)
						.join("\n")
						.trim();
					// biome-ignore lint/suspicious/noExplicitAny: cache fields not on typed Usage yet
					const norm = normalizeAnthropicUsage(res.usage as any);
					inputTok = norm.input;
					outputTok = norm.output;
					cacheRead = norm.cacheRead;
					cacheWrite = norm.cacheWrite;
				} else {
					// ── Gemini path: implicit prefix cache, single concatenated prompt.
					const prompt = buildResponderPrompt(params.query, corpusText, params.package);
					const client = getGenai();
					const res = await client.models.generateContent({
						model: ROUTER_MODEL,
						contents: prompt,
						config: {
							temperature: 0.2,
							maxOutputTokens: 30_000,
						},
					});
					raw = (res.text ?? "").trim();
					// normalizeGeminiUsage handles the prompt-vs-cached subtraction
					// and folds reasoning tokens into output so the host ledger
					// can't double-count them. See helper docstring.
					const norm = normalizeGeminiUsage(res.usageMetadata);
					inputTok = norm.input;
					outputTok = norm.output;
					cacheRead = norm.cacheRead;
					cacheWrite = norm.cacheWrite;
				}

				if (!raw) {
					const details: SearchDetails = { ok: false, fallback: "empty response" };
					return {
						content: [{ type: "text" as const, text: `Responder returned empty for ${params.package}` }],
						details,
						isError: true,
					};
				}
				// `cited` is still parsed (so the audit trail under
				// `details.cited` keeps working for ops debugging), but we
				// never render it back into the chat: the Sources footer
				// is noise the agent doesn't need and the user doesn't
				// want to see.
				const { answer, cited } = splitAnswerAndSources(raw);
				const elapsed = Date.now() - t0;
				const tokInfo =
					cacheRead || cacheWrite
						? `in=${inputTok} (cached_read=${cacheRead}${cacheWrite ? ` cached_write=${cacheWrite}` : ""}) out=${outputTok}`
						: `in=${inputTok} out=${outputTok}`;
				const header = `Package: ${params.package} · model: ${ROUTER_MODEL} · ${elapsed}ms · ${tokInfo}`;
				const details: SearchDetails = {
					ok: true,
					package: params.package,
					cited,
					elapsedMs: elapsed,
					usage: {
						input: inputTok,
						output: outputTok,
						cacheRead,
						cacheWrite,
						model: ROUTER_MODEL,
					},
				};
				return {
					content: [{ type: "text" as const, text: `${header}\n\n${answer}` }],
					details,
				};
			} catch (err: unknown) {
				const msg = err instanceof Error ? err.message : String(err);
				const details: SearchDetails = { ok: false, error: msg };
				return {
					content: [{ type: "text" as const, text: `search_docs failed (${params.package}): ${msg}` }],
					details,
					isError: true,
				};
			}
		},
	});

	// ── list_fonts ─────────────────────────────────────────────────────────
	pi.registerTool({
		name: "list_fonts",
		label: "List Typst Fonts",
		description:
			"Enumerate fonts the local typst binary can see. Use BEFORE writing `#set text(font: \"X\")` — typst silently substitutes unknown fonts.",
		promptSnippet: "list_fonts — enumerate fonts visible to typst (call before #set text(font: ...))",
		parameters: Type.Object({
			filter: Type.Optional(Type.String({ description: "Case-insensitive substring filter on font family name." })),
		}),
		execute: async (_id, params, signal) => {
			type FontsDetails = { ok: boolean; count?: number; error?: string };
			try {
				const { stdout } = await exec("typst", ["fonts"], { signal, cwd, maxBuffer: 4 * 1024 * 1024 });
				const lines = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
				const filtered = params.filter
					? lines.filter((l) => l.toLowerCase().includes(params.filter!.toLowerCase()))
					: lines;
				const text = filtered.length
					? filtered.join("\n")
					: `No fonts ${params.filter ? `matching "${params.filter}" ` : ""}found.`;
				const details: FontsDetails = { ok: true, count: filtered.length };
				return {
					content: [{ type: "text" as const, text: `Found ${filtered.length} fonts.\n${text}` }],
					details,
				};
			} catch (err: unknown) {
				const e = err as { stderr?: string; message?: string };
				const msg = (e.stderr || e.message || String(err)).trim();
				const details: FontsDetails = { ok: false, error: msg };
				return {
					content: [{ type: "text" as const, text: `list_fonts failed: ${msg}` }],
					details,
					isError: true,
				};
			}
		},
	});

	// ── web_search ─────────────────────────────────────────────────────────
	pi.registerTool({
		name: "web_search",
		label: "Web Search (Google grounded)",
		description: [
			"Grounded Google Search via Gemini's first-party `googleSearch` tool.",
			"Use when search_docs can't help: uncovered Typst packages (cmarker, polylux, showybox, …), real-world references for the document's content (research papers, citations, current stats, news, person/place/event details), or compile errors from packages outside the seven indexed ones.",
			"Pass a verbose natural-language query — Gemini fans it out into multiple specific Google searches.",
			"Returns a synthesised markdown answer plus a Sources block of cited URLs. Follow up with `open_url` on a specific URL if you need the full source text to quote precisely.",
		].join("\n"),
		promptSnippet:
			"web_search(query) — grounded Google Search; returns answer + cited URLs (use open_url to read any cited source in full)",
		parameters: Type.Object({
			query: Type.String({
				description: "Verbose natural-language brief. Specific > terse: 'how to use the showybox 2.0.4 package for callout boxes' beats 'showybox'.",
			}),
		}),
		execute: async (_id, params) => {
			// `usage` follows the same contract as search_docs so the host
			// ledger bills the user for the grounded-search LLM call.
			type WebSearchDetails = {
				ok: boolean;
				model?: string;
				queries?: string[];
				sources?: { uri: string; title?: string }[];
				elapsedMs?: number;
				error?: string;
				usage?: {
					input: number;
					output: number;
					cacheRead: number;
					cacheWrite: number;
					model: string;
				};
			};

			const q = params.query.trim();
			if (!q) {
				return {
					content: [{ type: "text" as const, text: "web_search: empty query." }],
					details: { ok: false, error: "empty query" } as WebSearchDetails,
					isError: true,
				};
			}

			const t0 = Date.now();
			let res: Awaited<ReturnType<GoogleGenAI["models"]["generateContent"]>>;
			try {
				const client = getGenai();
				res = await client.models.generateContent({
					model: WEB_SEARCH_MODEL,
					contents: q,
					config: {
						temperature: 0.2,
						maxOutputTokens: 30_000,
						tools: [{ googleSearch: {} }],
					},
				});
			} catch (err: unknown) {
				const msg = err instanceof Error ? err.message : String(err);
				return {
					content: [{ type: "text" as const, text: `web_search: grounded search via ${WEB_SEARCH_MODEL} failed: ${msg}` }],
					details: { ok: false, error: msg, model: WEB_SEARCH_MODEL } as WebSearchDetails,
					isError: true,
				};
			}

			let answer = (res.text ?? "").trim();
			if (!answer) {
				try {
					const parts = res.candidates?.[0]?.content?.parts ?? [];
					answer = parts
						.map((p) => (typeof (p as { text?: string }).text === "string" ? (p as { text: string }).text : ""))
						.filter(Boolean)
						.join("\n")
						.trim();
				} catch {
					// best-effort fallback
				}
			}

			const meta = res.candidates?.[0]?.groundingMetadata;
			const queries = (meta?.webSearchQueries ?? []).map((s: string) => s).filter(Boolean);
			const sources: { uri: string; title?: string }[] = [];
			const seen = new Set<string>();
			for (const chunk of meta?.groundingChunks ?? []) {
				const web = (chunk as { web?: { uri?: string; title?: string; domain?: string } }).web;
				if (!web?.uri || seen.has(web.uri)) continue;
				seen.add(web.uri);
				sources.push({ uri: web.uri, title: web.title || web.domain });
				if (sources.length >= 15) break;
			}

			const elapsed = Date.now() - t0;

			const headerParts: string[] = [];
			headerParts.push(`Web search · model: ${WEB_SEARCH_MODEL} · ${elapsed}ms · ${sources.length} source(s)`);
			if (queries.length) {
				headerParts.push(`Searched: ${queries.slice(0, 6).map((qs) => `\`${qs}\``).join(", ")}`);
			}

			const body = answer || "_(no synthesised answer returned)_";
			const sourcesBlock = sources.length
				? "\n\nSources:\n" +
					sources.map((s) => (s.title ? `- [${s.title}](${s.uri})` : `- ${s.uri}`)).join("\n")
				: "";

			const wsUsage = normalizeGeminiUsage(res.usageMetadata);

			return {
				content: [{ type: "text" as const, text: `${headerParts.join("\n")}\n\n${body}${sourcesBlock}` }],
				details: {
					ok: true,
					model: WEB_SEARCH_MODEL,
					queries,
					sources,
					elapsedMs: elapsed,
					usage: {
						input: wsUsage.input,
						output: wsUsage.output,
						cacheRead: wsUsage.cacheRead,
						cacheWrite: wsUsage.cacheWrite,
						model: WEB_SEARCH_MODEL,
					},
				} as WebSearchDetails,
			};
		},
	});

	// ── open_url ───────────────────────────────────────────────────────────
	pi.registerTool({
		name: "open_url",
		label: "Open URL",
		description: [
			"Fetch one URL and return its readable text content. The agent's way to actually open a link.",
			"Use after `web_search` when you need to quote a cited source precisely, or whenever the user pastes a URL.",
			"HTML pages are stripped to plain markdown-ish text (links preserved as `text (url)`). Plain text / JSON / markdown are returned as-is. Binary content (PDF, images, videos, archives) is rejected — for images use `read` after downloading via `bash` + curl; for PDFs use `bash` + `pdftotext` or `bash` + curl piped to a typst include.",
			`Body is hard-capped at ${OPEN_URL_MAX_CHARS.toLocaleString()} chars; longer pages are truncated with a marker. Network timeout is ${OPEN_URL_TIMEOUT_MS / 1000}s.`,
			"Follows redirects. Sends a normal browser User-Agent. No auth, no cookies — sites that require login will return their public/login page.",
		].join("\n"),
		promptSnippet:
			"open_url(url) — fetch URL, strip HTML, return readable text (use after web_search to read a cited source in full)",
		parameters: Type.Object({
			url: Type.String({
				description: "Absolute http(s) URL. Must include the scheme.",
			}),
		}),
		execute: async (_id, params, signal) => {
			type OpenUrlDetails = {
				ok: boolean;
				url?: string;
				status?: number;
				contentType?: string;
				bytes?: number;
				chars?: number;
				truncated?: boolean;
				elapsedMs?: number;
				error?: string;
			};

			const raw = params.url.trim();
			if (!/^https?:\/\//i.test(raw)) {
				return {
					content: [{ type: "text" as const, text: `open_url: only http(s) URLs are supported. Got: ${raw}` }],
					details: { ok: false, error: "non-http(s) URL", url: raw } as OpenUrlDetails,
					isError: true,
				};
			}

			const t0 = Date.now();
			const ac = new AbortController();
			const timeoutHandle = setTimeout(() => ac.abort(new Error("open_url timeout")), OPEN_URL_TIMEOUT_MS);
			// Surface external cancellation (the agent killing the call) too.
			const onParentAbort = () => ac.abort(signal?.reason);
			signal?.addEventListener?.("abort", onParentAbort);

			let response: Response;
			try {
				response = await fetch(raw, {
					method: "GET",
					redirect: "follow",
					signal: ac.signal,
					headers: {
						"User-Agent":
							"Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 pi-typst-agent",
						Accept: "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.5",
					},
				});
			} catch (err: unknown) {
				clearTimeout(timeoutHandle);
				signal?.removeEventListener?.("abort", onParentAbort);
				const msg = err instanceof Error ? err.message : String(err);
				return {
					content: [{ type: "text" as const, text: `open_url: fetch failed for ${raw}: ${msg}` }],
					details: { ok: false, error: msg, url: raw } as OpenUrlDetails,
					isError: true,
				};
			}

			const ct = (response.headers.get("content-type") ?? "").toLowerCase();
			const status = response.status;
			const finalUrl = response.url || raw;

			const isText =
				ct.startsWith("text/") ||
				ct.includes("application/json") ||
				ct.includes("application/xml") ||
				ct.includes("application/xhtml") ||
				ct.includes("application/javascript") ||
				ct.includes("application/ld+json");

			if (!isText) {
				clearTimeout(timeoutHandle);
				signal?.removeEventListener?.("abort", onParentAbort);
				const len = response.headers.get("content-length");
				return {
					content: [{
						type: "text" as const,
						text:
							`open_url: ${finalUrl} returned binary content (Content-Type: ${ct || "?"}, size: ${len ?? "?"}).\n` +
							`Cannot strip to text. For PDFs use \`bash("curl -sL '${finalUrl}' -o /tmp/x.pdf && pdftotext /tmp/x.pdf -")\`. ` +
							`For images use \`bash("curl -sL '${finalUrl}' -o workspace/img.png")\` then \`read("workspace/img.png")\`.`,
					}],
					details: {
						ok: false,
						url: finalUrl,
						status,
						contentType: ct,
						error: "binary content type",
					} as OpenUrlDetails,
					isError: true,
				};
			}

			let bodyText: string;
			try {
				const buf = await response.arrayBuffer();
				const bytes = buf.byteLength;
				if (bytes > OPEN_URL_MAX_BYTES) {
					bodyText = new TextDecoder("utf-8", { fatal: false }).decode(buf.slice(0, OPEN_URL_MAX_BYTES));
				} else {
					bodyText = new TextDecoder("utf-8", { fatal: false }).decode(buf);
				}
			} catch (err: unknown) {
				clearTimeout(timeoutHandle);
				signal?.removeEventListener?.("abort", onParentAbort);
				const msg = err instanceof Error ? err.message : String(err);
				return {
					content: [{ type: "text" as const, text: `open_url: failed reading body for ${finalUrl}: ${msg}` }],
					details: { ok: false, url: finalUrl, status, contentType: ct, error: msg } as OpenUrlDetails,
					isError: true,
				};
			} finally {
				clearTimeout(timeoutHandle);
				signal?.removeEventListener?.("abort", onParentAbort);
			}

			const isHtml = ct.includes("html") || /<!doctype html|<html[\s>]/i.test(bodyText.slice(0, 2000));
			let processed = isHtml ? htmlToText(bodyText) : bodyText.trim();

			let truncated = false;
			if (processed.length > OPEN_URL_MAX_CHARS) {
				processed =
					processed.slice(0, OPEN_URL_MAX_CHARS).trimEnd() +
					`\n\n_… body truncated to ${OPEN_URL_MAX_CHARS.toLocaleString()} chars; refetch with a more specific query if you need the rest._`;
				truncated = true;
			}

			const elapsed = Date.now() - t0;
			const header =
				`URL: ${finalUrl}\n` +
				`HTTP ${status} · ${ct || "?"} · ${processed.length.toLocaleString()} chars${truncated ? " (truncated)" : ""} · ${elapsed}ms`;

			return {
				content: [{ type: "text" as const, text: `${header}\n\n${processed}` }],
				details: {
					ok: true,
					url: finalUrl,
					status,
					contentType: ct,
					bytes: processed.length,
					chars: processed.length,
					truncated,
					elapsedMs: elapsed,
				} as OpenUrlDetails,
			};
		},
	});

	// ── list_packages ──────────────────────────────────────────────────────
	pi.registerTool({
		name: "list_packages",
		label: "List Indexed Typst Packages",
		description:
			"Returns the pinned versions of the third-party packages the docs corpus covers. Use these import lines verbatim — anything else and you're on your own.",
		promptSnippet: "list_packages — pinned import lines for the seven indexed Typst packages",
		parameters: Type.Object({}),
		execute: async () => {
			const lines = [
				`#import "@preview/cetz:0.5.0"`,
				`#import "@preview/cetz:0.5.0": canvas, draw`,
				`#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge`,
				`#import "@preview/quill:0.7.2": *`,
				`#import "@preview/codly:1.3.0": *`,
				`#import "@preview/circuiteria:0.2.0"`,
				`#import "@preview/touying:0.7.3": *`,
				`#import themes.<metropolis|simple|dewdrop|university|aqua|stargazer>: *`,
			];
			return {
				content: [{ type: "text" as const, text: `Pinned imports (search_docs corpus matches these versions):\n${lines.join("\n")}` }],
				details: { ok: true },
			};
		},
	});
}
