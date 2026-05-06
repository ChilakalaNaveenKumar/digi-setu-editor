/**
 * Single shared markdown-it instance with sane defaults that approximate
 * pi-tui's MarkdownTheme (links, code, lists). Heavy lifting (highlighting,
 * KaTeX, etc.) is intentionally out — Step 1 stays minimal.
 */
import MarkdownIt from "markdown-it";

export const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
});

export function renderMarkdown(src: string): string {
  return md.render(src);
}
