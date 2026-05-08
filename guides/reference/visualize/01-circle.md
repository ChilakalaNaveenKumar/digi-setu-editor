# `circle()` — Drawing Circles

`circle` produces a circle, optionally filled with content. The circle keeps
a 1:1 aspect ratio and grows to fit its body if both `radius` and explicit
dimensions are omitted.

## Signature

```text
circle(
  radius: length = 0pt,
  width:  auto | relative = auto,
  height: auto | relative | fraction = auto,
  fill:   none | color | gradient | tiling = none,
  stroke: none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  inset:  relative | dictionary = 0% + 5pt,
  outset: relative | dictionary = (:),
  body:   none | content = none,
) -> content
```

`radius`, `width`, and `height` are **mutually exclusive**. Use `radius` for
absolute sizing, `width`/`height` when you need a circle whose size scales
with its parent (e.g. `width: 50%`).

## When to use what

| Goal                                         | Reach for                            |
| -------------------------------------------- | ------------------------------------ |
| Fixed-size dot, marker, badge                | `circle(radius: 4pt, fill: ...)`     |
| Circle that grows with the container         | `circle(width: 100%)`                |
| Circle that wraps content                    | `circle[Centered text]`              |
| Outline-only circle                          | `circle(stroke: 1pt + black)`        |

## Default stroke disappears with `fill`

If you set a `fill`, the default 1pt black stroke is dropped. Set `stroke:`
explicitly if you need both.

## Padding (`inset`) and bleed (`outset`)

`inset` adds invisible padding **inside** the circle (default `0% + 5pt`
keeps content from touching the rim). `outset` enlarges the circle's
bounding box without affecting layout — handy for highlight bubbles.

See the [box documentation](../layout/05-box.md) for the per-side
dictionary form (`(left: 2pt, rest: 0pt)`).
