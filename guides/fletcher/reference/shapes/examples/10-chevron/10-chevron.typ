// Shapes 10 — chevron.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: chevron
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  spacing: 5mm,
  node((0, 0), [Step 1], shape: chevron),
  node((1, 0), [Step 2], shape: chevron),
  node((2, 0), [Step 3], shape: chevron),
)
