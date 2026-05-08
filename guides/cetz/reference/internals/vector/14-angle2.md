# `vector.angle2()` — Signed 2D Angle

Returns the angle between two vectors as a Typst angle. Computed as
`atan2(b.y − a.y, b.x − a.x)` — a 2D direction angle from `a` to `b`.

## Signature

```text
angle2(a: vector, b: vector) -> angle
```

## Parameters

- **`a`** — origin point/vector.
- **`b`** — target point/vector.

## Example

See [`examples/14-angle2/14-angle2.typ`](./examples/14-angle2/14-angle2.typ).
