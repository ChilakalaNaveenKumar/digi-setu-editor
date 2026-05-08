# `matrix.transform-shear-x()` — Shear Along X

Returns a 4×4 affine matrix that shears along the X axis with the given
factor — equivalent to `(x, y, z) → (x + factor·y, y, z)`.

## Signature

```text
transform-shear-x(factor: float) -> matrix
```

## Parameters

- **`factor`** — shear factor.

## Example

See [`examples/07-transform-shear-x/07-transform-shear-x.typ`](./examples/07-transform-shear-x/07-transform-shear-x.typ).
