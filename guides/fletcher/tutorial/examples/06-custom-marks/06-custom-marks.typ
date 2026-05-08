// Tutorial 06 — custom marks: minimal + parametric + inheriting.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#import fletcher.cetz.draw
#set page(width: auto, height: auto, margin: 6pt)

#let circle-mark = (
  draw: draw.circle((0, 0), radius: 2, fill: none),
)

#diagram(
  edge((0, 0), (1, 0), stroke: 1pt, marks: (circle-mark, circle-mark), bend: 30deg),
  edge((0, 1), (1, 1), stroke: 3pt + orange, marks: (none, circle-mark)),
)

#v(0.6em)

#let sized-mark = (
  size: 2,
  draw: mark => draw.circle((0, 0), radius: mark.size, fill: none),
)

#diagram(edge((0,0), (1,0), stroke: 3pt,
  marks: (sized-mark + (size: 4), sized-mark)))

#v(0.6em)

#let red-stealth = (
  inherit: "stealth",
  fill: red,
  stroke: none,
)

#diagram(edge((0,0), (1,0), "rr", stroke: 2pt,
  marks: (red-stealth, red-stealth + (fill: blue))))
