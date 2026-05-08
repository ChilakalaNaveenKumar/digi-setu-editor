// Internals/draw 04 — multi-segment "bus" connections with rounded
// corners; this is what `draw-edge-polyline` produces.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (16mm, 12mm),
  node-stroke: 0.5pt,
  node-corner-radius: 3pt,
  node((0, 0), [CPU]),
  node((3, 0), [RAM]),
  node((0, 2), [GPU]),
  node((3, 2), [SSD]),
  node((1.5, 1), [Bus controller]),
  edge((0, 0), "r,d,r", (3, 0), corner-radius: 4pt, "->"),
  edge((0, 2), "r,u,r", (3, 2), corner-radius: 4pt, "->"),
  edge((0, 0), "d,r", (1.5, 1), corner-radius: 3pt, "->"),
  edge((3, 0), "d,l", (1.5, 1), corner-radius: 3pt, "->"),
  edge((1.5, 1), "d,r", (3, 2), corner-radius: 3pt, "->"),
  edge((0, 2), "u,r", (1.5, 1), corner-radius: 3pt, "->"),
)
