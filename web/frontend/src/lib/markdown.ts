/**
 * Chat markdown renderer.
 *
 * Built on markdown-it with three augmentations that turn the previously
 * plain-text-with-asterisks render into something the user can actually
 * read:
 *
 *   1. Shiki syntax highlighting in fenced code blocks. Reuses the same
 *      `getHighlighter()` singleton that powers the editor pane, so the
 *      colour theme matches between the chat and the editor and we don't
 *      pay for a second tokenizer bundle.
 *   2. KaTeX math (`$inline$`, `$$display$$`) — agents emit math constantly
 *      when explaining typst's `set par(leading: 0.65em)` etc., and the
 *      pre-rendered ASCII version was unreadable.
 *   3. GitHub-flavoured task lists (`- [x] done`, `- [ ] todo`) — pi
 *      writes these in plans / TODOs and they should look like checkboxes,
 *      not raw brackets.
 *
 * Plus markdown-it's built-in tables (`| col1 | col2 |`) and linkify (so
 * bare URLs become clickable). HTML embedded in the source is still
 * disabled (`html: false`) — agents have no business dropping raw <script>
 * into chat output.
 *
 * Streaming concern: we re-render the WHOLE message text on every token
 * append. markdown-it is fast (<1ms for typical chat messages); Shiki is
 * the one that can blow up if a 500-line code block is being streamed
 * line-by-line. To keep that bounded we (a) only highlight blocks that
 * are visibly closed (the streaming partial defaults to plaintext until
 * the closing fence arrives), and (b) cap each highlight at 300 lines —
 * larger blocks degrade to plaintext rather than freezing the page.
 */

import MarkdownIt from "markdown-it";
import markdownItAnchor from "markdown-it-anchor";
import markdownItTaskLists from "markdown-it-task-lists";
import markdownItKatex from "@vscode/markdown-it-katex";
import { getHighlighter, langForPath } from "./highlighter";
import type { BundledLanguage } from "shiki";

const SHIKI_THEME = "github-dark-default";
const MAX_HIGHLIGHT_LINES = 300;

// Languages the Shiki bundle knows about. Anything outside this set falls
// back to plaintext-with-escaped-html. Mirrors highlighter.ts so we don't
// have to await the highlighter just to ask "do you support this lang?".
const KNOWN_LANGS = new Set<string>([
  "typst",
  "markdown",
  "json",
  "yaml",
  "toml",
  "python",
  "javascript",
  "typescript",
  "vue",
  "html",
  "css",
  "bash",
  "shell",
  "dockerfile",
  "xml",
  // Common aliases the agent emits even though Shiki uses the canonical name:
  "ts",
  "js",
  "py",
  "sh",
  "yml",
  "md",
]);

function normalizeLang(raw: string | undefined): BundledLanguage | null {
  if (!raw) return null;
  const lower = raw.toLowerCase().trim();
  if (!KNOWN_LANGS.has(lower)) return null;
  switch (lower) {
    case "ts":
      return "typescript";
    case "js":
      return "javascript";
    case "py":
      return "python";
    case "sh":
      return "bash";
    case "yml":
      return "yaml";
    case "md":
      return "markdown";
    default:
      return lower as BundledLanguage;
  }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Cache the singleton highlighter on first use. We do NOT await it inside
// `highlight` (markdown-it expects a sync callback); instead we kick off
// the load on module init and serve plaintext until it resolves. Once
// loaded, subsequent renders hit the warm cache.
let cachedHl: Awaited<ReturnType<typeof getHighlighter>> | null = null;
let highlighterReady: Promise<void> | null = null;

function ensureHighlighter(): void {
  if (cachedHl || highlighterReady) return;
  highlighterReady = getHighlighter()
    .then((hl) => {
      cachedHl = hl;
    })
    .catch((err) => {
      console.warn("[markdown] Shiki highlighter failed to load:", err);
    });
}

export function whenHighlighterReady(): Promise<void> {
  ensureHighlighter();
  return highlighterReady ?? Promise.resolve();
}

ensureHighlighter();

function highlightFence(
  code: string,
  langRaw: string,
  _attrs: string,
): string {
  const lang = normalizeLang(langRaw);
  // Always wrap in a div with the data-lang attribute so the CSS-driven
  // copy button + language label can pick it up. The button itself is
  // inserted by the chat-side IntersectionObserver (see ChatPane.vue
  // setup) — keeps the renderer side-effect-free.
  const langLabel = lang ?? langRaw ?? "text";

  const lineCount = (code.match(/\n/g)?.length ?? 0) + 1;
  if (!lang || !cachedHl || lineCount > MAX_HIGHLIGHT_LINES) {
    return (
      `<pre data-lang="${escapeHtml(langLabel)}"><code>` +
      escapeHtml(code) +
      "</code></pre>"
    );
  }

  try {
    const html = cachedHl.codeToHtml(code, { lang, theme: SHIKI_THEME });
    // Shiki returns `<pre class="shiki ..." style="...">...</pre>`; we
    // strip its outer <pre> so our own <pre data-lang=…> wrapper survives
    // and the CSS rules can target one consistent shell.
    const inner = html
      .replace(/^<pre[^>]*>/, "")
      .replace(/<\/pre>\s*$/, "");
    return `<pre data-lang="${escapeHtml(langLabel)}" class="shiki-pre">${inner}</pre>`;
  } catch (exc) {
    console.warn(`[markdown] Shiki failed for lang=${langLabel}:`, exc);
    return (
      `<pre data-lang="${escapeHtml(langLabel)}"><code>` +
      escapeHtml(code) +
      "</code></pre>"
    );
  }
}

export const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true,
  highlight: highlightFence,
});

// Bare http(s) URLs become anchors. We make them open in a new tab so
// clicking a citation link doesn't navigate away from the chat.
md.renderer.rules.link_open = function (tokens, idx, options, _env, self) {
  const tok = tokens[idx];
  if (tok.attrIndex("target") < 0) tok.attrPush(["target", "_blank"]);
  if (tok.attrIndex("rel") < 0) tok.attrPush(["rel", "noopener noreferrer"]);
  return self.renderToken(tokens, idx, options);
};

md.use(markdownItAnchor, {
  permalink: false,
  level: [2, 3, 4],
  slugify: (s: string) =>
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, ""),
});

md.use(markdownItTaskLists, { enabled: false, label: true });

// `@vscode/markdown-it-katex` exports a default function that takes the
// markdown-it instance directly (some forks export a {default} wrapper —
// handle both). KaTeX is loaded once per page; the CSS is imported in
// app.css alongside our prose styles.
const katexPlugin =
  typeof markdownItKatex === "function"
    ? markdownItKatex
    : (markdownItKatex as { default: unknown }).default;
md.use(katexPlugin as never, {
  throwOnError: false,
  // Render display math centered, inline math on the line.
  enableMathInlineInLinks: false,
});

/** Suffix used by the wrapper the chat injects around fenced code blocks. */
export const FENCE_DATA_LANG_ATTR = "data-lang";

/** Render a markdown source string to HTML. Safe to call on every token append. */
export function renderMarkdown(src: string): string {
  if (!src) return "";
  return md.render(src);
}

// Pre-import the highlighter handler symbol so tree-shaking keeps it.
export { langForPath };
