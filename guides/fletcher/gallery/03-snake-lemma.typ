// Gallery 03 — the snake lemma diagram (3 × 3 grid + serpentine arrow).

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (16mm, 14mm),
  node-stroke: none,
  // Top row: kernels.
  node((1, 0), $op("ker") f$),
  node((2, 0), $op("ker") g$),
  node((3, 0), $op("ker") h$),
  // Middle row: A → B → C → 0.
  node((0, 1), [ ]),
  node((1, 1), $A$),
  node((2, 1), $B$),
  node((3, 1), $C$),
  node((4, 1), $0$),
  // Lower row: 0 → A' → B' → C'.
  node((0, 2), $0$),
  node((1, 2), $A'$),
  node((2, 2), $B'$),
  node((3, 2), $C'$),
  node((4, 2), [ ]),
  // Bottom row: cokernels.
  node((1, 3), $op("coker") f$),
  node((2, 3), $op("coker") g$),
  node((3, 3), $op("coker") h$),
  // Vertical maps and rows.
  edge((1, 0), (1, 1), "->"),
  edge((2, 0), (2, 1), "->"),
  edge((3, 0), (3, 1), "->"),
  edge((1, 1), (2, 1), "->"),
  edge((2, 1), (3, 1), "->"),
  edge((3, 1), (4, 1), "->"),
  edge((0, 1), (1, 1), "->"),
  edge((1, 1), (1, 2), "->", $f$, label-side: left),
  edge((2, 1), (2, 2), "->", $g$, label-side: left),
  edge((3, 1), (3, 2), "->", $h$, label-side: left),
  edge((0, 2), (1, 2), "->"),
  edge((1, 2), (2, 2), "->"),
  edge((2, 2), (3, 2), "->"),
  edge((3, 2), (4, 2), "->"),
  edge((1, 2), (1, 3), "->"),
  edge((2, 2), (2, 3), "->"),
  edge((3, 2), (3, 3), "->"),
  // The connecting morphism — the "snake".
  edge((3, 0), "r,d,d,d,l,l,l,l,d", (1, 3), "..>",
    bend: 0deg, label: text(0.85em)[$delta$], label-pos: 0.5),
)
