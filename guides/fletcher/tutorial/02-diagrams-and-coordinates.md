# 2 — Diagrams and coordinates

A `diagram(..)` lays its children out on a flexible coordinate grid.
Two coordinate systems coexist:

- **Elastic** (or `uv`) — *row/column* numbers like `(2, 1)`. Rows and
  columns auto-grow to fit the largest node placed in them, and the
  spacing between cells is set by `spacing:` on `diagram`.
- **Absolute** (or `xy`) — *physical* lengths like `(10mm, 5mm)`.
  Nodes at absolute coords are **floating** — they never affect layout.

A node placed at an elastic coord *grows* the grid; a node placed at an
absolute coord just sits there.

## Elastic coordinates

```typst
#diagram(
  debug: 1,
  node((0,0), [a]),
  node((1,0), [b]),
  node((1,1), [c]),
  node((0,2), [d]),
)
```

The grid has 2 columns and 3 rows; cell sizes adjust to the contents.

## Fractional elastic coordinates

```typst
#diagram(
  debug: 1,
  node((0,0), [a]),
  node((0.5, 1), [c]),  // splits its width across columns 0 and 1
)
```

A node at column `0.5` causes the layout to grow *both* columns 0 and 1
by half the node width — handy for centred labels.

## Absolute coordinates

```typst
#diagram(
  node((0, 0), [origin], stroke: 0.5pt),
  // 1cm to the right of origin, 5mm down — never affects grid
  node((rel: (1cm, 5mm), to: (0,0)), [floating]),
)
```

## CeTZ-style coordinate expressions

Fletcher accepts the same shorthands as CeTZ:

| Form | Meaning |
| ---- | ------- |
| `(rel: (du, dv), to: <name>)` | Relative offset from another point. |
| `(45deg, 1cm)` | Polar (angle, distance from origin). |
| `(<P>, 80%, <Q>)` | Linear interpolation between named points. |
| `(<X>, "\|-", <Y>)` | Perpendicular intersection. |

See [`examples/02-diagrams-and-coordinates/02-diagrams-and-coordinates.typ`](examples/02-diagrams-and-coordinates/02-diagrams-and-coordinates.typ).

## Choosing the axes

`diagram(axes: (ltr, ttb))` is the default — *u* increases →, *v*
increases ↓. Other useful options:

| `axes` | Effect |
| ------ | ------ |
| `(ltr, btt)` | *v* increases up the page (math convention). |
| `(ttb, ltr)` | Matrix-style: *u* is row, *v* is column. |

## Pitfalls

- A node at `(2, 1)` reserves a cell, growing the grid; a node at
  `(20mm, 10mm)` does **not**. Don't mix the two if you need
  predictable layout.
- `spacing:` and `cell-size:` can be a single length or a `(x, y)`
  pair. A bare length applies to *both* axes.
- Fractional coords (`0.5`) split width across two adjacent columns;
  if your grid looks "double wide" check for stray fractional indices.

## Next

[`03-nodes.md`](03-nodes.md) — node basics, shapes, anchors, groups.
