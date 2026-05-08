// Gallery 04 — DFA recognising binary strings ending in `01`.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (22mm, 12mm),
  node-stroke: 0.7pt,
  node-corner-radius: 50%,
  node((-0.6, 0), [], stroke: none),
  node((0, 0), $q_0$, shape: fletcher.shapes.circle),
  node((1, 0), $q_1$, shape: fletcher.shapes.circle),
  node((2, 0), $q_2$, shape: fletcher.shapes.circle, extrude: (0, 3)),
  edge((-0.6, 0), (0, 0), "->"),
  edge((0, 0), (0, 0), "->", $0$, bend: 130deg),
  edge((0, 0), (1, 0), "->", $1$),
  edge((1, 0), (1, 0), "->", $1$, bend: 130deg),
  edge((1, 0), (0, 0), "->", $0$, bend: -50deg),
  edge((0, 0), (2, 0), "->", $0$, bend: 30deg),
  edge((2, 0), (1, 0), "->", $1$, bend: 30deg),
  edge((2, 0), (2, 0), "->", $0$, bend: 130deg),
)
