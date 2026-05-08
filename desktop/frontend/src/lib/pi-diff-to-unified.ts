/**
 * Convert pi's custom diff string into a standard unified diff so we can
 * feed it to diff2html (or any other unified-diff renderer).
 *
 * pi format (from coding-agent's edit tool, captured live 2026-05-05):
 *
 *     <symbol><pad-line-number> <content>
 *
 * Where symbol is " " (context), "+" (add), or "-" (remove). The line
 * number is the OLD line number for "-" / context, and NEW line number
 * for "+". Single-hunk changes have no separator; non-adjacent changes
 * appear as one continuous list (we infer hunk boundaries by looking
 * at line-number gaps).
 *
 * Standard unified diff:
 *
 *     --- a/<path>
 *     +++ b/<path>
 *     @@ -<oldStart>,<oldCount> +<newStart>,<newCount> @@
 *     <space|+|->content
 *     ...
 *
 * For BRAND-NEW files (write tool), we synthesize "compared against /dev/null"
 * which renders as all-green addition lines.
 */

import { parseDiff, synthAddDiff, type DiffLine } from "./diff-parse";

interface Hunk {
  oldStart: number;
  oldCount: number;
  newStart: number;
  newCount: number;
  bodyLines: string[];
}

function buildHunkFromLines(lines: DiffLine[]): Hunk | null {
  if (!lines.length) return null;
  let oldStart = -1;
  let newStart = -1;
  let oldCount = 0;
  let newCount = 0;
  const body: string[] = [];

  for (const ln of lines) {
    switch (ln.kind) {
      case "context":
        if (oldStart === -1) oldStart = ln.lineno;
        if (newStart === -1) newStart = ln.lineno;
        oldCount++;
        newCount++;
        body.push(" " + ln.content);
        break;
      case "remove":
        if (oldStart === -1) oldStart = ln.lineno;
        // Approximate: when a hunk starts with a remove (no context lead),
        // newStart is best-effort the same line number (it'll be displaced
        // by subsequent additions).
        if (newStart === -1) newStart = Math.max(1, ln.lineno);
        oldCount++;
        body.push("-" + ln.content);
        break;
      case "add":
        if (newStart === -1) newStart = ln.lineno;
        if (oldStart === -1) oldStart = Math.max(1, ln.lineno);
        newCount++;
        body.push("+" + ln.content);
        break;
    }
  }

  return { oldStart, oldCount, newStart, newCount, bodyLines: body };
}

/** Render a standard unified diff string. Path is used for the `+++ b/<path>` header. */
function renderUnified(path: string, hunks: Hunk[], isNewFile: boolean): string {
  if (!hunks.length) return "";
  const oldHeader = isNewFile ? "--- /dev/null" : `--- a/${path}`;
  const newHeader = `+++ b/${path}`;
  const body = hunks
    .map((h) => {
      const header = `@@ -${h.oldStart},${h.oldCount} +${h.newStart},${h.newCount} @@`;
      return [header, ...h.bodyLines].join("\n");
    })
    .join("\n");
  return [oldHeader, newHeader, body].join("\n") + "\n";
}

/**
 * Convert pi's edit-tool diff string into unified diff.
 * Returns "" if input is empty/unparseable so callers can fall back to a
 * "no visible changes" placeholder.
 */
export function piDiffToUnified(piDiff: string | undefined | null, path: string): string {
  if (!piDiff) return "";
  const parsed = parseDiff(piDiff);
  if (!parsed.lines.length) return "";

  const hunks: Hunk[] = [];
  for (const hunkLines of parsed.hunks) {
    const h = buildHunkFromLines(hunkLines);
    if (h) hunks.push(h);
  }
  // Default to single hunk if parser didn't split.
  if (!hunks.length) {
    const h = buildHunkFromLines(parsed.lines);
    if (h) hunks.push(h);
  }
  return renderUnified(path, hunks, /*isNewFile*/ false);
}

/**
 * Build a unified diff for a brand-new file write — every line is an
 * addition compared against /dev/null. Renders as solid green in
 * diff2html, mirroring how Cursor/GitHub display new files.
 */
export function writeContentToUnified(content: string, path: string): string {
  const synth = synthAddDiff(content);
  if (!synth.lines.length) return "";
  const body = synth.lines.map((l) => "+" + l.content);
  const header = `@@ -0,0 +1,${synth.added} @@`;
  return [
    "--- /dev/null",
    `+++ b/${path}`,
    header,
    ...body,
    "",
  ].join("\n");
}
