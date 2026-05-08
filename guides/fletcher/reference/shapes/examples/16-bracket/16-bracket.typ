// Shapes 16 — bracket wrapper.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: bracket
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: 1cm,
  node-stroke: teal,
  node((0, 0), $A$, name: <A>),
  node((1, 0), $B$, name: <B>),
  node(enclose: (<A>, <B>),
    shape: bracket.with(dir: top)),
)
