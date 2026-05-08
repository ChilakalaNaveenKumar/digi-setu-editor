// Reference 02 — node() with enclose and named anchors.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node-stroke: 1pt,
  node((0, 0), name: <A>)[$A$],
  node((1, 0), name: <B>)[$B$],
  node(text(white)[$Sigma$], enclose: (<A>, <B>),
    fill: black, layer: -1),
  edge(<A>, <B>, "->"),
)
