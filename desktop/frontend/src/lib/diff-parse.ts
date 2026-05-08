/**
 * Parse pi's `result.details.diff` string into structured lines.
 *
 * Format produced by pi-coding-agent's edit tool (verified by capturing a
 * real edit run; see web/backend dump on 2026-05-05):
 *
 *   <symbol><pad-line-number> <content>
 *
 * - symbol is " " (context), "+" (addition), or "-" (removal)
 * - pad-line-number is right-aligned, variable width depending on file size
 * - the rest of the line, after the FIRST space following the number, is
 *   the original source content (verbatim, with no markup)
 *
 * Example:
 *      1 import math
 *      2
 *     -3 def circle_area(r):
 *     -4     return math.pi * r * r
 *     +3 def compute_area(r):
 *     +4     return math.pi * r ** 2
 *      5
 *
 * Pure / no Vue. Returns empty array on missing/malformed input — callers
 * decide whether to render a fallback.
 */

export type DiffLineKind = "context" | "add" | "remove";

export interface DiffLine {
  kind: DiffLineKind;
  /** 1-based line number from the diff header. May be the OLD or NEW file's
   *  line number depending on `kind`. */
  lineno: number;
  /** Source line content (no markup, no leading symbol). May contain leading
   *  whitespace which IS significant for code rendering. */
  content: string;
}

export interface ParsedDiff {
  lines: DiffLine[];
  added: number;
  removed: number;
  /** Hunks delimited by 1+ blank pi-rendered lines (no symbol+lineno).
   *  Used to render visual gaps between non-adjacent change clusters. */
  hunks: DiffLine[][];
}

const LINE_RE = /^([ +\-])\s*(\d+)\s?(.*)$/;

export function parseDiff(diff: string | undefined | null): ParsedDiff {
  const lines: DiffLine[] = [];
  let added = 0;
  let removed = 0;
  if (!diff) return { lines, added, removed, hunks: [] };

  for (const raw of diff.split("\n")) {
    const m = LINE_RE.exec(raw);
    if (!m) continue;
    const sym = m[1];
    const num = Number.parseInt(m[2], 10);
    if (Number.isNaN(num)) continue;
    const content = m[3] ?? "";
    let kind: DiffLineKind;
    if (sym === "+") {
      kind = "add";
      added++;
    } else if (sym === "-") {
      kind = "remove";
      removed++;
    } else {
      kind = "context";
    }
    lines.push({ kind, lineno: num, content });
  }

  // Group consecutive change clusters separated by long context runs.
  // Heuristic: any context line that's >2 away from the next non-context
  // starts a new hunk. We compute hunks lazily — pi's diffs are usually
  // small enough that a single hunk is fine, but keeping the structure
  // future-proofs the renderer.
  const hunks: DiffLine[][] = [];
  let current: DiffLine[] = [];
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    current.push(ln);
    if (ln.kind === "context") {
      // Look ahead — if next 3 are all context, close the hunk.
      let runOfContext = 0;
      let j = i + 1;
      while (j < lines.length && lines[j].kind === "context") {
        runOfContext++;
        if (runOfContext >= 3) break;
        j++;
      }
      if (runOfContext >= 3) {
        hunks.push(current);
        current = [];
        // Skip the long context run for the NEXT hunk start.
        i = j - 1;
      }
    }
  }
  if (current.length) hunks.push(current);

  return { lines, added, removed, hunks };
}

/**
 * Build a ParsedDiff from raw file content where every line is treated as
 * an addition. Used by WriteToolCard so a brand-new file renders with the
 * same all-green +-gutter visual as an edit (Cursor-style "everything added"
 * affordance for new files).
 */
export function synthAddDiff(content: string): ParsedDiff {
  if (!content) return { lines: [], added: 0, removed: 0, hunks: [] };
  const raw = content.split("\n");
  const stripped =
    raw.length > 1 && raw[raw.length - 1] === "" ? raw.slice(0, -1) : raw;
  const lines: DiffLine[] = stripped.map((c, i) => ({
    kind: "add",
    lineno: i + 1,
    content: c,
  }));
  return {
    lines,
    added: lines.length,
    removed: 0,
    hunks: lines.length ? [lines] : [],
  };
}

