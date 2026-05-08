// Shapes 11 — hexagon.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: hexagon
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Hex],   shape: hexagon),
  node((1, 0), [Wider], shape: hexagon.with(angle: 45deg)),
)
