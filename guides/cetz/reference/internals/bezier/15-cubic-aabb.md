# `bezier.cubic-aabb()` — Tight AABB Of A Cubic

Returns the tight axis-aligned bounding box of a cubic Bézier curve as
`(low, high)`, two 3-vectors. Internally calls `cubic-extrema` to find
the t-values at which the curve reaches its bounds.

## Signature

```text
cubic-aabb(s: vector, e: vector, c1: vector, c2: vector) -> (vector, vector)
```

## Parameters

- **`s`**, **`e`**, **`c1`**, **`c2`** — control points.

## Example

See [`examples/15-cubic-aabb/15-cubic-aabb.typ`](./examples/15-cubic-aabb/15-cubic-aabb.typ).
