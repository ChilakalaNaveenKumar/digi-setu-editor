// Shapes 03 — ellipse.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: ellipse
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [wide label], shape: ellipse),
  node((1, 0), [wide label], shape: ellipse.with(scale: 1.4)),
)
