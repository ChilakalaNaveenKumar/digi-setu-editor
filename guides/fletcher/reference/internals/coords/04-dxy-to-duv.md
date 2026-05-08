# `dxy-to-duv(grid, xy, dxy)` — xy tangent → uv tangent

Inverse of [`duv-to-dxy`](03-duv-to-dxy.md). Given a small physical
displacement `dxy` at point `xy`, return the equivalent displacement in
elastic uv space.

## Signature

```typst
dxy-to-duv(
  grid: dict,
  xy:   (length, length),  // base point in xy
  dxy:  (length, length),  // displacement in xy
) -> (float, float)
```

## When you need it

Snap a physical drawing tool back to the elastic grid:

```typst
let nearest-cell = fletcher.xy-to-uv(grid, (5pt, 4pt))
let cursor       = fletcher.dxy-to-duv(grid, (5pt, 4pt), (1mm, 0mm))
// `cursor` is in uv units, ready to compose with elastic positions
```

See [`examples/04-dxy-to-duv/04-dxy-to-duv.typ`](examples/04-dxy-to-duv/04-dxy-to-duv.typ).

## Pitfalls

- Same finite-difference caveat as `duv-to-dxy` — keep `dxy` small.
- The result is unitless (it's a delta in row/column index space).

## Related

- Forward: [`duv-to-dxy`](03-duv-to-dxy.md)
- Point inverse: [`xy-to-uv`](02-xy-to-uv.md)
