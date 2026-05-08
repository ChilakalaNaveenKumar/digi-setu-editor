// Shapes 07 — diamond.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: diamond
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Choice], shape: diamond),
  node((1, 0), [Choice], shape: diamond.with(fit: 0)),
)
