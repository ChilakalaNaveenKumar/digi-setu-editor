# `bezier.line-cubic-intersections()` — Line × Cubic Intersections

Returns the intersection points between a line and a cubic Bézier curve.
Used by `intersections()` and various stroke-aware mark placements.

## Signature

```text
line-cubic-intersections(la: vector, lb: vector, s: vector, e: vector, c1: vector, c2: vector, ray: bool = false) -> array
```

## Parameters

- **`la`**, **`lb`** — endpoints of the line.
- **`s`**, **`e`**, **`c1`**, **`c2`** — cubic control points.
- **`ray`** — if `true`, treat the line segment as an infinite ray.

## Example

See [`examples/17-line-cubic-intersections/17-line-cubic-intersections.typ`](./examples/17-line-cubic-intersections/17-line-cubic-intersections.typ).
