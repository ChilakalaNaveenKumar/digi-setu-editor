// Shapes 08 — triangle.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: triangle
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Up],   shape: triangle.with(dir: top)),
  node((1, 0), [Down], shape: triangle.with(dir: bottom, angle: 90deg)),
)
