# `intersection.line-cubic()` — Line × Cubic Bézier Intersection

Returns the array of intersection points between a line segment and a
cubic Bézier curve.

## Signature

```text
line-cubic(la: vector, lb: vector, s: vector, e: vector, c1: vector, c2: vector) -> array
```

## Parameters

- **`la`**, **`lb`** — line endpoints.
- **`s`**, **`e`**, **`c1`**, **`c2`** — cubic control points.

## Example

See [`examples/02-line-cubic/02-line-cubic.typ`](./examples/02-line-cubic/02-line-cubic.typ).
