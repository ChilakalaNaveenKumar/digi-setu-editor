# `bezier.cubic-extrema()` — Cubic Extrema

Returns the parameter values `t ∈ (0, 1)` at which the cubic Bézier
curve reaches a local extremum on each axis. CeTZ uses these to compute
tight axis-aligned bounding boxes for cubic curves.

## Signature

```text
cubic-extrema(s: vector, e: vector, c1: vector, c2: vector) -> array
```

## Parameters

- **`s`**, **`e`**, **`c1`**, **`c2`** — control points.

## Example

See [`examples/14-cubic-extrema/14-cubic-extrema.typ`](./examples/14-cubic-extrema/14-cubic-extrema.typ).
