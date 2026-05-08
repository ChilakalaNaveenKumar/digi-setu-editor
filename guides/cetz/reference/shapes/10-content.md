# `content()` — Place Typst Content on the Canvas

Positions arbitrary Typst content (text, math, boxes, images, …) on the
canvas. The content itself is **not** transformed — only its position is
(use the `auto-scale` style if you need scaling).

## Signature

```text
content(
  ..args-style: coordinate | content | style,
  angle:  angle | coordinate = 0deg,
  anchor: none | str = none,
  name:   none | str = none,
)
```

## Forms

| Call | Result |
| ---- | ------ |
| `content(p, body)` | Place `body` at point `p`. |
| `content(a, b, body)` | Place `body` inside the rectangle from `a` to `b`. |
| `content(p, body, angle: …)` | Rotate `body` by an angle. |
| `content(p, body, angle: q)` | Rotate `body` to point its right side toward `q`. |

## Styling

- **Root:** `content`
- **`padding`** *(style)* — `number | dictionary`. Spacing around the body.
- **`frame`** *(style)* — `none | "rect" | "circle"`. Inherits the current
  `stroke`/`fill` for the frame.
- **`auto-scale`** *(style)* — `bool`. When `true`, the body scales with the
  current canvas scale (default `false`).
- **`wrap`** *(style)* — `function | none`. Wraps the body, e.g.
  `text.with(red)` to colourise everything. Must return content.

## Anchors

Border anchors (default `center`), plus baseline-aware ones:

| Anchor | Position |
| ------ | -------- |
| `mid` | content centre, baseline → top |
| `mid-east` / `mid-west` | extended sideways at mid height |
| `base` | horizontally centred baseline |
| `base-east` / `base-west` | extended sideways at baseline |
| `text` | content start on the baseline |

## Pitfalls

- The body's metrics are measured by Typst; size differences in the wrap
  function (`wrap: text.with(size: 24pt)`) **are** reflected in the bounds.
- For text on a line, set `angle:` to the line's end coordinate so the text
  rotates to follow the line direction (see example).

## Example

See [`examples/10-content/10-content.typ`](./examples/10-content/10-content.typ).

## Related

- [`drawable.content`](../internals/drawable/06-content.md) — the
  underlying drawable
- [`util.measure`](../internals/util/16-measure.md) — measures content
  size during anchor resolution
- [`util.as-padding-dict`](../internals/util/17-as-padding-dict.md) —
  normalises the `padding:` style
