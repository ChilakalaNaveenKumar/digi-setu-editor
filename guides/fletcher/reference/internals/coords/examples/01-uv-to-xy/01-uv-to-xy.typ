// Internals/coords 01 — `uv-to-xy` lets you draw extra CeTZ geometry on
// top of a Fletcher diagram, anchored to the elastic grid. Here a real
// commutative square gets a hand-drawn red diagonal "trace" linking the
// two opposite corners.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (18mm, 12mm),
  node-stroke: none,
  node((0, 0), $A$, name: <a>),
  node((1, 0), $B$, name: <b>),
  node((0, 1), $C$, name: <c>),
  node((1, 1), $D$, name: <d>),
  edge(<a>, <b>, "->", $f$),
  edge(<a>, <c>, "->", $g$, label-side: right),
  edge(<b>, <d>, "->", $h$),
  edge(<c>, <d>, "->", $k$, label-side: right),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    // Trace the diagonal of the square in elastic coords.
    let p1 = fletcher.uv-to-xy(grid, (0, 0))
    let p2 = fletcher.uv-to-xy(grid, (1, 1))
    fletcher.cetz.draw.line(p1, p2,
      stroke: 1pt + red.transparentize(40%))
  })
)
