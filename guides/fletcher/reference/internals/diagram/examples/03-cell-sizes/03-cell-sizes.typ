// Internals/diagram 03 — UML-flavoured class hierarchy. Cells inherit
// the width of the *widest* member (`AbstractFactory`), so the column
// stretches automatically — that's what `compute-cell-sizes` does.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  axes: (ltr, btt),
  spacing: (10mm, 12mm),
  node-stroke: 0.6pt,
  node-corner-radius: 2pt,
  node((1, 2), [Object], fill: gray.lighten(80%)),
  node((1, 1), [AbstractFactory]),
  node((0, 0), [LoggerFactory]),
  node((1, 0), [DBConnectionFactory]),
  node((2, 0), [HTTPClientFactory]),
  edge((1, 1), (1, 2), "-|>"),
  edge((0, 0), (1, 1), "-|>"),
  edge((1, 0), (1, 1), "-|>"),
  edge((2, 0), (1, 1), "-|>"),
)
