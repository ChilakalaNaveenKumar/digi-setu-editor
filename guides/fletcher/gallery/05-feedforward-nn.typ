// Gallery 05 — fully-connected feed-forward neural network.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let layer(x, n, label-prefix, fill) = range(n).map(i =>
  fletcher.node((x, i), text(8pt, [#label-prefix#sub[#(i + 1)]]),
    shape: fletcher.shapes.circle, fill: fill, stroke: 0.5pt))

#let connect(n0, n1, x0, x1) = {
  let edges = ()
  for i in range(n0) {
    for j in range(n1) {
      edges.push(fletcher.edge((x0, i), (x1, j),
        stroke: 0.3pt + gray.darken(20%)))
    }
  }
  edges
}

#diagram(
  spacing: (22mm, 8mm),
  ..layer(0, 4, $x$, blue.lighten(85%)),
  ..layer(1, 5, $h$, orange.lighten(80%)),
  ..layer(2, 3, $y$, green.lighten(80%)),
  ..connect(4, 5, 0, 1),
  ..connect(5, 3, 1, 2),
)
