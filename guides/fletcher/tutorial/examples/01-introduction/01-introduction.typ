// Tutorial 01 — first Fletcher diagram.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node((0, 0), $A$),
  edge("->"),
  node((1, 0), $B$),
)
