# Diagram internals — overview

Helpers that build a Fletcher *grid* from raw `node` / `edge` arrays.
You only need these if you replace the layout pipeline (e.g. write a
custom `render:` callback that uses your own grid).

| Page | Function | Purpose |
| ---- | -------- | ------- |
| [`01-interpret-axes.md`](01-interpret-axes.md) | `interpret-axes(axes)` | Validate / normalise the `axes:` argument. |
| [`02-expand-fractional-rects.md`](02-expand-fractional-rects.md) | `expand-fractional-rects(rects)` | Resolve fractional-position rects so they sit on integer cells. |
| [`03-compute-cell-sizes.md`](03-compute-cell-sizes.md) | `compute-cell-sizes(rects, axes)` | Per-row / per-column min sizes from rectangles. |
| [`04-compute-cell-centers.md`](04-compute-cell-centers.md) | `compute-cell-centers(sizes, spacing)` | Convert sizes into row / column **center positions**. |
| [`05-compute-grid.md`](05-compute-grid.md) | `compute-grid(rects, ...)` | Top-level helper that runs the three above and returns a `grid` dict. |

## Typical use

```typst
let grid = fletcher.compute-grid(
  fletcher.measure-node-size.with(...).map(...),
  axes:    (ltr, btt),
  spacing: (1cm, 1cm),
)
```

Most users go through `diagram(...)` and never call these directly.

## Pitfalls

- `axes:` accepts standard `ltr`, `rtl`, `ttb`, `btt` directions.
  Crossed combinations (e.g. `ttb, btt`) raise an error in
  `interpret-axes`.
- `expand-fractional-rects` may insert *extra cells*; row / column
  numbers below it shift by one if you depend on indices.
