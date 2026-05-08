// Demo 02 — Control-flow graph for `while (i < n) { if even(i) sum +=
// i; ++i; }` plus a side-by-side dominator tree.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 8pt)
#set text(10pt)

#let entry(uv, lbl) = fletcher.node(uv, align(left, lbl),
  shape: fletcher.shapes.rect, fill: blue.lighten(85%),
  stroke: 0.5pt, inset: 5pt, corner-radius: 2pt)

#let cond(uv, lbl) = fletcher.node(uv, lbl,
  shape: fletcher.shapes.diamond, fill: yellow.lighten(75%),
  stroke: 0.5pt, inset: 4pt)

= Control-flow graph

#diagram(
  spacing: (16mm, 8mm),
  entry((1, 0), [B0: `i = 0; sum = 0`]),
  cond((1, 1), [`i < n`]),
  cond((1, 2), [`even(i)`]),
  entry((0, 3), [B3: `sum += i`]),
  entry((1, 3), [B4: nop]),
  entry((1, 4), [B5: `++i`]),
  entry((1, 5), [exit]),
  edge((1, 0), (1, 1), "->"),
  edge((1, 1), (1, 2), "->", $T$),
  edge((1, 1), (1, 5), "->", $F$, bend: -45deg),
  edge((1, 2), (0, 3), "->", $T$, label-side: right),
  edge((1, 2), (1, 3), "->", $F$),
  edge((0, 3), (1, 4), "->"),
  edge((1, 3), (1, 4), "-"),
  edge((1, 4), (1, 5), "->"),
  edge((1, 5), (1, 1), "..>", $"back-edge"$, bend: 45deg),
)

#v(8pt)

= Dominator tree of the same graph

#diagram(
  axes: (ltr, btt),
  spacing: (12mm, 10mm),
  node-stroke: 0.5pt,
  node-corner-radius: 2pt,
  node((1, 5), [B0]),
  node((1, 4), [B1: `i<n`]),
  node((1, 3), [B2: `even(i)`]),
  node((0.4, 2), [B3]),
  node((1.6, 2), [B4]),
  node((1, 1), [B5]),
  node((1, 0), [B6: exit]),
  edge((1, 4), (1, 5), "-"),
  edge((1, 3), (1, 4), "-"),
  edge((0.4, 2), (1, 3), "-"),
  edge((1.6, 2), (1, 3), "-"),
  edge((1, 1), (1, 3), "-"),
  edge((1, 0), (1, 1), "-"),
)
