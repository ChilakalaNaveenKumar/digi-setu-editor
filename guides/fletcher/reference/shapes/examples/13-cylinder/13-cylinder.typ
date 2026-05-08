// Shapes 13 — cylinder.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: cylinder
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [DB],   shape: cylinder),
  node((1, 0), [Stack], shape: cylinder.with(rings: (10%, 50%, 90%), tilt: 4deg)),
)
