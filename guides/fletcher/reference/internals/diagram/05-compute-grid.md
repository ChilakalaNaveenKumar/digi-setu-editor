# `compute-grid(rects, ..)` — top-level layout helper

The end-to-end function that turns measured rectangles into a usable
`grid` dictionary. Internally it chains
[`expand-fractional-rects`](02-expand-fractional-rects.md) →
[`compute-cell-sizes`](03-compute-cell-sizes.md) →
[`compute-cell-centers`](04-compute-cell-centers.md).

## Signature

```typst
compute-grid(
  rects:    array,
  axes:     (direction, direction),
  spacing:  (length, length),
  origin:   (length, length),
  flip:     (bool, bool),
) -> dict
```

The returned dictionary contains:

| Key | Description |
| --- | ----------- |
| `centers` | `(column-centers, row-centers)` arrays from `compute-cell-centers`. |
| `sizes`   | `(column-sizes, row-sizes)` arrays from `compute-cell-sizes`. |
| `spacing` | The same `spacing:` you passed in. |
| `origin`  | The grid's origin in CeTZ coordinates. |
| `axes`    | The normalised axes tuple. |
| `flip`    | Per-axis flip booleans. |

## Why you'd touch it

You replace `diagram(...)` with a custom pipeline (e.g. building two
linked diagrams that share a coordinate system). The grid you build is
what `uv-to-xy`, `xy-to-uv`, `find-node-at`, and the rest expect.

See [`examples/05-compute-grid/05-compute-grid.typ`](examples/05-compute-grid/05-compute-grid.typ)
for a "use the grid Fletcher hands you" demo via `render:`.

## Pitfalls

- The `flip` argument follows axis direction (`rtl`, `btt` set the
  corresponding flag). Mismatches between `axes:` and `flip:` produce
  upside-down diagrams.
- Fletcher does not memoise grid computation; if you call it many
  times keep the `rects` array minimal.

## Related

- All other diagram-internals pages.
- [`coords/`](../coords/00-coords-overview.md) for what to do with the
  resulting grid.
