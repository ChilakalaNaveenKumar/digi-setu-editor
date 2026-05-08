// Gallery 09 — State machine for an order's lifecycle, complete with
// loops and a "cancel from anywhere" branch.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let state(uv, lbl, ..rest) = fletcher.node(uv, lbl,
  shape: fletcher.shapes.pill, fill: blue.lighten(85%),
  stroke: 0.6pt, inset: 5pt, ..rest)

#diagram(
  spacing: (22mm, 12mm),
  state((-0.6, 0), [start], fill: white, stroke: none),
  state((0, 0), [Cart]),
  state((1, 0), [Awaiting\ payment]),
  state((2, 0), [Paid]),
  state((3, 0), [Shipped]),
  state((4, 0), [Delivered], fill: green.lighten(80%)),
  state((2, 1), [Cancelled], fill: red.lighten(80%)),
  edge((-0.6, 0), (0, 0), "->"),
  edge((0, 0), (1, 0), "->", $"checkout"$),
  edge((1, 0), (0, 0), "->", $"edit"$, bend: -40deg),
  edge((1, 0), (2, 0), "->", $"pay"$),
  edge((2, 0), (3, 0), "->", $"ship"$),
  edge((3, 0), (4, 0), "->", $"deliver"$),
  edge((0, 0), (2, 1), "..>", $"cancel"$, bend: 30deg, label-side: right),
  edge((1, 0), (2, 1), "..>"),
  edge((2, 0), (2, 1), "..>"),
)
