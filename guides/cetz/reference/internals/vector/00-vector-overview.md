# `vector` — 3D Vector Math

`cetz.vector` is the workhorse module for vector arithmetic — used by every
shape, transformation and projection.

A *vector* in CeTZ is a Typst array of 3 floats `(x, y, z)`. Most functions
also accept a 2-element form `(x, y)` and pad with `0` automatically (via
`as-vec`).

The module is exposed at `cetz.vector.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-as-mat.md`](./01-as-mat.md) | `as-mat()` |
| [`02-as-vec.md`](./02-as-vec.md) | `as-vec()` |
| [`03-len.md`](./03-len.md) | `len()` |
| [`04-add.md`](./04-add.md) | `add()` |
| [`05-sub.md`](./05-sub.md) | `sub()` |
| [`06-dist.md`](./06-dist.md) | `dist()` |
| [`07-scale.md`](./07-scale.md) | `scale()` |
| [`08-div.md`](./08-div.md) | `div()` |
| [`09-neg.md`](./09-neg.md) | `neg()` |
| [`10-norm.md`](./10-norm.md) | `norm()` |
| [`11-element-product.md`](./11-element-product.md) | `element-product()` |
| [`12-dot.md`](./12-dot.md) | `dot()` |
| [`13-cross.md`](./13-cross.md) | `cross()` |
| [`14-angle2.md`](./14-angle2.md) | `angle2()` |
| [`15-angle.md`](./15-angle.md) | `angle()` |
| [`16-lerp.md`](./16-lerp.md) | `lerp()` |

## Related

- [`internals/matrix`](../matrix/00-matrix-overview.md) — 4×4 affine
  transforms; `as-mat` lifts a vector into matrix form
- [`internals/coordinate`](../coordinate/00-coordinate-overview.md) —
  user-facing coordinates resolve into vectors via `coordinate.resolve`
- [Types — `vector`](../../../types/00-types-overview.md)
