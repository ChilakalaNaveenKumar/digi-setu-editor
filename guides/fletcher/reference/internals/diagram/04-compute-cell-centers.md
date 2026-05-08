# `compute-cell-centers(sizes, spacing)` — cumulative cell positions

Convert a tuple of `(column-sizes, row-sizes)` plus `spacing:` into the
**center coordinate** of every column and row. Those centers are then
stored in `grid.centers`, ready for `uv-to-xy` conversions.

## Signature

```typst
compute-cell-centers(
  sizes:   (column-sizes: array, row-sizes: array),
  spacing: (length, length),
) -> (column-centers: array, row-centers: array)
```

## How it works

For columns: cumulatively add half the size, full spacing, half the
next size — etc. Same procedure for rows.

This is what makes elastic coordinates **non-linear**: a row with a
huge node pushes the next row down by `(half-size + spacing +
next-half-size)`, not by a fixed amount.

## Example

```typst
#diagram(
  spacing: 1.5cm,
  node((0, 0), [A]),
  node((1, 0), [Wide one]),
  node((2, 0), [B]),
  node((3, 0), [Even wider]),
)
```

Each adjacent pair sits at a different physical distance.

See [`examples/04-cell-centers/04-cell-centers.typ`](examples/04-cell-centers/04-cell-centers.typ).

## Pitfalls

- `spacing:` is **gap between** cell edges, not centre-to-centre — to
  reason about distances use the centers array directly.
- The first center is at `size / 2`, *not* zero.

## Related

- [`compute-cell-sizes`](03-compute-cell-sizes.md)
- [`compute-grid`](05-compute-grid.md)
- [`uv-to-xy`](../coords/01-uv-to-xy.md)
