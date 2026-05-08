// Shapes 17 — paren wrapper.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: paren
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: 1cm,
  node-stroke: teal,
  node((0, 0), $A$, name: <A>),
  node((1, 0), $B$, name: <B>),
  node(enclose: (<A>, <B>),
    shape: paren.with(dir: top, label: [tuple])),
)
