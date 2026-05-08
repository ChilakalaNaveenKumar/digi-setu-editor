// Gallery 01 — Commutative square, the "hello world" of category theory.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (20mm, 14mm),
  node-stroke: none,
  node((0, 0), $A$, name: <a>),
  node((1, 0), $B$, name: <b>),
  node((0, 1), $C$, name: <c>),
  node((1, 1), $D$, name: <d>),
  edge(<a>, <b>, "->", $f$),
  edge(<a>, <c>, "->", $g$, label-side: right),
  edge(<b>, <d>, "->", $h$),
  edge(<c>, <d>, "->", $k$, label-side: right),
  edge(<a>, <d>, "->", $g h$, bend: -25deg, label-side: left),
)
