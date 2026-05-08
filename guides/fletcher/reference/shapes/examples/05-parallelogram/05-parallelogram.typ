// Shapes 05 — parallelogram.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: parallelogram
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [In],  shape: parallelogram.with(angle: 30deg)),
  node((1, 0), [Out], shape: parallelogram.with(angle: 30deg, flip: true)),
)
