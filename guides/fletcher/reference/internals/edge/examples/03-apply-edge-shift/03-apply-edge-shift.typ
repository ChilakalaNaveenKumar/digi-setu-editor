// Internals/edge 03 — three parallel morphisms between A and B,
// kept apart by `shift:`. This is the natural place this internal
// helper runs in production.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (28mm, 12mm),
  node-stroke: none,
  node((0, 0), $A$),
  node((1, 0), $B$),
  edge((0, 0), (1, 0), "->", $f$, shift: -6pt),
  edge((0, 0), (1, 0), "->", $g$),
  edge((0, 0), (1, 0), "->", $h$, shift: +6pt),
)
