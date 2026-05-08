// Shapes 01 — rect.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: rect
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Hello], shape: rect),
  node((1, 0), [World], shape: rect, corner-radius: 3pt),
)
