// Internals/draw 03 — a bouquet of arcs from one root, all rendered by
// `draw-edge-arc` under the hood.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (24mm, 12mm),
  node-stroke: none,
  node((0, 1), $A$),
  node((2, 0), $B_1$),
  node((2, 1), $B_2$),
  node((2, 2), $B_3$),
  edge((0, 1), (2, 0), "->", $f_1$, bend: -25deg),
  edge((0, 1), (2, 1), "->", $f_2$),
  edge((0, 1), (2, 2), "->", $f_3$, bend: +25deg, label-side: right),
)
