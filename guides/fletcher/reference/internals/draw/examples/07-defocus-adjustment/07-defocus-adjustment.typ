// Internals/draw 07 — three arrows into one wide node, contrasting
// `defocus: 0` (all arrows at centre) with `defocus: 1` (spread out).

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

= No defocus

#diagram(
  spacing: (24mm, 7mm),
  node-stroke: 0.5pt,
  node((0, 0), $A$),
  node((0, 1), $B$),
  node((0, 2), $C$),
  node((1, 1), [Wide processing node],
    width: 40mm, height: 12mm, defocus: 0),
  edge((0, 0), (1, 1), "->"),
  edge((0, 1), (1, 1), "->"),
  edge((0, 2), (1, 1), "->"),
)

#v(8pt)

= With defocus = 1

#diagram(
  spacing: (24mm, 7mm),
  node-stroke: 0.5pt,
  node((0, 0), $A$),
  node((0, 1), $B$),
  node((0, 2), $C$),
  node((1, 1), [Wide processing node],
    width: 40mm, height: 12mm, defocus: 1),
  edge((0, 0), (1, 1), "->"),
  edge((0, 1), (1, 1), "->"),
  edge((0, 2), (1, 1), "->"),
)
