# Node internals — overview

Helpers around the **node** lifecycle: measuring its size on the
elastic grid, resolving multi-coordinate "enclosure" lists, and
turning user coordinates into the canonical `(uv, xy)` form.

| Page | Function | Purpose |
| ---- | -------- | ------- |
| [`01-measure-node-size.md`](01-measure-node-size.md) | `measure-node-size(node, styles)` | Measure a node's body and return a rect for the layout pass. |
| [`02-resolve-node-enclosures.md`](02-resolve-node-enclosures.md) | `resolve-node-enclosures(nodes, grid)` | Expand `enclose:` lists into final coordinate sets. |
| [`03-resolve-node-coordinates.md`](03-resolve-node-coordinates.md) | `resolve-node-coordinates(node, grid)` | Convert user coords (`uv`, `xy`, polar, …) into `(uv, xy)`. |

## When you'd reach for these

- Authoring a custom `shape:` that needs to know the final node size
  before drawing.
- Building a *post-processing* layer that draws decorations on top of
  Fletcher's diagram and needs each node's resolved position.

## Pitfalls

- These helpers expect a complete `grid` dict — call them from inside
  a `render:` callback or after running `compute-grid` manually.
- `measure-node-size` requires a `styles` value; obtain it via
  `style(...)` or `context`.
