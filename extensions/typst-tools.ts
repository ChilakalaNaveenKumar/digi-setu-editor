/**
 * Typst tools for pi-coding-agent.
 *
 * Compile / render / inspect happens via pi's built-in `bash` tool — no wrapper.
 * The system prompt teaches the recipes (compile, render PNG, then `read` the
 * PNG to look at the actual page).
 *
 * Tools registered here are only the things bash CAN'T do — i.e. side-LLM calls
 * and network access:
 *   - style_guide    → MANDATORY first call for any new design. Calls Flash to
 *                       author workspace/style/style.typ.
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

const ROUTER_MODEL = process.env.PI_TYPST_ROUTER_MODEL ?? "claude-haiku-4-5";
const DESIGN_MODEL = process.env.PI_TYPST_DESIGN_MODEL ?? "gemini-3-flash-preview";

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
- Be dense and concrete. Show the exact import lines and 5-30 line copy-paste examples.
- Cite the doc paths you pulled from at the bottom under "Sources:" (one per line, repo-relative paths like guides/touying/themes/02-metropolis.md).
- If the corpus genuinely doesn't cover the question, say so plainly in one line; don't invent API.
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

	// ── style_guide ────────────────────────────────────────────────────────
	pi.registerTool({
		name: "style_guide",
		label: "Generate Typst Style Guide",
		description: [
			"MANDATORY first action when creating any new Typst document.",
			"Calls a side-LLM (the 'design worker') to author workspace/style/style.typ — a single Typst file defining colors, fonts, sizes, mood, and layout intent for the document(s) you are about to write.",
			"Inputs:",
			"  topic         — what the document is about (audience, purpose, tone). Be specific.",
			"  hints         — optional user preferences. Pass the user's words verbatim if they expressed any (about look, mood, references, palette, anything). Leave empty if they didn't.",
			"  available_fonts — optional. If you've already called list_fonts, pass the (filtered) list so the worker can only pick installed fonts. If omitted, the tool fetches them itself.",
			"After this tool succeeds, every .typ you write must start with `#import \"style/style.typ\": *` and use the variables defined there (primary, secondary, body-font, mood, hero-style, etc.) instead of hardcoded values.",
			"Re-call when the user asks to redesign — pass their request verbatim through `hints`. Overwrites style.typ.",
		].join("\n"),
		promptSnippet:
			"style_guide(topic, hints?) — MANDATORY first call before writing any new document; produces workspace/style/style.typ with colors/fonts/mood that all .typ files must import",
		parameters: Type.Object({
			topic: Type.String({
				description: "What the document is about. Include audience, purpose, tone (e.g. 'quarterly review deck for fintech executive board').",
			}),
			hints: Type.Optional(
				Type.String({ description: "User preferences for mood/colors/style. Pass verbatim if the user said any." }),
			),
			available_fonts: Type.Optional(
				Type.Array(Type.String(), {
					description: "Optional list of installed font family names. If omitted, the tool runs `typst fonts` itself.",
				}),
			),
			model: Type.Optional(
				Type.String({
					description: `Optional model override. Defaults to PI_TYPST_DESIGN_MODEL env var (currently ${DESIGN_MODEL}). Pass "gemini-3.1-pro-preview" if Flash output keeps coming back generic.`,
				}),
			),
		}),
		execute: async (_id, params, signal) => {
			type StyleDetails = {
				ok: boolean;
				path?: string;
				bytes?: number;
				model?: string;
				elapsedMs?: number;
				error?: string;
			};

			const styleDir = path.join(cwd, "workspace", "style");
			const stylePath = path.join(styleDir, "style.typ");
			const t0 = Date.now();

			let fonts = params.available_fonts;
			if (!fonts || fonts.length === 0) {
				try {
					const { stdout } = await exec("typst", ["fonts"], { signal, cwd, maxBuffer: 4 * 1024 * 1024 });
					fonts = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
				} catch (err: unknown) {
					const msg = err instanceof Error ? err.message : String(err);
					return {
						content: [{ type: "text" as const, text: `style_guide: failed to enumerate fonts via 'typst fonts': ${msg}` }],
						details: { ok: false, error: `font enumeration failed: ${msg}` } as StyleDetails,
						isError: true,
					};
				}
			}

			const fontList = fonts.slice(0, 200).join(", ");
			const chosenModel = params.model ?? DESIGN_MODEL;

			const systemInstruction = [
				"You are a senior art director with a strong, opinionated visual eye. You design documents that look like they belong in a design portfolio.",
				"Your one and only output is the raw contents of a Typst file (style.typ). No prose, no markdown fences, no explanation outside the file's own comment headers.",
				"You decide the entire visual identity. The variable names below are a fixed contract (the writing agent depends on them); the VALUES are entirely yours.",
				"Take a real position. A safe, generic, 'professional' design is a worse outcome than a strong design that someone might disagree with.",
			].join("\n");

			const prompt = `# Brief
TOPIC: ${params.topic.trim()}
USER HINTS (verbatim): ${params.hints?.trim() || "(none — you have full creative freedom)"}

# Available fonts (you may ONLY use these family names)
${fontList}

# Step 1 — Brainstorm (in your head, do NOT output)
Mentally sketch three substantially different visual directions for this brief. They should differ on at least TWO of:
  - brightness (light / dark / mid-tone)
  - color temperature (warm / cool / neutral / mixed)
  - saturation (muted / vivid)
  - typographic mood (serif / sans / mixed / display)
  - density (airy / compact / journal-dense)

Do not list out generic moodboard tropes — invent directions that come from THIS topic and audience specifically. Pick the ONE that fits best and commit to it. If you find yourself defaulting to whatever palette feels "safe" for the topic, pick a different one.

# Step 2 — Author the Typst file (this IS your output)

The file shape below is the contract with the writing agent — variable names are fixed, every VALUE marked <…> is yours. Use any Typst color form: \`rgb("#…")\`, \`rgb(r, g, b)\`, \`oklch(...)\`, named colors (any of the std-lib names), or \`color.lighten()/darken()\`. Use any installed font.

\`\`\`
// AUTO-GENERATED by style_guide tool. Re-run style_guide to change.
//
// MOOD:        <one short kebab-case label that captures THIS design. Invent it. Do not reuse a label you've seen before.>
// AUDIENCE:    <one short line>
// REASONING:   <3-5 lines explaining (a) the direction you picked, (b) why it suits THIS topic and audience specifically, (c) at least one direction you deliberately rejected and why>
//
// HERO_STYLE:    <one short kebab-case label describing the title-area treatment you intend. Invent it.>
// SECTION_STYLE: <one short kebab-case label for how body sections should look. Invent it.>
// CHART_STYLE:   <one short kebab-case label for the chart aesthetic. Invent it.>

// ── Colors — variable names are fixed, values are yours. ──
#let primary    = <COLOR_PRIMARY>     // the most prominent color in the document (can be background, brand color, ink — your call)
#let secondary  = <COLOR_SECONDARY>   // a supporting color that complements primary
#let accent     = <COLOR_ACCENT>      // the one color that draws the eye — used sparingly for emphasis, links, key numbers, dataviz callouts
#let background = <COLOR_BACKGROUND>  // page fill
#let surface    = <COLOR_SURFACE>     // card / panel / table-header fill (offset from background for depth)
#let foreground = <COLOR_FOREGROUND>  // body text — must have strong contrast against background
#let text-muted = <COLOR_TEXT_MUTED>  // captions, axis labels — readable but visually de-emphasized

// ── Typography (font family strings — pick from the installed list above) ──
#let body-font     = "<FONT_BODY>"
#let heading-font  = "<FONT_HEADING>"
#let mono-font     = "<FONT_MONO>"

// ── Sizes — pick what suits your fonts and the topic. ──
#let body-size       = <SIZE_BODY>      // any Typst length, e.g. 9pt, 10.5pt, 12pt
#let heading-weight  = <WEIGHT_HEADING> // 100..900 in steps of 100
#let line-height     = <LINE_HEIGHT>    // a number; typically between 1.2 and 1.8

// ── Style intent (string copies of the comments above; read by the writing agent) ──
#let mood          = "<SAME AS MOOD ABOVE>"
#let hero-style    = "<SAME AS HERO_STYLE ABOVE>"
#let section-style = "<SAME AS SECTION_STYLE ABOVE>"
#let chart-style   = "<SAME AS CHART_STYLE ABOVE>"

// ── Chart palette: an ARRAY of colors for CeTZ / Fletcher data series. ──
// Pick however many entries this design wants — 3 to 10 is the sensible range.
// 3 if the document mostly does pairwise comparisons. More if it has dashboards
// or multi-series charts. Each color must be visually distinct from its neighbours
// AND readable over background.
#let chart-palette = (<DATA_COLOR_1>, <DATA_COLOR_2>, <DATA_COLOR_N…>)
\`\`\`

# Rules
- Output ONLY the Typst source. No prose before or after. No \`\`\`typst fences around it.
- Every \`<…>\` slot must be filled with a real value. No placeholders left.
- The four MOOD/HERO/SECTION/CHART string values must match their comment-header counterparts exactly.
- Fonts must come from the installed list. If your ideal font isn't there, pick the closest installed family.
- foreground must be readable on background. accent must be readable on both background and surface.
- chart-palette is a Typst array \`(c1, c2, ...)\` of at least 3 colors; no maximum.
- Take a real position. Generic "safe" designs are a worse outcome than a strong design someone might disagree with.`;

			let raw: string;
			try {
				const client = getGenai();
				const res = await client.models.generateContent({
					model: chosenModel,
					contents: prompt,
					config: {
						temperature: 0.95,
						maxOutputTokens: 4_000,
						systemInstruction,
					},
				});
				raw = (res.text ?? "").trim();
			} catch (err: unknown) {
				const msg = err instanceof Error ? err.message : String(err);
				return {
					content: [{ type: "text" as const, text: `style_guide: design model ${chosenModel} failed: ${msg}` }],
					details: { ok: false, error: msg, model: chosenModel } as StyleDetails,
					isError: true,
				};
			}

			let body = raw.replace(/^```(?:typst)?\s*\n/, "").replace(/\n```\s*$/, "").trim();
			if (!body) {
				return {
					content: [{ type: "text" as const, text: `style_guide: design model returned empty content` }],
					details: { ok: false, error: "empty response", model: chosenModel } as StyleDetails,
					isError: true,
				};
			}
			if (!body.endsWith("\n")) body += "\n";

			await fs.mkdir(styleDir, { recursive: true });
			await fs.writeFile(stylePath, body, "utf8");

			const testTypPath = path.join(styleDir, ".style-test.typ");
			const testContent =
				`#import "style.typ": primary, secondary, body-font, heading-font, mood, hero-style\n` +
				`#set page(width: 100pt, height: 50pt)\n` +
				`#set text(font: body-font)\n` +
				`#text(fill: primary)[ok]\n`;
			await fs.writeFile(testTypPath, testContent, "utf8");

			let compileError: string | null = null;
			try {
				await exec("typst", ["compile", "--root", cwd, testTypPath, "/dev/null"], {
					signal,
					cwd,
					maxBuffer: 2 * 1024 * 1024,
				});
			} catch (err: unknown) {
				const e = err as { stderr?: string; stdout?: string; message?: string };
				compileError = (e.stderr || e.stdout || e.message || String(err)).trim();
			} finally {
				await fs.unlink(testTypPath).catch(() => {});
			}

			const elapsed = Date.now() - t0;

			if (compileError) {
				const compact = compileError.split("\n").slice(0, 30).join("\n");
				return {
					content: [
						{
							type: "text" as const,
							text:
								`style_guide: wrote workspace/style/style.typ (${body.length} bytes) BUT it does not compile:\n${compact}\n\n` +
								`The file was kept on disk so you can inspect it. Either edit it, or call style_guide again with clearer hints.`,
						},
					],
					details: {
						ok: false,
						path: "workspace/style/style.typ",
						bytes: body.length,
						model: chosenModel,
						elapsedMs: elapsed,
						error: `compile failed: ${compact}`,
					} as StyleDetails,
					isError: true,
				};
			}

			const moodMatch = body.match(/^\/\/\s*MOOD:\s*(.+)$/m);
			const heroMatch = body.match(/^\/\/\s*HERO_STYLE:\s*(.+)$/m);
			const summary = `Wrote workspace/style/style.typ (${body.length} bytes, ${elapsed}ms, model: ${chosenModel}). Mood: ${moodMatch?.[1]?.trim() ?? "?"}, hero: ${heroMatch?.[1]?.trim() ?? "?"}. Compile-tested OK. All .typ files you write next must \`#import "style/style.typ": *\`.`;

			return {
				content: [{ type: "text" as const, text: summary }],
				details: { ok: true, path: "workspace/style/style.typ", bytes: body.length, model: chosenModel, elapsedMs: elapsed } as StyleDetails,
			};
		},
	});

	// ── search_docs ────────────────────────────────────────────────────────
	pi.registerTool({
		name: "search_docs",
		label: "Search Typst Docs",
		description: [
			"Look up something in the indexed Typst documentation corpus.",
			"Pick the smallest relevant `package` so the responder LLM only sees the corpus that matters:",
			"  typst        — core Typst language and stdlib (no third-party packages)",
			"  cetz         — vector drawing primitives (canvas, draw, line, etc.)",
			"  fletcher     — diagrams built on CeTZ (diagram, node, edge)",
			"  quill        — quantum circuit diagrams",
			"  codly        — code-block styling",
			"  circuiteria  — block-level circuit diagrams",
			"  touying      — slide / presentation framework with themes",
			"Pack the `query` with real symbol names, parameter names, and any compiler error you've seen.",
			"Returns the responder's freeform markdown answer plus the doc paths it cited.",
		].join("\n"),
		promptSnippet:
			"search_docs(query, package) — Flash-Lite responder loaded with full corpus for one package; returns dense answer + cited paths",
		parameters: Type.Object({
			query: Type.String({ description: "Concrete brief. Include symbol names, error text, what you're trying to build." }),
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
			type SearchDetails = {
				ok: boolean;
				package?: string;
				cited?: string[];
				elapsedMs?: number;
				fallback?: string;
				error?: string;
			};
			if (!VALID_CORPORA.has(params.package)) {
				const details: SearchDetails = { ok: false, error: `invalid package ${params.package}` };
				return {
					content: [{ type: "text" as const, text: `Invalid package: ${params.package}` }],
					details,
					isError: true,
				};
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
					inputTok = res.usage?.input_tokens ?? 0;
					outputTok = res.usage?.output_tokens ?? 0;
					// biome-ignore lint/suspicious/noExplicitAny: cache fields not on typed Usage yet
					const u = res.usage as any;
					cacheRead = u?.cache_read_input_tokens ?? 0;
					cacheWrite = u?.cache_creation_input_tokens ?? 0;
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
					inputTok = res.usageMetadata?.promptTokenCount ?? 0;
					outputTok = res.usageMetadata?.candidatesTokenCount ?? 0;
					cacheRead = res.usageMetadata?.cachedContentTokenCount ?? 0;
				}

				if (!raw) {
					const details: SearchDetails = { ok: false, fallback: "empty response" };
					return {
						content: [{ type: "text" as const, text: `Responder returned empty for ${params.package}` }],
						details,
						isError: true,
					};
				}
				const { answer, cited } = splitAnswerAndSources(raw);
				const elapsed = Date.now() - t0;
				const tokInfo =
					cacheRead || cacheWrite
						? `in=${inputTok} (cached_read=${cacheRead}${cacheWrite ? ` cached_write=${cacheWrite}` : ""}) out=${outputTok}`
						: `in=${inputTok} out=${outputTok}`;
				const header = `Package: ${params.package} · model: ${ROUTER_MODEL} · ${elapsed}ms · ${cited.length} sources · ${tokInfo}`;
				const sources = cited.length ? `\n\nSources:\n${cited.map((p) => `- ${p}`).join("\n")}` : "";
				const details: SearchDetails = { ok: true, package: params.package, cited, elapsedMs: elapsed };
				return {
					content: [{ type: "text" as const, text: `${header}\n\n${answer}${sources}` }],
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
			type WebSearchDetails = {
				ok: boolean;
				model?: string;
				queries?: string[];
				sources?: { uri: string; title?: string }[];
				elapsedMs?: number;
				error?: string;
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

			return {
				content: [{ type: "text" as const, text: `${headerParts.join("\n")}\n\n${body}${sourcesBlock}` }],
				details: { ok: true, model: WEB_SEARCH_MODEL, queries, sources, elapsedMs: elapsed } as WebSearchDetails,
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
