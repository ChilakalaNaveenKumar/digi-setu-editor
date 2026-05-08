// Internals/node 02 — categorical "Subcategory of Set" diagram. The
// dashed enclosure groups the sub-objects, which is what
// `resolve-node-enclosures` resolves under the hood.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (16mm, 12mm),
  node-stroke: 0.6pt,
  node((0, 0), $emptyset$,    name: <0>),
  node((1, 0), $1$,           name: <1>),
  node((2, 0), $2$,           name: <2>),
  node((3, 0), $bb(N)$,       name: <N>),
  edge(<0>, <1>, "->"),
  edge(<1>, <2>, "->"),
  edge(<2>, <N>, "->"),
  node(enclose: (<1>, <2>),
    inset: 8pt,
    stroke: (paint: gray, dash: "dashed"),
    fill: gray.lighten(90%),
    label: text(7pt, gray.darken(20%))[finite]),
)
