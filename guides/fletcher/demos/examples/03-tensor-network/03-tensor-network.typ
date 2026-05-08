// Demo 03 — Penrose-style tensor network with shared indices.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 8pt)

#let tensor(uv, name, fill) = fletcher.node(uv, $#name$,
  shape: fletcher.shapes.rect, fill: fill, stroke: 0.6pt,
  inset: 6pt, corner-radius: 2pt, name: label(str(name)))

= MPS-like contraction $A^i_j B^j_k C^k$

#diagram(
  spacing: (20mm, 14mm),
  tensor((0, 0), "A", red.lighten(80%)),
  tensor((1, 0), "B", green.lighten(80%)),
  tensor((2, 0), "C", blue.lighten(80%)),
  // Open indices.
  edge((0, -0.7), <A>, "-", $i$, label-pos: 0.2),
  edge((2, -0.7), <C>, "-", $k$, label-pos: 0.2),
  // Contracted bond indices.
  edge(<A>, <B>, "-", $j$),
  edge(<B>, <C>, "-", $k'$),
  // Bottom labels.
  edge(<A>, (0, 0.7), "-", text(7pt, gray)[#sym.dots], stroke: none),
)

#v(10pt)

= A 4-leg tensor with one contracted leg

#diagram(
  spacing: 16mm,
  tensor((0, 0), "T", purple.lighten(80%)),
  edge((0, 0), (0, -0.8), "-", $a$),
  edge((0, 0), (-0.8, 0), "-", $b$),
  edge((0, 0), (0.8, 0), "-", $c$),
  edge((0, 0), (0, 0.8), "-", $d$),
)
