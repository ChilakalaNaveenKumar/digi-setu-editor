# `bezier.quadratic-point()` — Quadratic Bézier Point

Evaluates a quadratic Bézier curve `(a, b, c)` at parameter `t ∈ [0, 1]`
and returns the resulting point.

## Signature

```text
quadratic-point(a: vector, b: vector, c: vector, t: float) -> vector
```

## Parameters

- **`a`** — first control point (start).
- **`b`** — middle (off-curve) control point.
- **`c`** — last control point (end).
- **`t`** — interpolation parameter.

## Example

See [`examples/01-quadratic-point/01-quadratic-point.typ`](./examples/01-quadratic-point/01-quadratic-point.typ).
