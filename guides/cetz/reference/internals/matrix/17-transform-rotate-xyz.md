# `matrix.transform-rotate-xyz()` — Compose X·Y·Z Rotations

Returns the matrix product `rotate-x(x) · rotate-y(y) · rotate-z(z)`.

## Signature

```text
transform-rotate-xyz(x: angle, y: angle, z: angle) -> matrix
```

## Parameters

- **`x`**, **`y`**, **`z`** — rotation angles about each axis, applied in
  the order X then Y then Z.

## Example

See [`examples/17-transform-rotate-xyz/17-transform-rotate-xyz.typ`](./examples/17-transform-rotate-xyz/17-transform-rotate-xyz.typ).
