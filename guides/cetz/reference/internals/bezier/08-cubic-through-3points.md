# `bezier.cubic-through-3points()` — Cubic Bézier Through 3 Points

Computes the two off-curve control points of a cubic Bézier curve that
passes through `s`, `B`, `e`. Used by `bezier-through` when 3 points and
4 control points are wanted.

## Signature

```text
cubic-through-3points(s: vector, B: vector, e: vector) -> (vector, vector)
```

## Parameters

- **`s`** — start.
- **`B`** — required through-point.
- **`e`** — end.

## Example

See [`examples/08-cubic-through-3points/08-cubic-through-3points.typ`](./examples/08-cubic-through-3points/08-cubic-through-3points.typ).
