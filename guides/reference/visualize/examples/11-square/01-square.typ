#set page(width: 14cm, height: auto, margin: 8pt)

== Sizing modes

#square(size: 30pt, fill: aqua)
#h(8pt)
#square(width: 30%, fill: yellow.lighten(60%))
#h(8pt)
#square(height: 1cm, fill: green.lighten(70%))

== Wrapping content keeps 1:1 aspect

#square(fill: blue.lighten(80%), inset: 8pt)[
  #set align(center + horizon)
  Auto sized
]

== Color swatches grid

#stack(
  dir: ltr, spacing: 4pt,
  ..for c in (red, orange, yellow, green, blue, purple) {
    (square(size: 18pt, fill: c, stroke: 0.5pt + black),)
  },
)

== Tile with rounded corner and centered glyph

#square(
  size: 28pt, radius: 6pt,
  fill: white, stroke: 0.5pt + black,
)[
  #set align(center + horizon)
  ★
]
