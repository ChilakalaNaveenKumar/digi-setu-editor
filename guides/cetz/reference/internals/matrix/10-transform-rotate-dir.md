# `matrix.transform-rotate-dir()` — Rotate To Look Direction

Returns a 4×4 affine rotation matrix that aligns the local axes with a
direction vector and an "up" vector — the camera-style "look‑at"
construction.

## Signature

```text
transform-rotate-dir(dir: vector, up: vector) -> matrix
```

## Parameters

- **`dir`** — forward vector to align with.
- **`up`** — up vector defining the reference plane.

## Example

See [`examples/10-transform-rotate-dir/10-transform-rotate-dir.typ`](./examples/10-transform-rotate-dir/10-transform-rotate-dir.typ).
