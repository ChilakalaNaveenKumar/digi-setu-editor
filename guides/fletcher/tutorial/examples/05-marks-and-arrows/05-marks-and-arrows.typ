// Tutorial 05 — marks shorthand strings.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: 1cm,
  edge((0,0), (1,0), "->"),
  edge((0,1), (1,1), "=>"),
  edge((0,2), (1,2), "hook'-/->>"),
  edge((0,3), (1,3), "o..O"),
)
