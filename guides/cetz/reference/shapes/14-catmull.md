# `catmull()` — Catmull-Rom Spline

Draws a Catmull-Rom spline that passes through every input point.

## Signature

```text
catmull(
  ..pts-style: coordinate | style,
  close: bool      = false,
  name:  none | str = none,
)
```

## Parameters

- **`..pts-style`** — positional arguments are the points the curve passes
  through. Named arguments configure styling.
- **`close`** — when `true` the curve closes with a straight line between
  start and end.
- **`name`** — element name.
- **`tension`** *(style)* — `float`. How tight the curve fits the points.
  Higher = less curvy. Typical range `[0.4, 0.5]`.

## Styling

- **Root:** `catmull`
- Supports `mark`.

## Anchors

Path anchors plus `pt-0`, `pt-1`, … (one per input point; `pt-0` ≡ `start`).

## Example

See [`examples/14-catmull/14-catmull.typ`](./examples/14-catmull/14-catmull.typ).

## Related

- [`hobby`](./15-hobby.md) — alternative smooth-fit curve (Hobby algorithm)
- [`bezier.catmull-to-cubic`](../internals/bezier/16-catmull-to-cubic.md)
  — the conversion to cubic Bezier sections that powers this shape
