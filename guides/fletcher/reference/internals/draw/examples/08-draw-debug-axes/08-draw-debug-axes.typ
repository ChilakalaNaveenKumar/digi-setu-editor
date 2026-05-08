// Internals/draw 08 — same diagram with debug levels 0, 1, 2.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let demo(d) = diagram(
  debug: d,
  spacing: (16mm, 12mm),
  node-stroke: none,
  node((0, 0), $A$),
  node((1, 0), $B$),
  node((0, 1), $C$),
  node((1, 1), $D$),
  edge((0, 0), (1, 0), "->", $f$),
  edge((0, 0), (0, 1), "->", $g$, label-side: right),
  edge((0, 1), (1, 1), "->", $k$, label-side: right),
  edge((1, 0), (1, 1), "->", $h$),
)

= debug: 0

#demo(0)

#v(8pt)

= debug: 1

#demo(1)

#v(8pt)

= debug: 2

#demo(2)
