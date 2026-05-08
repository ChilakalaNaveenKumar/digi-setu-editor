#set page(width: 16cm, height: auto, margin: 8pt)

== A custom trapezoid

#polygon(
  fill: blue.lighten(80%),
  stroke: blue,
  (20pt, 0pt),
  (60pt, 0pt),
  (80pt, 50pt),
  (0pt, 50pt),
)

== Star with two fill rules

#let star = polygon.with(
  (25pt, 0pt),
  (10pt, 50pt),
  (50pt, 20pt),
  (0pt, 20pt),
  (40pt, 50pt),
)

#star(fill: red, fill-rule: "non-zero")
#h(8pt)
#star(fill: red, fill-rule: "even-odd")

== Regular polygons (triangle through hexagon)

#stack(
  dir: ltr, spacing: 8pt,
  ..for n in (3, 4, 5, 6) {
    (polygon.regular(
      size: 30pt, vertices: n,
      fill: aqua, stroke: 1pt + blue,
    ),)
  },
)

== Dot-marked outline

#polygon(
  stroke: 1.5pt + maroon,
  (0pt, 0pt), (40pt, 10pt), (60pt, 50pt), (10pt, 40pt),
)
