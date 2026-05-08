// Internals/diagram 01 — Hasse diagram of the divisibility lattice on
// the divisors of 12. With `axes: (ltr, btt)` smaller numbers sit at
// the bottom and "divides" arrows go upward.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  axes: (ltr, btt),
  spacing: (12mm, 12mm),
  node-stroke: none,
  node((1, 0), $1$),
  node((0, 1), $2$),
  node((1, 1), $3$),
  node((0, 2), $4$),
  node((1, 2), $6$),
  node((0.5, 3), $12$),
  edge((1, 0), (0, 1), "-"),
  edge((1, 0), (1, 1), "-"),
  edge((0, 1), (0, 2), "-"),
  edge((0, 1), (1, 2), "-"),
  edge((1, 1), (1, 2), "-"),
  edge((0, 2), (0.5, 3), "-"),
  edge((1, 2), (0.5, 3), "-"),
)
