// Demo 01 — A short tour of common category-theory diagrams in
// Fletcher: identity, composition, isomorphism, and a 3-object cube.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 8pt)
#set text(11pt)

= Identity and composition

#diagram(
  spacing: 18mm,
  node-stroke: none,
  node((0, 0), $A$, name: <a>),
  node((1, 0), $B$, name: <b>),
  node((2, 0), $C$, name: <c>),
  edge(<a>, <b>, "->", $f$),
  edge(<b>, <c>, "->", $g$),
  edge(<a>, <c>, "->", $g compose f$, bend: -30deg),
  edge(<a>, <a>, "->", $id_A$, bend: 130deg),
  edge(<c>, <c>, "->", $id_C$, bend: 130deg),
)

#v(8pt)

= Isomorphism

#diagram(
  spacing: (24mm, 14mm),
  node-stroke: none,
  node((0, 0), $X$),
  node((1, 0), $Y$),
  edge((0, 0), (1, 0), "->", $f$, label-side: left),
  edge((1, 0), (0, 0), "->", $f^(-1)$, bend: -30deg, label-side: left),
)

#v(8pt)

= Cube of arrows

#diagram(
  spacing: (15mm, 12mm),
  node-stroke: none,
  node((0, 0), $A$, name: <A>),
  node((2, 0), $B$, name: <B>),
  node((0, 2), $C$, name: <C>),
  node((2, 2), $D$, name: <D>),
  node((1, -1), $A'$, name: <Ap>),
  node((3, -1), $B'$, name: <Bp>),
  node((1, 1),  $C'$, name: <Cp>),
  node((3, 1),  $D'$, name: <Dp>),
  edge(<A>, <B>, "->"),
  edge(<C>, <D>, "->"),
  edge(<A>, <C>, "->"),
  edge(<B>, <D>, "->"),
  edge(<Ap>, <Bp>, "->"),
  edge(<Cp>, <Dp>, "->"),
  edge(<Ap>, <Cp>, "->"),
  edge(<Bp>, <Dp>, "->"),
  edge(<A>, <Ap>, "->", stroke: (paint: gray, dash: "dashed")),
  edge(<B>, <Bp>, "->", stroke: (paint: gray, dash: "dashed")),
  edge(<C>, <Cp>, "->", stroke: (paint: gray, dash: "dashed")),
  edge(<D>, <Dp>, "->", stroke: (paint: gray, dash: "dashed")),
)
