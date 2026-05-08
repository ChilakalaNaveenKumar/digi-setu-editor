# `bezier.cubic-arclen()` — Cubic Bézier Arc Length

Approximates the arc length of a cubic Bézier curve via Gauss–Legendre
quadrature with `samples` sample points.

## Signature

```text
cubic-arclen(s: vector, e: vector, c1: vector, c2: vector, samples: int = 20) -> float
```

## Parameters

- **`s`**, **`e`**, **`c1`**, **`c2`** — control points of the curve.
- **`samples`** — number of quadrature samples (more = more accurate, slower).

## Example

See [`examples/10-cubic-arclen/10-cubic-arclen.typ`](./examples/10-cubic-arclen/10-cubic-arclen.typ).
