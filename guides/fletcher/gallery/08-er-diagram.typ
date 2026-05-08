// Gallery 08 — Entity-relationship diagram (Customer–Order–Product).

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#import fletcher.shapes: rect, diamond
#set page(width: auto, height: auto, margin: 6pt)

#let entity(uv, name) = fletcher.node(uv, name, shape: rect,
  stroke: 0.7pt, fill: blue.lighten(85%), inset: 6pt)

#let rel(uv, name) = fletcher.node(uv, name, shape: diamond,
  stroke: 0.7pt, fill: yellow.lighten(75%))

#let attr(uv, name) = fletcher.node(uv, text(8pt, name),
  shape: fletcher.shapes.ellipse, stroke: 0.4pt, inset: 3pt)

#diagram(
  spacing: (16mm, 11mm),
  entity((0, 1), [Customer]),
  entity((4, 1), [Product]),
  rel((2, 1), [orders]),
  attr((-1, 0), [name]),
  attr((-1, 2), [email]),
  attr((5, 0), [sku]),
  attr((5, 2), [price]),
  attr((1, 0), [date]),
  attr((3, 0), [qty]),
  edge((0, 1), (2, 1), "-", $1$),
  edge((4, 1), (2, 1), "-", $N$),
  edge((-1, 0), (0, 1), "-", stroke: 0.4pt),
  edge((-1, 2), (0, 1), "-", stroke: 0.4pt),
  edge((5, 0), (4, 1), "-", stroke: 0.4pt),
  edge((5, 2), (4, 1), "-", stroke: 0.4pt),
  edge((1, 0), (2, 1), "-", stroke: 0.4pt),
  edge((3, 0), (2, 1), "-", stroke: 0.4pt),
)
