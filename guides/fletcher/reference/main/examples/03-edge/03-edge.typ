// Reference 03 — edge() variants: arc, poly with corner, label.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (12mm, 6mm),
  node((0, 0), $A$),
  node((1, 0), $B$),
  edge((0, 0), (1, 0), "<-<<", bend: -25deg, $f$),
  node((-1, -1), $0$),
  edge((-1, -1), (0, 0), "..|>", corner: right, $g$),
)
