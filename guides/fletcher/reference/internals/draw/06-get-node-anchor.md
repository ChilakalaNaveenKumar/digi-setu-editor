# `get-node-anchor(node, θ, callback)`

Return the point on a node's outline at angle `θ` (measured from the
node's centre, counter-clockwise from the positive x-axis), and pass
that point to `callback`.

This is the helper Fletcher uses to figure out *where* to attach an
arrow on a non-rectangular node — circles, diamonds, octagons, custom
shapes.

## Signature

```typst
get-node-anchor(
  node:     dict,             // node from the resolved nodes array
  θ:        angle,            // direction from centre
  callback: point -> any,
)
```

## Example — manual radial spokes

```typst
render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
  fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
  let n = fletcher.find-node-at(nodes, (0, 0))
  for theta in (0deg, 60deg, 120deg, 180deg, 240deg, 300deg) {
    fletcher.get-node-anchor(n, theta, p => {
      fletcher.cetz.draw.line(n.pos.xyz, p, stroke: 0.4pt + red)
    })
  }
})
```

See [`examples/06-get-node-anchor/06-get-node-anchor.typ`](examples/06-get-node-anchor/06-get-node-anchor.typ).

## Pitfalls

- Some node shapes have a non-trivial `outset:` — `get-node-anchor`
  honours it. If you draw your own outlines and they don't match the
  Fletcher anchor, double-check the node's `outset:` value.
- Result is callback-style; you cannot return the anchor point.

## Related

- [`find-farthest-intersection`](05-find-farthest-intersection.md)
- [`defocus-adjustment`](07-defocus-adjustment.md)
- [Tutorial: nodes (anchors)](../../../tutorial/03-nodes.md)
