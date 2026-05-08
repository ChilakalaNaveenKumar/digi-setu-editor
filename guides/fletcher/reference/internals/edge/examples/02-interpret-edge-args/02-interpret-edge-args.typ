// Internals/edge 02 — three calls to edge() that all produce the SAME
// arrow, demonstrating that `interpret-edge-args` rearranges any legal
// permutation of {marks, vertices, label}.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

// Style 1: marks at the end.
#diagram(
  spacing: (24mm, 6mm),
  node((0, 0), $A$, name: <a1>),
  node((1, 0), $B$, name: <b1>),
  edge(<a1>, <b1>, $f$, "->"),
)

#v(8pt)

// Style 2: marks in the middle.
#diagram(
  spacing: (24mm, 6mm),
  node((0, 0), $A$, name: <a2>),
  node((1, 0), $B$, name: <b2>),
  edge(<a2>, "->", <b2>, $f$),
)

#v(8pt)

// Style 3: marks first, then label, then vertices via keyword.
#diagram(
  spacing: (24mm, 6mm),
  node((0, 0), $A$, name: <a3>),
  node((1, 0), $B$, name: <b3>),
  edge(<a3>, <b3>, marks: "->", label: $f$),
)
