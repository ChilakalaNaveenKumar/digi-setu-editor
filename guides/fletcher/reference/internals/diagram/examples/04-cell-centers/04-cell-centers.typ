// Internals/diagram 04 — a NLP pipeline whose stages have very
// different label widths. The cell *centres* end up at uneven physical
// positions even though the elastic indices are 0, 1, 2, 3, 4, 5.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let stages = (
  (0, [Input\ text], white),
  (1, [Tokeniser], blue.lighten(80%)),
  (2, [Embeddings], blue.lighten(80%)),
  (3, [Transformer\ blocks $times N$], orange.lighten(75%)),
  (4, [LM head], blue.lighten(80%)),
  (5, [Sampled\ token], white),
)

#diagram(
  spacing: (8mm, 10mm),
  node-stroke: 0.6pt,
  node-corner-radius: 3pt,
  ..stages.map(((u, lbl, c)) =>
    fletcher.node((u, 0), align(center, lbl), fill: c, inset: 6pt)),
  ..stages.windows(2).map(((a, b)) =>
    fletcher.edge((a.at(0), 0), (b.at(0), 0), "->")),
)
