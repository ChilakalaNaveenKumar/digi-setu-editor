# `bezier.quadratic-through-3points()` — Quadratic Bézier Through 3 Points

Returns the off-curve control point of a quadratic Bézier curve that
passes through `s`, `B`, `e` (in that order). Used internally by the
`bezier-through` shape with two control points.

## Signature

```text
quadratic-through-3points(s: vector, B: vector, e: vector) -> vector
```

## Parameters

- **`s`** — start.
- **`B`** — required through-point (defaults to lying at `t = 0.5`).
- **`e`** — end.

## Example

See [`examples/06-quadratic-through-3points/06-quadratic-through-3points.typ`](./examples/06-quadratic-through-3points/06-quadratic-through-3points.typ).
