// Shapes 04 — pill.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: pill
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), [Status: OK], shape: pill, fill: green.lighten(80%)),
)
