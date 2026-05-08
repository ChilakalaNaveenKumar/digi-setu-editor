# `strike` — strikethrough text

`strike(body: content, stroke: auto | stroke = auto, offset: auto | length = auto, extent: length = 0pt, background: bool = false) -> content`

Draws a horizontal line **through** text.

```typst
This is #strike[not] relevant.
```

## Parameters (similar shape to `overline`/`underline` — but **no `evade`**)

| Field        | Default  | What it does                                                          |
| ------------ | -------- | --------------------------------------------------------------------- |
| `stroke`     | `auto`   | `auto` = font color + font-recommended thickness                       |
| `offset`     | `auto`   | Vertical offset from the strike position                                |
| `extent`     | `0pt`    | Extra horizontal extent on each side; negative trims inward             |
| `background` | `false`  | `true` = behind glyphs; `false` = in front                              |

There is **no `evade` parameter** for `strike` — the line always crosses through.

## Not for redaction

A thick `stroke` makes content look "redacted", but the underlying text is **still selectable, copyable, and present in PDF text extraction**. For real redaction:

- Render redacted regions as `rect(fill: black, ...)` instead of striking through.
- Or process the PDF post-hoc with a real redaction tool.

## Pitfalls

- **NOT actual redaction.** Anyone can copy-paste the struck-through text. The Typst docs explicitly call this out.
- **`offset: auto`** uses font metrics, which can put the line awkwardly low for some fonts (especially serif fonts with high `x-height`). If `auto` looks wrong, set a manual offset.
- **No `evade` field.** The line always crosses every glyph. There's no "skip the descender" option (that wouldn't make sense for strikethrough anyway).
- **`extent` is per-side**, same as the other line elements.
- **`background: true` is invisible at default thickness.** Only the thick-stroke "highlighter" variant benefits from this.
- **Strike inside a heading** is technically allowed but unusual — most styles don't strike headings.

## Examples (compile-verified)

- `examples/09-strike/01-strike.typ` — default, custom stroke (color + thickness), font-driven `offset` vs manual, `extent` ±, `background: true`.

## Reference

- Official: https://typst.app/docs/reference/text/strike/
- `overline`: https://typst.app/docs/reference/text/overline/
- `underline`: https://typst.app/docs/reference/text/underline/
- `stroke`: https://typst.app/docs/reference/visualize/stroke/
