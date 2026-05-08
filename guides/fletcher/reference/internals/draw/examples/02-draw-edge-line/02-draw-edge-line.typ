// Internals/draw 02 — straight edges with extrusion (parallel strokes)
// for tape and double-line styles, plus the debug grid overlay.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (22mm, 10mm),
  node-stroke: none,
  node((0, 0), $A$),
  node((1, 0), $B$),
  node((0, 1), $C$),
  node((1, 1), $D$),
  node((0, 2), $E$),
  node((1, 2), $F$),
  edge((0, 0), (1, 0), "->", stroke: 0.6pt),
  edge((0, 1), (1, 1), "->", extrude: (-2, 2),  stroke: 0.5pt),
  edge((0, 2), (1, 2), "->>", extrude: (-3, 0, 3), stroke: 0.5pt),
)
