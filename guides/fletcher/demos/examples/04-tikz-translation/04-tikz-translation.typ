// Demo 04 — Translating canonical TikZ-cd diagrams into Fletcher.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 8pt)
#set text(11pt)

= Triangle (Snake)

#diagram(
  spacing: 16mm,
  node-stroke: none,
  node((0, 0), $A$),
  node((1, 0), $B$),
  node((2, 0), $C$),
  node((1, 1), $X$),
  edge((0, 0), (1, 0), "->", $f$),
  edge((1, 0), (2, 0), "->", $g$),
  edge((0, 0), (1, 1), "->", $h$, label-side: right),
  edge((1, 1), (2, 0), "->", $k$, label-side: right),
  edge((1, 0), (1, 1), "..>", $exists !$, label-side: left),
)

#v(8pt)

= Functor square

#diagram(
  spacing: (22mm, 14mm),
  node-stroke: none,
  node((0, 0), $C$),
  node((1, 0), $D$),
  node((0, 1), $C'$),
  node((1, 1), $D'$),
  edge((0, 0), (1, 0), "->", $F$),
  edge((0, 1), (1, 1), "->", $F'$, label-side: right),
  edge((0, 0), (0, 1), "->", $G$),
  edge((1, 0), (1, 1), "->", $H$, label-side: right),
  edge((0, 0), (1, 1), "=>", $alpha$,
    bend: -25deg, label-side: left),
)

#v(8pt)

= Adjunction $F tack.l G$

#diagram(
  spacing: (28mm, 0mm),
  node-stroke: none,
  node((0, 0), $cal(C)$),
  node((1, 0), $cal(D)$),
  edge((0, 0), (1, 0), "->", $F$, label-side: left, bend: 30deg),
  edge((1, 0), (0, 0), "->", $G$, label-side: left, bend: 30deg),
)
