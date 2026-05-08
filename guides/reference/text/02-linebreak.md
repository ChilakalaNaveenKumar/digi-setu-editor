# `linebreak` — start a new line within a paragraph

`linebreak(justify: bool = false) -> content`

Advances to the next line **without ending the paragraph** (unlike `parbreak`). Inline content following the break is still part of the same paragraph.

## Markup shorthand

```typst
First line \
Second line \
Third line
```

`\` followed by whitespace (or end of line) inserts an unjustified line break. Always equivalent to `#linebreak()`.

## `justify: true`

Available only via the function form. Tells the line-breaker to **justify the line before breaking** — useful when you manually pick a better break point than the optimized algorithm:

```typst
#set par(justify: true)
#let jb = linebreak(justify: true)
This line will be justified to the margin #jb
even though I broke it manually.
```

Without `justify: true`, your manually broken lines render ragged-right even inside a justified paragraph.

## Trailing line breaks at end-of-paragraph

| Pattern        | Effect                                                    |
| -------------- | --------------------------------------------------------- |
| `text \`       | Single trailing break — **ignored**                        |
| `text \ \`     | Two trailing breaks — adds **one empty line**              |
| `text \ \ \`   | Three trailing breaks — adds two empty lines               |

This avoids the surprise of "I added a `\` at the end of my line and got a stray empty line".

## `linebreak` vs `parbreak`

| Use                             | Function     |
| ------------------------------- | ------------ |
| Same paragraph, new line        | `linebreak`  |
| End paragraph, start new one    | `parbreak` (or blank line) |
| End page                        | `pagebreak`  |

`linebreak` keeps `par`-level state (first-line-indent, line numbering counter, etc.) intact; `parbreak` resets it.

## Pitfalls

- **`\` requires whitespace after it.** `\foo` is escape syntax, not a line break. Write `\ foo` or `\\nfoo`.
- **Markup `\` is always unjustified.** If you need justified line breaks, use `linebreak(justify: true)` directly.
- **Empty lines via `\ \` count toward layout.** Whitespace at the end of a paragraph isn't free.
- **Inside list/enum items**, `\` line breaks work normally; nested `parbreak` would end the item entirely.
- **Inside `box(...)`**, `linebreak` still wraps inside the box. Don't expect a `\` to break OUT of a box.

## Examples (compile-verified)

- `examples/02-linebreak/01-linebreak-syntax.typ` — markup `\`, function-form `linebreak(justify: true)` for manual justified breaks, trailing-break behaviour.

## Reference

- Official: https://typst.app/docs/reference/text/linebreak/
- `parbreak`: https://typst.app/docs/reference/model/parbreak/
- `pagebreak`: https://typst.app/docs/reference/layout/pagebreak/
