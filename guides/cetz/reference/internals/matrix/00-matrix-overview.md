# `matrix` — Affine-Matrix Math

`cetz.matrix` provides everything CeTZ needs to compose 4×4 transformation
matrices. A *matrix* is a Typst array of arrays — a list of rows, each row
a list of column entries.

The module is exposed at `cetz.matrix.<fn>`.

## Builders

| File | Function |
| --- | --- |
| [`01-ident.md`](./01-ident.md) | `ident()` |
| [`02-diag.md`](./02-diag.md) | `diag()` |
| [`03-dim.md`](./03-dim.md) | `dim()` |
| [`04-column.md`](./04-column.md) | `column()` |
| [`05-round.md`](./05-round.md) | `round()` |

## Affine Transforms (4×4)

| File | Function |
| --- | --- |
| [`06-transform-translate.md`](./06-transform-translate.md) | `transform-translate()` |
| [`07-transform-shear-x.md`](./07-transform-shear-x.md) | `transform-shear-x()` |
| [`08-transform-shear-z.md`](./08-transform-shear-z.md) | `transform-shear-z()` |
| [`09-transform-scale.md`](./09-transform-scale.md) | `transform-scale()` |
| [`10-transform-rotate-dir.md`](./10-transform-rotate-dir.md) | `transform-rotate-dir()` |
| [`11-transform-rotate-x.md`](./11-transform-rotate-x.md) | `transform-rotate-x()` |
| [`12-transform-rotate-y.md`](./12-transform-rotate-y.md) | `transform-rotate-y()` |
| [`13-transform-rotate-z.md`](./13-transform-rotate-z.md) | `transform-rotate-z()` |
| [`14-transform-rotate-aer.md`](./14-transform-rotate-aer.md) | `transform-rotate-aer()` |
| [`15-transform-rotate-xz.md`](./15-transform-rotate-xz.md) | `transform-rotate-xz()` |
| [`16-transform-rotate-ypr.md`](./16-transform-rotate-ypr.md) | `transform-rotate-ypr()` |
| [`17-transform-rotate-xyz.md`](./17-transform-rotate-xyz.md) | `transform-rotate-xyz()` |

## Operations

| File | Function |
| --- | --- |
| [`18-mul-mat.md`](./18-mul-mat.md) | `mul-mat()` |
| [`19-mul4x4-vec3.md`](./19-mul4x4-vec3.md) | `mul4x4-vec3()` |
| [`20-mul-vec.md`](./20-mul-vec.md) | `mul-vec()` |
| [`21-inverse.md`](./21-inverse.md) | `inverse()` |

## Related

- [`reference/transformation`](../../transformation/00-transformation-overview.md)
  — the user-facing transform shapes
  ([`rotate`](../../transformation/03-rotate.md),
  [`translate`](../../transformation/04-translate.md),
  [`scale`](../../transformation/05-scale.md),
  [`set-transform`](../../transformation/01-set-transform.md))
- [`reference/projection`](../../projection/00-projection-overview.md) —
  3-D projections built on these matrices
- [`internals/vector`](../vector/00-vector-overview.md) — vector math
  multiplied by these matrices
- [Types — `matrix`](../../../types/00-types-overview.md)
