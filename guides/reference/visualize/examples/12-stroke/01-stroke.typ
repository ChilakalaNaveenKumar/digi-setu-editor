#set page(width: 16cm, height: auto, margin: 8pt)
#set line(length: 100%)

== Shorthand forms

#stack(
  spacing: 6pt,
  line(stroke: 2pt),                   // thickness only
  line(stroke: red),                   // color only
  line(stroke: 2pt + red),             // length + color
  line(stroke: stroke(thickness: 2pt, paint: red, cap: "round")),
)

== Caps

#stack(spacing: 6pt,
  line(stroke: (thickness: 6pt, paint: blue, cap: "butt")),
  line(stroke: (thickness: 6pt, paint: blue, cap: "round")),
  line(stroke: (thickness: 6pt, paint: blue, cap: "square")),
)

== Joins (miter / round / bevel)

#let zigzag = (
  curve.move((0pt, 30pt)),
  curve.line((20pt, 0pt)),
  curve.line((40pt, 30pt)),
  curve.line((60pt, 0pt)),
)

#stack(
  dir: ltr, spacing: 12pt,
  curve(stroke: 6pt + blue, ..zigzag),
  curve(stroke: (thickness: 6pt, paint: blue, join: "round"), ..zigzag),
  curve(stroke: (thickness: 6pt, paint: blue, join: "bevel"), ..zigzag),
)

== Miter limit (low → quickly bevels, high → keeps sharp)

#let spike = (
  curve.move((15pt, 0pt)),
  curve.line((0pt, 30pt)),
  curve.line((30pt, 30pt)),
  curve.line((10pt, 20pt)),
)

#stack(
  dir: ltr, spacing: 12pt,
  curve(stroke: (thickness: 6pt, paint: blue, miter-limit: 1), ..spike),
  curve(stroke: (thickness: 6pt, paint: blue, miter-limit: 4), ..spike),
  curve(stroke: (thickness: 6pt, paint: blue, miter-limit: 8), ..spike),
)

== Dash patterns

#stack(
  spacing: 6pt,
  line(stroke: (thickness: 2pt, dash: "dotted")),
  line(stroke: (thickness: 2pt, dash: "dashed")),
  line(stroke: (thickness: 2pt, dash: "dash-dotted")),
  line(stroke: (thickness: 2pt, dash: (10pt, 5pt, "dot", 5pt))),
  line(stroke: (thickness: 2pt,
                dash: (array: (10pt, 5pt, "dot", 5pt), phase: 10pt))),
)
