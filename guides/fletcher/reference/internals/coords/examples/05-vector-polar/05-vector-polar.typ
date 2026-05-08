// Internals/coords 05 — radial annotations of an MLP "neuron" using
// `vector-polar-with-xy-or-uv-length`. The black ticks are uv-anchored
// (length scales with the grid); the blue tick is fixed at 6pt no
// matter the grid spacing.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#set page(width: auto, height: auto, margin: 6pt)

#let inputs = (
  (-1, -1, $x_1$),
  (-1,  0, $x_2$),
  (-1,  1, $x_3$),
)

#diagram(
  spacing: (18mm, 12mm),
  node-stroke: 0.5pt,
  ..inputs.map(((u, v, lbl)) => fletcher.node((u, v), lbl,
    shape: fletcher.shapes.circle)),
  fletcher.node((0, 0), $sigma$, shape: fletcher.shapes.circle,
    fill: blue.lighten(80%)),
  fletcher.node((1, 0), $y$, shape: fletcher.shapes.circle),
  ..inputs.map(((u, v, _)) => fletcher.edge((u, v), (0, 0), "->")),
  fletcher.edge((0, 0), (1, 0), "->"),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    let centre = fletcher.uv-to-xy(grid, (0, 0))
    for theta in (0deg, 60deg, 120deg, 180deg, 240deg, 300deg) {
      let off = fletcher.vector-polar-with-xy-or-uv-length(
        grid, centre, 0.55, theta)
      fletcher.cetz.draw.line(centre,
        (centre.at(0) + off.at(0), centre.at(1) + off.at(1)),
        stroke: 0.4pt + black.transparentize(50%))
    }
    let off = fletcher.vector-polar-with-xy-or-uv-length(
      grid, centre, 6pt, 90deg)
    fletcher.cetz.draw.line(centre,
      (centre.at(0) + off.at(0), centre.at(1) + off.at(1)),
      mark: (end: ">"), stroke: 0.8pt + blue)
  })
)
