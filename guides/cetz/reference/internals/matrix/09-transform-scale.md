# `matrix.transform-scale()` — Scale Matrix

Returns a 4×4 affine matrix that scales by the supplied factor or factors.

## Signature

```text
transform-scale(f: float | (x: float, y: float, z: float) | dictionary) -> matrix
```

## Parameters

- **`f`** — scale factor(s):
  - a single number → uniform scale on all axes,
  - a 3-tuple `(sx, sy, sz)` → per-axis scale,
  - a dictionary `(x: ..., y: ..., z: ...)` → per-axis scale.

## Example

See [`examples/09-transform-scale/09-transform-scale.typ`](./examples/09-transform-scale/09-transform-scale.typ).
