/**
 * Singleton Shiki highlighter.
 *
 * Lazy-initializes on first call (so the initial app bundle stays small),
 * loads a fixed set of languages we expect in this workspace, and exposes
 * a synchronous `highlightLines()` once ready.
 *
 * Why these languages: typst is the primary use case; the rest cover
 * everything pi might write while bootstrapping a project (build scripts,
 * configs, READMEs). Add more by appending to LANGS — Shiki bundles them
 * on demand from `shiki/langs/*` so the cost is per-language.
 *
 * Why one theme: keeping the bundle lean. To swap themes later, expose a
 * setter that loads a new theme name via `highlighter.loadTheme(name)`.
 *
 * Streaming considerations: callers should throttle re-highlight calls
 * during streaming (see EditorPane), since shiki re-tokenizes the whole
 * source each time. For files <50KB this is sub-millisecond on modern
 * machines and not worth incrementalizing. For larger files, consider
 * a virtualized line view.
 */

import type { BundledLanguage, Highlighter } from "shiki";
import { getSingletonHighlighter } from "shiki";

const LANGS: BundledLanguage[] = [
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
];

/** Default theme. Pairs well with our token-driven Notion teal surfaces. */
const THEME = "github-dark-default";

let highlighterPromise: Promise<Highlighter> | null = null;

export function getHighlighter(): Promise<Highlighter> {
  if (!highlighterPromise) {
    highlighterPromise = getSingletonHighlighter({
      themes: [THEME],
      langs: LANGS,
    });
  }
  return highlighterPromise;
}

/**
 * Map a file extension to a Shiki language id. Returns null for unsupported
 * extensions (caller should fall back to plain monospace). Centralizes
 * extension → language so EditorPane doesn't carry that knowledge.
 */
export function langForPath(path: string | undefined): BundledLanguage | null {
  if (!path) return null;
  const ext = path.includes(".") ? path.split(".").pop()!.toLowerCase() : "";
  switch (ext) {
    case "typ":
      return "typst";
    case "md":
    case "markdown":
      return "markdown";
    case "json":
    case "jsonc":
      return "json";
    case "yml":
    case "yaml":
      return "yaml";
    case "toml":
      return "toml";
    case "py":
      return "python";
    case "js":
    case "mjs":
    case "cjs":
      return "javascript";
    case "ts":
    case "mts":
    case "cts":
      return "typescript";
    case "vue":
      return "vue";
    case "html":
    case "htm":
      return "html";
    case "css":
      return "css";
    case "sh":
    case "bash":
    case "zsh":
      return "bash";
    case "dockerfile":
      return "dockerfile";
    case "xml":
    case "svg":
      return "xml";
    default:
      return null;
  }
}

/**
 * Tokenize source into per-line spans of styled HTML. Returns a list of
 * line strings (HTML for the line content only — no <pre>/<code> wrapper)
 * so callers can render each line in their own gutter+content row.
 *
 * If the language isn't loaded (e.g. unknown ext), returns plaintext lines
 * with HTML-escaped content. Errors are swallowed and turned into
 * plaintext fallback so a bad highlight never breaks the editor.
 */
export async function highlightLines(
  source: string,
  lang: BundledLanguage | null
): Promise<string[]> {
  if (!source) return [];
  if (!lang) return splitEscaped(source);

  try {
    const hl = await getHighlighter();
    // codeToTokens preserves theme-driven inline styles per token.
    const result = hl.codeToTokens(source, { lang, theme: THEME });
    return result.tokens.map((line) =>
      line
        .map(
          (tok) =>
            `<span style="color:${tok.color ?? "inherit"}${
              tok.fontStyle === 1
                ? ";font-style:italic"
                : tok.fontStyle === 2
                ? ";font-weight:600"
                : ""
            }">${escapeHtml(tok.content)}</span>`
        )
        .join("")
    );
  } catch (exc) {
    console.warn("[highlighter] failed for", lang, exc);
    return splitEscaped(source);
  }
}

function splitEscaped(source: string): string[] {
  return source.split("\n").map(escapeHtml);
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
