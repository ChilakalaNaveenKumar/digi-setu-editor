# `bezier.cubic-point()` — Cubic Bézier Point

Evaluates a cubic Bézier curve `(a, c1, c2, b)` at parameter `t` and
returns the resulting point.

## Signature

```text
cubic-point(a: vector, b: vector, c1: vector, c2: vector, t: float) -> vector
```

## Parameters

- **`a`** — start.
- **`b`** — end.
- **`c1`**, **`c2`** — first and second off-curve control points.
- **`t`** — interpolation parameter.

## Example

See [`examples/03-cubic-point/03-cubic-point.typ`](./examples/03-cubic-point/03-cubic-point.typ).
