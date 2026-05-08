// Internals/coords 03 — `duv-to-dxy` shows that "1 elastic step" is
// not a constant length. Above each cell of an inheritance diagram we
// draw a calibration arrow of *the same uv length* — visibly different
// in xy because each cell has a different label width.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (12mm, 14mm),
  node-stroke: 0.6pt,
  node((0, 1), [Object]),
  node((1, 1), [Iterable\<T\>]),
  node((2, 1), [Collection\<T\>]),
  node((3, 1), [List\<T\>]),
  edge((0, 1), (1, 1), "->"),
  edge((1, 1), (2, 1), "->"),
  edge((2, 1), (3, 1), "->"),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    for u in (0, 1, 2) {
      let p = fletcher.uv-to-xy(grid, (u + 0.5, 0.2))
      let dxy = fletcher.duv-to-dxy(grid, (u + 0.5, 0.2), (1, 0))
      let q = (p.at(0) + dxy.at(0), p.at(1) + dxy.at(1))
      fletcher.cetz.draw.line(p, q, mark: (end: ">"),
        stroke: 0.7pt + red.darken(15%))
    }
  })
)
