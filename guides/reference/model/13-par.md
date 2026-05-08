# `par` — paragraphs and line numbering

`par(body, leading, spacing, justify, linebreaks, justification-limits, first-line-indent, hanging-indent) -> content`

Typst auto-collects inline content into paragraphs; you mainly use `par` in **set rules** to configure how paragraphs render. The element is also available as `par.line` for line-numbering.

## Most-used fields

| Field                  | Default     | What it does                                                                            |
| ---------------------- | ----------- | --------------------------------------------------------------------------------------- |
| `leading`              | `0.65em`    | Spacing between lines INSIDE a paragraph (bottom edge → top edge)                        |
| `spacing`              | `1.2em`     | Spacing between adjacent paragraphs                                                      |
| `justify`              | `false`     | Justify lines (auto-enables hyphenation if `text(hyphenate: auto)` and `lang` is known) |
| `linebreaks`           | `auto`      | `"simple"` (first-fit) or `"optimized"` (whole-paragraph). `auto` = optimized when justified |
| `justification-limits` | (defaults)  | How much spacing/tracking may stretch/shrink during justification                        |
| `first-line-indent`    | `0pt`       | Length OR `(amount: len, all: bool)`. `all: false` = only consecutive paragraphs        |
| `hanging-indent`       | `0pt`       | Indent for non-first lines                                                                |

## When does inline text become a paragraph?

| Location                                            | Wrapped in `par`?                  |
| --------------------------------------------------- | ----------------------------------- |
| Top of document                                     | Yes                                 |
| Inside a container (`#block`, `#figure`, ...) with **only** inline content | No |
| Same container, but with any block-level content too | Yes                                 |

To **force** a one-word run to become a paragraph, add a `parbreak()` after it. To **prevent** wrapping, put the inline content inside a `#block(...)`.

Why it matters:
- `par` set rules and `#show par:` rules only fire on real paragraphs.
- `first-line-indent` only applies to real paragraphs.
- PDF/HTML export emits a `<P>` / `<p>` tag only for real paragraphs (impacts accessibility).

## `par.line` — line numbering

`par.line` is *only* used in set rules; you can't place it directly. Set rules **must come before any page content** (numbering scope is uniform per page run).

| Field             | Default      | Notes                                                          |
| ----------------- | ------------ | -------------------------------------------------------------- |
| `numbering`       | `none`       | Pattern string OR function `(int) -> content`                  |
| `number-align`    | `auto`       | `auto` = grow away from text                                   |
| `number-margin`   | `start`      | `start` / `end` / `left` / `right`                             |
| `number-clearance`| `auto`       | Distance between number column and text                        |
| `numbering-scope` | `"document"` | `"page"` resets per page; `"document"` runs end-to-end          |

Disable line numbers inside selected elements with show-set rules:

```typst
#show figure: set par.line(numbering: none)
```

## Pitfalls

- **`first-line-indent` only fires between *consecutive* paragraphs by default** — never on the first paragraph in the document/container, never after a heading or other block. Use `(amount: ..., all: true)` to indent every paragraph.
- **Block-level content interrupts paragraphs.** Inserting a `#block(...)` between two paragraphs ends the first paragraph and starts a second. Adjacent block elements override `par.spacing` with their own `above`/`below`.
- **Adjacent inline-only containers don't get `par`.** A 1-word `#block[hi]` is NOT a paragraph; you can't style it with `set par`.
- **`par.line` set rule placement.** If you call `set par.line(numbering: ...)` AFTER content has been laid out on a page, you'll get an error or inconsistent numbering. Put it at the top of the document.
- **Justification + ragged alignment.** Setting `justify: true` still respects `align(...)`; the last line follows the alignment unless the line ends with a `linebreak(justify: true)`.

## Examples (compile-verified)

- `examples/13-par/01-justify-indent-spacing.typ` — `justify: true`, `first-line-indent` (length form vs `(amount, all: true)` dict form), `leading` / `spacing`.
- `examples/13-par/02-line-numbering.typ` — colored line numbers via function form, `numbering-scope: "page"`, suppressing numbers inside figures with show-set.

## Reference

- Official: https://typst.app/docs/reference/model/par/
- `parbreak`: https://typst.app/docs/reference/model/parbreak/
- `block`: https://typst.app/docs/reference/layout/block/
- `text` (font / hyphenation): https://typst.app/docs/reference/text/text/
