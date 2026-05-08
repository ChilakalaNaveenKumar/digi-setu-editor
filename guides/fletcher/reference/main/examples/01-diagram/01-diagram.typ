// Reference 01 — diagram() with debug grid + custom defaults.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  debug: 1,
  spacing: (10mm, 5mm),
  node-stroke: 1pt,
  edge-stroke: 1pt,
  mark-scale: 60%,
  edge((-2, 0), "r,u,r", "-|>", $f$, label-side: left),
  edge((-2, 0), "r,d,r", "..|>", $g$),
  node((0, -1), $F(s)$),
  node((0, +1), $G(s)$),
)
