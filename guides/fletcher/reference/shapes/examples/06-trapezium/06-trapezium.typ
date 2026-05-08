// Shapes 06 — trapezium.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: trapezium
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Funnel],     shape: trapezium.with(dir: bottom)),
  node((1, 0), [Spread Out], shape: trapezium.with(dir: top, angle: 30deg)),
)
