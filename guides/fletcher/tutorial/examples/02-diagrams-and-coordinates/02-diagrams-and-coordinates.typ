// Tutorial 02 — coordinate systems.
// Elastic, fractional, absolute, polar, interpolated.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  debug: 1,
  spacing: 10pt,
  node((0,0), [a]),
  node((1,0), [b]),
  node((1,1), [c]),
  node((0,2), [d]),
)

#v(0.6em)

#diagram(
  debug: 1,
  spacing: 10pt,
  node((0,0), [a]),
  node((0.5, 1), [c]),
)

#v(0.6em)

#diagram(
  node((0, 0), [origin], stroke: 0.5pt),
  node((rel: (1cm, 5mm), to: (0,0)), [floating], stroke: 0.5pt),
)
