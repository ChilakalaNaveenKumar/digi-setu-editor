# `highlight` — colored background behind text

`highlight(body: content, fill: none | color | gradient | tiling = rgb("#fffd11a1"), stroke: ? = (:), top-edge: length | str = "ascender", bottom-edge: length | str = "descender", extent: length = 0pt, radius: relative | dictionary = (:)) -> content`

Draws a colored background rectangle behind text — the typical "marker pen" effect.

```typst
This is #highlight[important].
```

## Parameters

| Field          | Default              | Notes                                                                                |
| -------------- | -------------------- | ------------------------------------------------------------------------------------ |
| `fill`         | `rgb("#fffd11a1")`    | Semi-transparent yellow. Accepts color, gradient, tiling, or `none`                  |
| `stroke`       | `(:)`                | Border around the highlight; same syntax as `rect.stroke`                            |
| `top-edge`     | `"ascender"`         | `"ascender"` / `"cap-height"` / `"x-height"` / `"baseline"` / `"bounds"`             |
| `bottom-edge`  | `"descender"`        | `"baseline"` / `"descender"` / `"bounds"`                                            |
| `extent`       | `0pt`                | Extra horizontal padding on each side; negative trims inward                         |
| `radius`       | `(:)`                | Rounded corners (number or per-corner dict)                                          |

## Edge values

The `top-edge` / `bottom-edge` strings let you tune how tall the highlight band is relative to the glyphs:

| Value           | Where it sits                                                  |
| --------------- | -------------------------------------------------------------- |
| `"ascender"`    | Top of the font's ascender — usually beyond all glyphs          |
| `"cap-height"`  | Top of uppercase letters                                        |
| `"x-height"`    | Top of non-ascending lowercase letters (`a`, `n`, `x`, ...)    |
| `"baseline"`    | The baseline                                                    |
| `"descender"`   | Bottom of the font's descender                                  |
| `"bounds"`      | Top/bottom of the actual glyph bounding box                    |

Combine `top-edge: "x-height"` + `bottom-edge: "baseline"` for a tight Anki-style highlight that only covers the body of lowercase letters.

## Pitfalls

- **Default fill includes alpha.** `#fffd11a1` has ~63% opacity — it blends with the page color. To get a fully opaque highlight, set `fill: yellow` (or any opaque color).
- **`extent` widens the highlight horizontally only.** To grow vertically, change `top-edge` / `bottom-edge`, not `extent`.
- **Adjacent highlights run into each other.** The bands stack tightly without separation; if you want gaps, use `box(...)` per highlight or play with `extent: -1pt`.
- **Highlight is drawn UNDER the text.** Stacking semantics: text on top of fill on top of page. There's no `background: false` flag here — the highlight always sits behind glyphs.
- **`stroke` is empty by default.** Setting just `stroke: 0.5pt` doesn't change the border color; use `stroke: 0.5pt + fuchsia` for a colored border.

## Examples (compile-verified)

- `examples/01-highlight/01-highlight-styles.typ` — default, custom color, stroked, padded + rounded, `x-height`/`baseline` band tuning.

## Reference

- Official: https://typst.app/docs/reference/text/highlight/
- `rect.stroke` (stroke syntax): https://typst.app/docs/reference/visualize/rect/#parameters-stroke
- `text.top-edge` (analogous edge concept for text frames): https://typst.app/docs/reference/text/text/#parameters-top-edge
