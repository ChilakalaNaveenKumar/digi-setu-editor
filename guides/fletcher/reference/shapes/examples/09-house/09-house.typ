// Shapes 09 — house.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: house
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Roof], shape: house),
  node((1, 0), [Tall roof], shape: house.with(angle: 30deg)),
)
