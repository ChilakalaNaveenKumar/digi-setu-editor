# `matrix.mul4x4-vec3()` — Apply 4×4 Matrix to 3-Vector

Applies a 4×4 affine matrix to a 3-vector. The optional `w` value is the
homogeneous coordinate (defaults to `1.0`, i.e. treat the vector as a
point; pass `0.0` to treat it as a direction).

## Signature

```text
mul4x4-vec3(mat: matrix, vec: vector, w: float = 1.0) -> vector
```

## Parameters

- **`mat`** — 4×4 transformation matrix.
- **`vec`** — 3-component vector.
- **`w`** — homogeneous coordinate.

## Example

See [`examples/19-mul4x4-vec3/19-mul4x4-vec3.typ`](./examples/19-mul4x4-vec3/19-mul4x4-vec3.typ).
