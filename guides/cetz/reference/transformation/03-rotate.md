# `rotate()` — Rotate the Coordinate System

Rotates the transformation matrix on the z-axis by a given angle, or on
other axes when specified.

## Signature

```text
rotate(
  ..angles: angle,
  origin:   none | coordinate = none,
)
```

## Parameters

- **`..angles`** — either a single positional angle (z-rotation) or named
  arguments `x:`, `y:`, `z:`, `yaw:`, `pitch:`, `roll:` for axis-specific
  rotations.
- **`origin`** — point to rotate around. Default `(0, 0, 0)`.

## Pitfalls

- Rotation order for combined rotations follows
  `R = R_z(z) R_y(y) R_x(x)` (Euler / yaw-pitch-roll convention) when you
  pass multiple named axes in a single call. See
  [`internals/matrix/transform-rotate-xyz`](../internals/matrix/16-transform-rotate-xyz.md)
  for the underlying matrix.
- For purely 2-D rotation, the positional `rotate(45deg)` is the natural
  form.

## Example

See [`examples/03-rotate/03-rotate.typ`](./examples/03-rotate/03-rotate.typ).
