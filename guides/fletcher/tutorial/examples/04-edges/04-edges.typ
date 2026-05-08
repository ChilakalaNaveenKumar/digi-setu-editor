// Tutorial 04 — edges: vertices, types, labels.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  edge((0,0), (1,1), "->", `line`),
  edge((2,0), (3,1), "->", bend: -30deg, `arc`),
  edge((4,0), (4,1), (5,1), (6,0), "->", `poly`),
)

#v(0.6em)

#diagram(
  node((0,0), $A$),
  edge("->", $f$, label-pos: 0.25),
  node((2,0), $B$),
)

#v(0.6em)

#diagram(
  node((0,0), $A$, name: <a>),
  node((1,1), $B$, name: <b>),
  edge(<a>, <b>, "->", snap-to: (<a>, none)),
)
