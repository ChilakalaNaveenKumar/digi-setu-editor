# Drawing internals — overview

Helpers that turn a fully-resolved edge dictionary into actual CeTZ
draw commands. You almost never call these directly — you reach for
them when:

- you write a custom `edge` shape (e.g. a Bezier or spline edge);
- you need to anchor an external CeTZ overlay onto a node's outline;
- you debug edge routing.

| Page | Function | Purpose |
| ---- | -------- | ------- |
| [`01-place-edge-label-on-curve.md`](01-place-edge-label-on-curve.md) | `place-edge-label-on-curve(edge, curve, debug)` | Drop an edge label on a parametric curve, respecting `label-pos` / `label-side`. |
| [`02-draw-edge-line.md`](02-draw-edge-line.md) | `draw-edge-line(edge, debug)` | Render a straight-line edge: stroke, marks, label. |
| [`03-draw-edge-arc.md`](03-draw-edge-arc.md) | `draw-edge-arc(edge, debug)` | Render a `bend:` arc edge. |
| [`04-draw-edge-polyline.md`](04-draw-edge-polyline.md) | `draw-edge-polyline(edge, debug)` | Render a multi-segment edge with optional `corner-radius`. |
| [`05-find-farthest-intersection.md`](05-find-farthest-intersection.md) | `find-farthest-intersection(objects, target, callback)` | Pick the intersection point of a CeTZ object farthest from a target. |
| [`06-get-node-anchor.md`](06-get-node-anchor.md) | `get-node-anchor(node, θ, callback)` | Compute the point on a node's outline at angle θ. |
| [`07-defocus-adjustment.md`](07-defocus-adjustment.md) | `defocus-adjustment(node, θ)` | Spread out connection points on long/wide nodes. |
| [`08-draw-debug-axes.md`](08-draw-debug-axes.md) | `draw-debug-axes(grid, debug, floating)` | Draw the elastic-grid axes (the `debug:` overlay). |
| [`09-hide.md`](09-hide.md) | `hide(objects, bounds)` | Mark diagram contents invisible while keeping (or dropping) layout space. |

## Common pattern: render a custom edge

```typst
#diagram(
  ...
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    // …additional draw calls anchored via get-node-anchor /
    // find-farthest-intersection / uv-to-xy.
  }),
)
```

## Pitfalls

- All these helpers run **after** layout — you only have access to
  them inside a `render:` callback, where `grid` and the resolved
  `nodes` array are available.
- `find-farthest-intersection` calls back synchronously even when
  there is no intersection — guard your callback or rely on the
  `target` fallback.
