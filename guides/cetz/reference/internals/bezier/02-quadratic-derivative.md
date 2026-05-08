# `bezier.quadratic-derivative()` — Quadratic Bézier Derivative

Returns the derivative (tangent vector) of a quadratic Bézier curve at
`t`. The vector points along the local tangent of the curve.

## Signature

```text
quadratic-derivative(a: vector, b: vector, c: vector, t: float) -> vector
```

## Parameters

Same as [`quadratic-point`](./01-quadratic-point.md).

## Example

See [`examples/02-quadratic-derivative/02-quadratic-derivative.typ`](./examples/02-quadratic-derivative/02-quadratic-derivative.typ).
