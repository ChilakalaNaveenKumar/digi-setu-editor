# `overline` — line above text

`overline(body: content, stroke: auto | stroke = auto, offset: auto | length = auto, extent: length = 0pt, evade: bool = true, background: bool = false) -> content`

Draws a horizontal line **above** the text.

```typst
#overline[A line over text.]
```

## Parameters (shared shape with `underline` and `strike`)

| Field        | Default  | What it does                                                     |
| ------------ | -------- | ---------------------------------------------------------------- |
| `stroke`     | `auto`   | `auto` = font color + font-recommended thickness; or any stroke value |
| `offset`     | `auto`   | Position relative to the baseline; `auto` reads font tables       |
| `extent`     | `0pt`    | Extra horizontal extent on each side; negative trims inward      |
| `evade`      | `true`   | Skip sections where the line would collide with glyphs (e.g. tall ascenders) |
| `background` | `false`  | `true` puts the line BEHIND glyphs, `false` puts it in FRONT      |

## When to use which underline-family function

| Function     | Line position                  | Typical use            |
| ------------ | ------------------------------ | ---------------------- |
| `overline`   | Above the text                 | Vector / set notation, archaic emphasis |
| `underline`  | Below the baseline             | Emphasis, links        |
| `strike`     | Through the middle             | Edits, redaction (visual only) |

## Pitfalls

- **`evade: true` only matters when the line would actually cross glyph outlines.** For overlines, this kicks in for tall capitals or glyphs with diacritics that poke above the cap height.
- **`offset` direction depends on the function.** For `overline`, *positive* values move the line down (toward the text). To raise it further above the text, use a *negative* offset. For `underline`, positive moves down (away from baseline).
- **`stroke: auto`** picks up the current `text.fill` color. Wrap in `text(fill: ...)` if you want both glyph and line to be a non-default color without specifying stroke twice.
- **`background: true` is invisible unless the stroke is thick enough** to extend past glyph outlines. Useful for highlighting-like effects with a wide stroke.
- **Line breaks inside the overlined content** produce ONE line per visible row — the over-line is per-line, not per-element. Long content wrapped over multiple lines gets multiple overlines.

## Examples (compile-verified)

- `examples/05-overline/01-overline.typ` — defaults, custom stroke + offset, `extent` ±, `evade` on/off, `background: true` with a thick stroke.

## Reference

- Official: https://typst.app/docs/reference/text/overline/
- `underline`: https://typst.app/docs/reference/text/underline/
- `strike`: https://typst.app/docs/reference/text/strike/
- `stroke`: https://typst.app/docs/reference/visualize/stroke/
