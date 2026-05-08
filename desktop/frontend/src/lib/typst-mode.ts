/**
 * Tiny Typst tokenizer for CodeMirror's StreamLanguage. Not a full Lezer
 * grammar — just enough to colour the constructs people actually look at:
 *
 *   • Comments (// and /* * /)
 *   • Hash keywords:  #let / #set / #show / #import / #include / #if /
 *                     #else / #for / #while / #return / #function / #true /
 *                     #false / #none / #auto
 *   • Hash variables / function calls (#foo, #foo())
 *   • Strings ("...")
 *   • Numbers + units (10pt, 1.5em, 50%, 100cm, etc.)
 *   • Headings (= one, == two, === three at line start)
 *   • Markup punctuation (* _ ` $ \ )
 *
 * That covers ~95% of what shows up in a typst document and matches the
 * One Dark theme tokens we use elsewhere.
 */

import type { StreamParser } from "@codemirror/language";

interface TypstState {
  /** True when we're inside a /* ... * / block comment (across lines). */
  inBlockComment: boolean;
}

const KEYWORDS = new Set([
  "let",
  "set",
  "show",
  "import",
  "include",
  "if",
  "else",
  "for",
  "while",
  "return",
  "function",
  "true",
  "false",
  "none",
  "auto",
  "in",
  "as",
  "context",
  "break",
  "continue",
]);

export const typstMode: StreamParser<TypstState> = {
  startState: () => ({ inBlockComment: false }),
  token(stream, state) {
    // ── inside multi-line block comment ───────────────────────────────
    if (state.inBlockComment) {
      while (!stream.eol()) {
        if (stream.match("*/")) {
          state.inBlockComment = false;
          return "comment";
        }
        stream.next();
      }
      return "comment";
    }

    if (stream.eatSpace()) return null;

    // line / block comments
    if (stream.match("//")) {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.match("/*")) {
      state.inBlockComment = true;
      // Try to close on the same line.
      while (!stream.eol()) {
        if (stream.match("*/")) {
          state.inBlockComment = false;
          return "comment";
        }
        stream.next();
      }
      return "comment";
    }

    // strings
    if (stream.peek() === '"') {
      stream.next();
      while (!stream.eol()) {
        const ch = stream.next();
        if (ch === "\\") {
          stream.next();
          continue;
        }
        if (ch === '"') return "string";
      }
      return "string";
    }

    // hash keywords / variables / function calls
    if (stream.peek() === "#") {
      stream.next();
      // #let, #set, etc. — read identifier, check keyword set.
      const m = stream.match(/^[a-zA-Z_][a-zA-Z0-9_-]*/);
      if (m && Array.isArray(m)) {
        const word = m[0];
        if (KEYWORDS.has(word)) return "keyword";
        // function call?
        if (stream.peek() === "(") return "variableName.function";
        return "variableName.special";
      }
      return "punctuation";
    }

    // numbers + units
    if (/[0-9]/.test(stream.peek() ?? "")) {
      stream.match(/^[0-9]+(?:\.[0-9]+)?(?:pt|cm|mm|em|in|fr|deg|rad|%|s|ms)?/);
      return "number";
    }

    // headings (line start "= ", "== ", "=== ")
    if (stream.sol() && stream.match(/^={1,6}\s+/)) {
      stream.skipToEnd();
      return "heading";
    }

    // markup punctuation single chars
    const ch = stream.next();
    if (!ch) return null;
    if ("*_`$\\".includes(ch)) return "operator";
    if ("{}()[]".includes(ch)) return "bracket";
    if (",;:".includes(ch)) return "punctuation";

    // identifiers (function names, dot access)
    if (/[a-zA-Z_]/.test(ch)) {
      stream.match(/^[a-zA-Z0-9_-]*/);
      return "variableName";
    }

    return null;
  },
  languageData: {
    commentTokens: { line: "//", block: { open: "/*", close: "*/" } },
  },
};
