// Gallery 10 — Yoneda-style naturality square with curved labelled arrows.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (28mm, 18mm),
  node-stroke: none,
  node((0, 0), $"Hom"(A, X)$),
  node((1, 0), $"Hom"(A, Y)$),
  node((0, 1), $"Hom"(B, X)$),
  node((1, 1), $"Hom"(B, Y)$),
  edge((0, 0), (1, 0), "->", $f compose -$),
  edge((0, 1), (1, 1), "->", $f compose -$, label-side: right),
  edge((0, 0), (0, 1), "->", $- compose g$),
  edge((1, 0), (1, 1), "->", $- compose g$, label-side: right),
  edge((0, 0), (1, 1), "..>", $f compose - compose g$,
    bend: -25deg, label-side: left),
)
