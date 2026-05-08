#set page(width: 16cm, height: auto, margin: 8pt)

== Lines and a closed shape

#curve(
  fill: aqua.lighten(60%),
  stroke: 1.5pt + blue,
  curve.move((0pt, 40pt)),
  curve.line((40pt, 40pt)),
  curve.line((40pt, 0pt)),
  curve.line((0pt, 0pt)),
  curve.close(),
)

== Quadratic + cubic Béziers

#curve(
  stroke: 2pt + red,
  curve.move((0pt, 60pt)),
  curve.quad((40pt, 0pt), (80pt, 60pt)),
  curve.cubic(auto, (160pt, 0pt), (200pt, 60pt)),
)

== Star with even-odd vs non-zero fill rule

#let star = curve.with(
  curve.move((25pt, 0pt)),
  curve.line((10pt, 50pt)),
  curve.line((50pt, 20pt)),
  curve.line((0pt, 20pt)),
  curve.line((40pt, 50pt)),
  curve.close(),
)

#star(fill: red, fill-rule: "non-zero")
#h(8pt)
#star(fill: red, fill-rule: "even-odd")

== Hole via two subpaths

#curve(
  fill: blue.lighten(70%),
  fill-rule: "even-odd",
  stroke: 1pt + blue,
  curve.line((50pt, 0pt)),
  curve.line((50pt, 50pt)),
  curve.line((0pt, 50pt)),
  curve.close(),
  curve.move((10pt, 10pt)),
  curve.line((40pt, 10pt)),
  curve.line((40pt, 40pt)),
  curve.line((10pt, 40pt)),
  curve.close(),
)

== Relative coordinates ("turtle")

#curve(
  stroke: 2pt + green,
  curve.line((30pt, 0pt), relative: true),
  curve.line((0pt, 30pt), relative: true),
  curve.line((30pt, 0pt), relative: true),
  curve.line((0pt, -30pt), relative: true),
  curve.line((30pt, 0pt), relative: true),
)
