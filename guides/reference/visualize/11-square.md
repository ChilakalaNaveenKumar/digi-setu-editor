# `square()` — Squares

`square` is `rect` with a 1:1 aspect ratio enforced. It exposes one
extra parameter, `size`, that sets both side lengths at once.

## Signature

```text
square(
  size:   auto | length = auto,                  // exclusive with width/height
  width:  auto | relative = auto,
  height: auto | relative | fraction = auto,
  fill:   none | color | gradient | tiling = none,
  stroke: none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  radius: relative | dictionary = (:),
  inset:  relative | dictionary = 0% + 5pt,
  outset: relative | dictionary = (:),
  body:   none | content = none,
) -> content
```

`size`, `width`, and `height` are **mutually exclusive**:

- `size: 30pt` — both sides 30pt.
- `width: 50%` — both sides equal 50% of the parent width.
- `height: 1cm` — both sides 1cm.

If you don't pass any of those and there's no body, you get a default
`30pt × 30pt` square. With a body and no explicit size, the square grows
to fit while preserving 1:1.

All other parameters behave exactly as in [`rect`](./10-rect.md):
`fill` removes the default stroke, `inset`/`outset`/`radius` accept either
a single value or a per-side/per-corner dictionary.

## When to use

| Pattern                          | Snippet                                              |
| -------------------------------- | ---------------------------------------------------- |
| Color swatch                     | `#square(size: 24pt, fill: red)`                     |
| Square avatar slot               | `#square(width: 40%, fill: gray.lighten(80%))`       |
| Centered icon tile               | `#square(size: 1cm, fill: white, stroke: 0.5pt + black)[★]` |
