#set page(width: 14cm, height: auto, margin: 8pt)

== Empty default

#ellipse(stroke: 1pt + black)
#h(8pt)
#ellipse(width: 80pt, height: 30pt, fill: aqua, stroke: none)

== Wrapping content

#ellipse(fill: yellow.lighten(60%))[
  #set align(center + horizon)
  Sized to fit
]

== Speech-bubble style with extra inset

#ellipse(
  inset: 12pt,
  fill: blue.lighten(85%),
  stroke: 1pt + blue,
)[Hello, world!]

== Relative width

#ellipse(width: 60%, height: 24pt, fill: green.lighten(70%))
