# `matrix.transform-rotate-xz()` — Compose X·Z Rotations

Returns the matrix product `rotate-x(x) · rotate-z(z)` — handy for
orthographic projections that combine an elevation tilt and a heading
spin.

## Signature

```text
transform-rotate-xz(x: angle, z: angle) -> matrix
```

## Parameters

- **`x`** — rotation about X.
- **`z`** — rotation about Z.

## Example

See [`examples/15-transform-rotate-xz/15-transform-rotate-xz.typ`](./examples/15-transform-rotate-xz/15-transform-rotate-xz.typ).
