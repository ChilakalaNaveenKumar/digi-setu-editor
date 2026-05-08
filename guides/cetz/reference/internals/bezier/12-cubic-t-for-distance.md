# `bezier.cubic-t-for-distance()` — Find `t` For An Arc Distance

Returns the parameter `t` at which the cumulative arc length of the cubic
Bézier curve `(s, e, c1, c2)` equals `d`.

## Signature

```text
cubic-t-for-distance(s: vector, e: vector, c1: vector, c2: vector, d: float, samples: int = 20) -> float
```

## Parameters

- **`s`**, **`e`**, **`c1`**, **`c2`** — control points.
- **`d`** — desired arc-length distance from the start.
- **`samples`** — quadrature samples to use for the arc-length estimate.

## Example

See [`examples/12-cubic-t-for-distance/12-cubic-t-for-distance.typ`](./examples/12-cubic-t-for-distance/12-cubic-t-for-distance.typ).
