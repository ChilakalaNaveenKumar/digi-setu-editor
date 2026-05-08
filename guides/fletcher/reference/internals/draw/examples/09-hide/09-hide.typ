// Internals/draw 09 — same diagram twice: with B fully visible, then
// with B hidden via `fletcher.hide` (layout still reserves the space).

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

= Step 1 — full diagram

#diagram(
  spacing: (20mm, 0mm),
  node-stroke: 0.5pt,
  node((0, 0), [A]),
  node((1, 0), [B]),
  node((2, 0), [C]),
  edge((0, 0), (1, 0), "->"),
  edge((1, 0), (2, 0), "->"),
)

#v(8pt)

= Step 2 — same diagram, B and its arrows hidden, layout preserved

#diagram(
  spacing: (20mm, 0mm),
  node-stroke: 0.5pt,
  node((0, 0), [A]),
  fletcher.hide(node((1, 0), [B])),
  node((2, 0), [C]),
  fletcher.hide(edge((0, 0), (1, 0), "->")),
  fletcher.hide(edge((1, 0), (2, 0), "->")),
)
