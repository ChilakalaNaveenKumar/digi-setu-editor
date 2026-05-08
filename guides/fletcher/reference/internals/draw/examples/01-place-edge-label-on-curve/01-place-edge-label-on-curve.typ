// Internals/draw 01 — labels at custom positions along arcs and a poly.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (24mm, 14mm),
  node-stroke: none,
  node((0, 0), $A$),
  node((1, 0), $B$),
  node((0, 1), $C$),
  node((1, 1), $D$),
  edge((0, 0), (1, 0), "->", $f$, label-pos: 0.2,  label-side: left),
  edge((0, 0), (0, 1), "->", $g$, label-pos: 0.5,  label-side: right),
  edge((0, 1), (1, 1), "->", $h$, label-pos: 0.8,  label-side: left),
  edge((0, 0), (1, 1), "->", $k$, label-pos: 0.35, bend: -25deg),
)
