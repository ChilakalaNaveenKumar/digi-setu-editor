# `box(body, ...)` — inline-level sized container

The inline counterpart to `block`. Use it inside running text to embed images, shapes, or styled spans. All elements except inline math, text, and boxes are block-level — `box()` lifts them into a paragraph.

## Parameters

| Param      | Type                                | Default       | Notes                                                              |
| ---------- | ----------------------------------- | ------------- | ------------------------------------------------------------------ |
| `width`    | `auto` / relative / fraction         | `auto`         | **Only width** can be fractional, and only inside a paragraph.     |
| `height`   | `auto` / relative                    | `auto`         | Fits content by default.                                           |
| `baseline` | relative                              | `0% + 0pt`     | Shift the baseline (positive = down).                              |
| `fill`     | `none` / color / gradient / tiling   | `none`         | Background.                                                        |
| `stroke`   | stroke spec                           | `(:)`          | Border.                                                            |
| `radius`   | relative / dictionary                 | `(:)`          | Corner rounding.                                                   |
| `inset`    | relative / dictionary                 | `(:)`          | Inner padding.                                                     |
| `outset`   | relative / dictionary                 | `(:)`          | Expand without affecting layout.                                   |
| `clip`     | bool                                  | `false`        | Clip overflow.                                                     |
| `body`     | `none` / content                     | `none`         | Content.                                                           |

## When to reach for `box`

| Use case                                       | Recipe                                                       |
| ---------------------------------------------- | ------------------------------------------------------------ |
| Embed an image inline with text                | `#box(height: 1em, image("icon.svg"))`                        |
| Inline colored "tag" span                      | `#box(fill: luma(240), inset: (x: 3pt), outset: (y: 3pt))[X]` |
| Horizontal rule that fills remaining line      | `Section #box(width: 1fr, line(length: 100%))`                |
| Lift a block element into a paragraph          | Wrap with `#box(...)`                                         |

`outset: (y: ..)` is the trick for inline styled spans: it expands the visual size *without* increasing line height.

## Examples (compile-verified)

- `examples/05-box/01-box.typ` — inline icon, styled inline rectangle, fractional width = horizontal rule, baseline shift, clipping.

## Reference

https://typst.app/docs/reference/layout/box/
