# `bezier.catmull-to-cubic()` — Convert Catmull–Rom To Cubic Béziers

Converts a Catmull–Rom spline through a list of `points` (with tension
`k`) into a list of cubic Bézier sections. Used by the `catmull` shape.

## Signature

```text
catmull-to-cubic(points: array, k: float, close: bool = false) -> array
```

## Parameters

- **`points`** — array of vectors the spline passes through.
- **`k`** — tension parameter in `[0, 1]` — `0.5` is the canonical value.
- **`close`** — if `true`, the spline forms a closed loop.

## Example

See [`examples/16-catmull-to-cubic/16-catmull-to-cubic.typ`](./examples/16-catmull-to-cubic/16-catmull-to-cubic.typ).
