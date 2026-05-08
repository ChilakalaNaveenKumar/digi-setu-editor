// Shapes 12 — octagon.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: octagon
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [STOP],     shape: octagon),
  node((1, 0), [tiny cuts], shape: octagon.with(truncate: 0.1)),
  node((2, 0), [big cuts],  shape: octagon.with(truncate: 0.4)),
)
