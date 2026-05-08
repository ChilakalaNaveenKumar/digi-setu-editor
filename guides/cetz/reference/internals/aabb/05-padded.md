# `aabb.padded()` — Pad A Bounding Box

Returns a new bounds dictionary expanded outward by `padding` on every
side. The argument can be a single number, a 2-tuple `(x, y)`, a 3-tuple
`(x, y, z)`, or a dictionary `(left, right, top, bottom, ...)`.

## Signature

```text
padded(bounds: bounds, padding: float | array | dictionary) -> bounds
```

## Parameters

- **`bounds`** — input bounds.
- **`padding`** — outward padding to apply.

## Example

See [`examples/05-padded/05-padded.typ`](./examples/05-padded/05-padded.typ).
