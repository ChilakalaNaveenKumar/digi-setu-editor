# `expand-fractional-rects(rects)` — pin nodes to integer cells

A node placed at a *fractional* coordinate (e.g. `(0.5, 1)`) sits
between two rows / columns. Fletcher splits any such row/column into
two so every node ends up on an integer cell. `expand-fractional-rects`
performs that splitting for the layout pipeline.

## Signature

```typst
expand-fractional-rects(rects: array) -> array
```

`rects` is the per-node list produced by `measure-node-size`. The
return value is the same list with extra rectangles inserted to "fill"
the new fractional cells.

## Example

```typst
#diagram(
  spacing: 1cm,
  node((0, 0), [A]),
  node((0.5, 0), [Half]),
  node((1, 0), [B]),
)
// `expand-fractional-rects` is what makes `(0.5, 0)` work.
```

See [`examples/02-expand/02-expand.typ`](examples/02-expand/02-expand.typ).

## Pitfalls

- Heavy use of fractional coords causes Fletcher to insert many rows /
  columns, which can subtly change spacing — prefer integer coords
  when alignment matters.
- After expansion, the *index* of nodes changes; do not rely on raw
  positional indices when post-processing rects.

## Related

- [`compute-cell-sizes`](03-compute-cell-sizes.md) consumes the
  expanded rects.
- [`compute-grid`](05-compute-grid.md) calls expansion as part of its
  pipeline.
