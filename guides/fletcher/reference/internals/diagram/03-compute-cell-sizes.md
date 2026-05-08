# `compute-cell-sizes(rects, axes)` — per-row / per-column min sizes

After Fletcher knows every node's bounding rectangle, it must decide
how *wide* each column and how *tall* each row should be. That is
`compute-cell-sizes`.

## Signature

```typst
compute-cell-sizes(
  rects: array,                          // expanded node rects
  axes:  (direction, direction),         // normalised (h, v)
) -> (column-sizes: array, row-sizes: array)
```

The function takes the largest width per column and the largest height
per row, returning two parallel arrays.

## Example (showing the *effect* — labels make rows/columns grow)

```typst
#diagram(
  spacing: 1cm,
  node((0, 0), [A]),
  node((1, 0), [Wider node]),
  node((0, 1), [Taller\ box]),
  node((1, 1), [B]),
)
```

The second column is wider than the first, and the second row is
taller because of the explicit line break — that's `compute-cell-sizes`
in action.

See [`examples/03-cell-sizes/03-cell-sizes.typ`](examples/03-cell-sizes/03-cell-sizes.typ).

## Pitfalls

- Sizes do **not** include `spacing:` — that is added later by
  [`compute-cell-centers`](04-compute-cell-centers.md).
- Empty rows / columns get a min-size of `0pt`.

## Related

- [`compute-cell-centers`](04-compute-cell-centers.md)
- [`compute-grid`](05-compute-grid.md)
