// Shapes 02 — circle.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: circle
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), $A$, shape: circle),
  node((1, 0), [BIG],  shape: circle),
)
