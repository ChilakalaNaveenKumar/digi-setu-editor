// Gallery 06 — Hasse diagram of the divisors of 60 ordered by divisibility.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

// (label, x, y, [divisors at the next-lower level])
#let lattice = (
  (60, 2,   4),
  (30, 1,   3),
  (20, 3,   3),
  (12, 5,   3),
  (15, 0.5, 2),
  (10, 1.5, 2),
  ( 6, 2.5, 2),
  ( 4, 4.5, 2),
  ( 5, 0,   1),
  ( 3, 1.5, 1),
  ( 2, 3.5, 1),
  ( 1, 2,   0),
)

#let edges = (
  (60, 30), (60, 20), (60, 12),
  (30, 15), (30, 10), (30,  6),
  (20, 10), (20,  4),
  (12,  6), (12,  4),
  (15,  5), (15,  3),
  (10,  5), (10,  2),
  ( 6,  3), ( 6,  2),
  ( 4,  2),
  ( 5,  1), ( 3,  1), ( 2,  1),
)

#diagram(
  axes: (ltr, btt),
  spacing: (8mm, 12mm),
  node-stroke: none,
  ..lattice.map(((n, x, y)) =>
    fletcher.node((x, y), $#n$, name: label(str(n)))),
  ..edges.map(((a, b)) =>
    fletcher.edge(label(str(a)), label(str(b)), "-")),
)
