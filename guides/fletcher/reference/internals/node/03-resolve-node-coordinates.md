# `resolve-node-coordinates(node, grid)` — canonical (uv, xyz) coords

Convert the user-supplied position of a node into Fletcher's canonical
form, exposing both **`pos.uv`** (elastic) and **`pos.xyz`** (absolute,
3-component) on the node dict.

## Signature

```typst
resolve-node-coordinates(
  node: dict,
  grid: dict,
) -> dict     // node with `pos.uv` and `pos.xyz` filled in
```

## What gets converted

`node((1, 0), …)` is `uv` by default — `resolve-node-coordinates`
fills in `pos.xyz` via [`uv-to-xy`](../coords/01-uv-to-xy.md).

If the user passed an absolute coordinate, the helper inversely fills
in `pos.uv` via [`xy-to-uv`](../coords/02-xy-to-uv.md). Either way,
both representations end up on the node and downstream helpers (edge
routing, anchors, etc.) can pick whichever they need.

## Example (inside `render:`)

```typst
#diagram(
  node((0, 0), [A]),
  node((1.5, 0), [Mid]),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    for n in nodes {
      let xyz = n.pos.xyz
      fletcher.cetz.draw.circle((xyz.at(0), xyz.at(1)), radius: 1pt, fill: red)
    }
  })
)
```

See [`examples/03-resolve-coordinates/03-resolve-coordinates.typ`](examples/03-resolve-coordinates/03-resolve-coordinates.typ).

## Pitfalls

- `pos.xyz` is a **3-component** vector (`x, y, z`). Slice off the
  first two when handing the value to a 2-D CeTZ primitive.
- The helper expects an already-`compute-grid`-derived `grid`. Calling
  it with a stale grid leads to drift between `uv` and `xyz`.

## Related

- [`uv-to-xy`](../coords/01-uv-to-xy.md), [`xy-to-uv`](../coords/02-xy-to-uv.md)
- [`measure-node-size`](01-measure-node-size.md)
