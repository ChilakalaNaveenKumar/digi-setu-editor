# `diagram()` — the envelope

Top-level constructor. Sets the layout grid and provides defaults for
all the `node()` and `edge()` calls inside.

## Signature

```typst
diagram(
  debug:              bool | 1 | 2 | 3 = false,
  axes:               (direction, direction) = (ltr, ttb),
  spacing:            length | (length, length) = 3em,
  cell-size:          length | (length, length) = 0pt,
  edge-stroke:        stroke = 0.048em,
  node-stroke:        stroke | none = none,
  edge-corner-radius: length | none = 2.5pt,
  node-corner-radius: length | none = none,
  node-inset:         length | (length, length) = 6pt,
  node-outset:        length | (length, length) = 0pt,
  node-shape:         rect | circle | function = auto,
  node-fill:          paint = none,
  node-defocus:       number = 0.2,
  label-sep:          length = 0.4em,
  label-size:         length = 1em,
  label-wrapper:      function = (default boxed wrapper),
  mark-scale:         percent = 100%,
  crossing-fill:      paint = white,
  crossing-thickness: number = 5,
  render:             function = (default cetz canvas),
  ..args:             any,
)
```

## Key options at a glance

| Option | What it controls |
| ------ | ---------------- |
| `debug` | `1` = grid lines, `2` = bounding boxes, `3` = anchors. |
| `axes` | Direction of `u` and `v`. `(ltr, btt)` flips y, `(ttb, ltr)` matrix-style. |
| `spacing` | Min gap between adjacent cell *contents* (not centres). |
| `cell-size` | Min row / column size, even if the cell is empty. |
| `edge-stroke` / `node-stroke` | Defaults for `edge(stroke:)` / `node(stroke:)`. Folded with per-element overrides. |
| `node-shape` / `node-fill` / `node-inset` / `node-outset` | Per-node defaults. |
| `node-defocus` | Edge-attachment offset for non-square nodes. `0` disables. |
| `label-*` | Defaults forwarded to `edge(label-*: ...)`. |
| `mark-scale` | Multiplier for arrow size relative to stroke thickness. |
| `crossing-fill` / `crossing-thickness` | Backdrop for `edge(.., crossing: true)`. |
| `render` | `(grid, nodes, edges, options) => content` — full custom canvas. |

## Examples

```typst
#diagram(
  debug: 1,
  spacing: (10mm, 5mm),
  node-stroke: 1pt,
  edge-stroke: 1pt,
  mark-scale: 60%,
  edge((-2, 0), "r,u,r", "-|>", $f$, label-side: left),
  edge((-2, 0), "r,d,r", "..|>", $g$),
  node((0, -1), $F(s)$),
  node((0, +1), $G(s)$),
)
```

See [`examples/01-diagram/01-diagram.typ`](examples/01-diagram/01-diagram.typ).

## Pitfalls

- `node-stroke: 1pt` *folds* with per-node `stroke: red`, giving
  `1pt + red`. To override entirely, set `node(stroke: 1pt + red)`.
- `spacing` is the gap between *bounding boxes*, not centres. Tall
  nodes give wider visual spacing.
- `axes: (ttb, ltr)` swaps the meaning of `(u, v)` to *(row, column)*.
  This is the matrix convention.

## Related

- Nodes: [`02-node.md`](02-node.md)
- Edges: [`03-edge.md`](03-edge.md)
- Shapes: [`reference/shapes/`](../shapes/00-shapes-overview.md)
