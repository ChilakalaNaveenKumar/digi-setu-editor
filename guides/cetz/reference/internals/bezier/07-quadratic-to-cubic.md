# `bezier.quadratic-to-cubic()` — Promote To Cubic

Promotes a quadratic Bézier curve `(s, e, c)` into the equivalent cubic
representation `(s, e, c1, c2)`. Useful when a renderer or storage format
only supports cubics.

## Signature

```text
quadratic-to-cubic(s: vector, e: vector, c: vector) -> (s, e, c1, c2)
```

## Parameters

- **`s`** — start.
- **`e`** — end.
- **`c`** — quadratic off-curve control point.

## Example

See [`examples/07-quadratic-to-cubic/07-quadratic-to-cubic.typ`](./examples/07-quadratic-to-cubic/07-quadratic-to-cubic.typ).
