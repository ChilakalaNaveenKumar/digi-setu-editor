# 01 — Writing Basics

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/tutorial/writing-in-typst/>
> **Audience:** an LLM agent that authors `.typ` files. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/01-writing-basics/`). Every line of prose here is an original reference; the canonical Typst tutorial is the human-friendly source.

---

## Modes (the foundation — do not skip)

Typst has three modes. Knowing which mode the cursor is in tells you whether `_x_` means italic, whether `#name(...)` is needed, and whether `[...]` is a string or content.

| Mode | Where you are | Function call syntax | Bracketed text |
|---|---|---|---|
| **Markup** | top-level document, content blocks `[...]` | `#name(args)` | `[...]` is a content block |
| **Code** | inside any `(...)` argument list, after `#` | `name(args)` (no `#`) | `[...]` is a content literal |
| **Math** | between `$...$` | `name(args)` (no `#`) | n/a |

When a function takes content, you pass `[ ... markup ... ]`. When it takes a string (e.g. a file path), you pass `"..."`. They are not interchangeable.

---

## 1. Paragraphs

- **Syntax:** Plain text. A blank line starts a new paragraph.
- **Example:** [`01-paragraph.typ`](./examples/01-writing-basics/01-paragraph.typ)
- **Pitfalls:** A single newline does not break a paragraph — it is treated as a soft wrap (a single space).

## 2. Headings

- **Syntax:** Line begins with one or more `=`. Level = count of `=` (1–6 typical). Whitespace must follow the last `=`.
- **Example:** [`02-headings.typ`](./examples/01-writing-basics/02-headings.typ)
- **Pitfalls:**
  - `=` must be at the start of the line (after optional indentation).
  - Do not put a space between the `=` characters: `= =` is `=` followed by literal `=`, not heading level 2.
  - Headings are content; they can be labelled (`<id>` after the line).

## 3. Italic emphasis

- **Syntax:** `_text_` inside markup mode.
- **Example:** [`03-emphasis.typ`](./examples/01-writing-basics/03-emphasis.typ)
- **Pitfalls:**
  - Underscores adjacent to letters are treated as part of the word (e.g. `snake_case_var` is not italics — only when `_` opens/closes around a span).
  - In math mode `_` means subscript, not italics. Do not use `_x_` for italics inside `$...$`.

## 4. Numbered list

- **Syntax:** Each item starts with `+` followed by a space.
- **Example:** [`04-numbered-list.typ`](./examples/01-writing-basics/04-numbered-list.typ)
- **Pitfalls:** Numbering is automatic — never write `1.`, `2.` yourself.

## 5. Bullet list

- **Syntax:** Each item starts with `-` followed by a space.
- **Example:** [`05-bullet-list.typ`](./examples/01-writing-basics/05-bullet-list.typ)
- **Pitfalls:** A `-` not at line-start is just a hyphen.

## 6. Nested lists

- **Syntax:** Indent the child item more than its parent. Numbered and bulleted nest freely.
- **Example:** [`06-nested-list.typ`](./examples/01-writing-basics/06-nested-list.typ)
- **Pitfalls:** Indentation must be consistent. Mixing tabs and spaces will silently produce a flat list.

## 7. Images — basic call

- **Syntax:** `#image("path/to/file")`. Supported formats: PNG, JPEG, GIF, SVG, PDF, WebP.
- **Example:** [`07-image-basic.typ`](./examples/01-writing-basics/07-image-basic.typ)
- **Pitfalls:**
  - The path is a string — always double-quoted.
  - Path is resolved relative to the source file by default.
  - Without `width`/`height`, the image fills the page width.

## 8. Images — sized with named arguments

- **Syntax:** `#image("path", width: <relative-length>)`. Lengths can be percentages (`70%`), absolute (`1cm`, `0.7in`, `120pt`), or `auto`.
- **Example:** [`08-image-width.typ`](./examples/01-writing-basics/08-image-width.typ)
- **Pitfalls:**
  - Named arguments come after positional ones, separated by commas.
  - Use `width: 70%`, not `width = 70%` (Typst uses `:` for named args, `=` would be a code-mode binding).

## 9. Figure with caption

- **Syntax:**
  ```
  #figure(
    image("path", width: ...),
    caption: [ ... markup ... ],
  )
  ```
- **Example:** [`09-figure-with-caption.typ`](./examples/01-writing-basics/09-figure-with-caption.typ)
- **Pitfalls:** Inside `figure(...)` you are in **code mode**, so the inner `image(...)` does **not** get a `#`. The caption is markup → wrap it in `[ ... ]`.

## 10. Labels and references

- **Syntax:**
  - Label: place `<name>` immediately after the element to label.
  - Reference: write `@name` in prose.
- **Example:** [`10-figure-labeled-and-referenced.typ`](./examples/01-writing-basics/10-figure-labeled-and-referenced.typ)
- **Pitfalls:**
  - Label name allows letters, digits, `-`, `_`, `:` and `.` — no spaces.
  - The label must come after the element; placing it before silently fails.
  - Headings and equations are referenceable too.

## 11. Bibliography and citations

- **Syntax:**
  - Load: `#bibliography("works.bib")` (BibLaTeX) or `"works.yml"` (Hayagriva, native).
  - Cite: `@key` (same syntax as a label reference).
- **Example:** [`11-bibliography.typ`](./examples/01-writing-basics/11-bibliography.typ)
- **Pitfalls:**
  - Only entries that are actually cited appear in the rendered bibliography (default behaviour).
  - The cited `@key` must exist in the loaded file; otherwise compile fails.
  - One bibliography per document.

## 12. Math — inline

- **Syntax:** `$expr$` with **no** padding space immediately after the opening `$` or before the closing `$`.
- **Example:** [`12-math-inline.typ`](./examples/01-writing-basics/12-math-inline.typ)
- **Pitfalls:** Adding padding spaces (`$ expr $`) switches it to block math.

## 13. Math — block (display)

- **Syntax:** `$ expr $` — exactly one space after `$` and one before the closing `$`. That whitespace is the *signal* for block math.
- **Example:** [`13-math-block.typ`](./examples/01-writing-basics/13-math-block.typ)
- **Pitfalls:** A missing space on either side silently downgrades to inline.

## 14. Math — single vs multi-letter identifiers

- **Rule:**
  - A **single letter** in math mode renders verbatim (e.g. `Q`, `v`).
  - A **run of two or more letters** is parsed as one symbol/variable/function name. `rho` → `ρ`. `lambda` → `λ`.
  - Implicit multiplication of two single-letter variables is written as `a b` (with a space). `ab` is the symbol/variable named `ab`.
  - To force a multi-letter literal *as text*, wrap it in double quotes: `"warmup offset"`.
- **Example:** [`14-math-multiletter-quoted.typ`](./examples/01-writing-basics/14-math-multiletter-quoted.typ)
- **Pitfalls:** Writing `Tn` when you meant `T n` will look up an identifier named `Tn` and print it as plain text instead of as `T · n`.

## 15. Math — subscripts and superscripts

- **Syntax:**
  - Subscript: `x_i`. Superscript: `x^2`.
  - For multi-character sub/superscripts, **wrap in `(...)`**: `x_(i+1)`, `e^(2 pi i)`.
- **Example:** [`15-math-sum-sub-super.typ`](./examples/01-writing-basics/15-math-sum-sub-super.typ)
- **Pitfalls:** `x_i+1` is `x_i` followed by `+ 1`, not `x_{i+1}`. Always parenthesise compound sub/superscripts.

## 16. Math — fractions

- **Syntax:** `numerator / denominator`. Parentheses around either side group the operand for the fraction but are not rendered.
- **Example:** [`16-math-fractions-and-parens.typ`](./examples/01-writing-basics/16-math-fractions-and-parens.typ)
- **Pitfalls:** `a + b / c` is `a + (b/c)`, not `(a+b)/c`. Use explicit `(a + b) / c`.

## 17. Math — function calls

- **Syntax:** `name(args)` — **no `#` prefix** inside math mode.
- **Example:** [`17-math-vec-function.typ`](./examples/01-writing-basics/17-math-vec-function.typ)
- **Notes:** Some functions exist only inside math mode — `vec`, `mat`, `cases`, `cal`, `frak`, `bb`, etc.
- **Pitfalls:** Writing `#vec(...)` inside `$...$` is a syntax error.

## 18. Math — symbol variants

- **Syntax:** Append a dot and a modifier name to a symbol: `arrow.squiggly`, `arrow.r.long`, `eq.not`.
- **Example:** [`18-math-symbol-variant.typ`](./examples/01-writing-basics/18-math-symbol-variant.typ)
- **Pitfalls:** Variant chains read left-to-right and are order-sensitive in some families. Validate by compiling.

## 19. Symbols in markup mode

- **Syntax:** Outside math, the same named symbols are reached via `#sym.NAME` (or `#sym.NAME.variant`).
- **Example:** [`19-symbol-in-markup.typ`](./examples/01-writing-basics/19-symbol-in-markup.typ)
- **Pitfalls:** `#arrow.r` is not valid (there is no top-level `arrow` function in markup); it must be `#sym.arrow.r`.

---

## Quick reference — markup characters this page introduces

| Character(s) | Meaning in markup mode |
|---|---|
| `=`, `==`, `===`, … | Heading levels 1, 2, 3, … |
| `_text_` | Italic emphasis |
| `+` (line start) | Numbered list item |
| `-` (line start) | Bullet list item |
| `#name(args)` | Function call |
| `[ ... ]` (in arg list) | Content block (markup as an argument) |
| `"..."` (in arg list) | String (file path, identifier, etc.) |
| `<label>` | Label attached to the preceding element |
| `@name` | Reference to a labelled element / cite key |
| `$ ... $` | Block math (note the spaces) |
| `$...$` | Inline math (no spaces) |

## Quick reference — math characters this page introduces

| Character(s) | Meaning in math mode |
|---|---|
| `_` | Subscript |
| `^` | Superscript |
| `/` | Fraction |
| `(...)` | Grouping (not rendered) |
| `"..."` | Literal multi-char text inside math |
| `name` (≥2 letters) | Symbol / variable / function name |
| `name.variant` | Symbol variant |
| `name(args)` | Function call (no `#`) |

---

## Self-check before shipping any `.typ` file

1. Did every `#fn(...)` need its `#`? (No `#` inside `(...)` arg lists or `$...$`.)
2. Are all multi-character subscripts/superscripts in `(...)`?
3. Is every cited `@key` present in the bibliography file?
4. Does the file actually compile? (`typst compile path.typ /tmp/out.pdf`)
