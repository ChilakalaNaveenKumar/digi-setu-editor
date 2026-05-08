# 7 — CeTZ integration

Fletcher's drawing primitives are deliberately small. For anything
more elaborate (Bézier edges, custom decorations, hand-drawn shapes),
the `render:` option of `diagram()` exposes the layout data so you can
draw with **CeTZ directly**.

## The `render:` callback

`render: (grid, nodes, edges, options) => content`. Default:

```typst
(grid, nodes, edges, options) => {
  cetz.canvas(fletcher.draw-diagram(grid, nodes, edges, debug: options.debug))
}
```

The four arguments give you everything Fletcher knows about:

- `grid` — `(origin, centers, spacing, flip)` describing row/column geometry.
- `nodes` — array of node dictionaries with computed `pos` and `size`.
- `edges` — array of edge dictionaries with computed vertices and styles.
- `options` — circuit-wide knobs (`debug`, etc.).

## A custom Bézier edge

```typst
#diagram(
  node((0, 1), $A$, stroke: 1pt, shape: fletcher.shapes.diamond),
  node((2, 0), [Bezier], fill: purple.lighten(80%)),
  render: (grid, nodes, edges, options) => {
    fletcher.cetz.canvas({
      fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
      let n1 = fletcher.find-node-at(nodes, (0, 1))
      let n2 = fletcher.find-node-at(nodes, (2, 0))
      let out-angle = 45deg
      let in-angle = -110deg
      fletcher.get-node-anchor(n1, out-angle, p1 => {
        fletcher.get-node-anchor(n2, in-angle, p2 => {
          let c1 = (to: p1, rel: (out-angle, 10mm))
          let c2 = (to: p2, rel: (in-angle, 20mm))
          fletcher.cetz.draw.bezier(p1, p2, c1, c2,
            mark: (end: ">"))
        })
      })
    })
  },
)
```

What's happening:

1. `fletcher.draw-diagram(...)` reuses Fletcher's default rendering for
   the nodes (and any non-Bézier edges).
2. `find-node-at(nodes, coord)` looks up the node dictionary.
3. `get-node-anchor(node, angle, callback)` calls the callback with
   the boundary point at the requested angle.
4. `cetz.draw.bezier(p1, p2, c1, c2, mark: ...)` draws the curve
   directly with CeTZ.

See [`examples/07-cetz-integration/07-cetz-integration.typ`](examples/07-cetz-integration/07-cetz-integration.typ).

## Pitfalls

- `cetz` is exported as `fletcher.cetz`; the `cetz.draw` submodule is
  `fletcher.cetz.draw`. Importing `cetz` separately is also fine but
  Fletcher already pulls a pinned version.
- Anchor callbacks (`get-node-anchor`) are *callbacks* — they pass
  the resolved point to a closure rather than returning it directly,
  because the point may depend on the still-active CeTZ canvas state.
- `render:` overrides the *entire* drawing — you'll usually want to
  call `fletcher.draw-diagram(...)` first to keep the default output,
  then add your own shapes on top.

## Next

[`08-touying.md`](08-touying.md) — incremental reveals for slides.
