// Internals/node 01 — a class-style box with mixed-size members. The
// columns/rows take their size from the widest/tallest member, which
// is exactly what `measure-node-size` reports for each node.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let cls(label, members) = align(left)[
  #strong[#label]
  #for m in members [
    \ - #raw(m)
  ]
]

#diagram(
  axes: (ltr, btt),
  spacing: (10mm, 12mm),
  node-stroke: 0.6pt,
  node-corner-radius: 3pt,
  node((0, 1), cls("Vehicle", ("wheels: int", "fuel: Fuel"))),
  node((0, 0), cls("Car", ("doors: int",))),
  node((1, 0), cls("Motorcycle", ("kickstand: bool", "engineSize: int"))),
  edge((0, 0), (0, 1), "-|>"),
  edge((1, 0), (0, 1), "-|>"),
)
