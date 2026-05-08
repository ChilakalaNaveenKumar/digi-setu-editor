#set page(width: 16cm, height: auto, margin: 8pt)

== Diagonal-stripe hatch

#let hatch = tiling(size: (8pt, 8pt))[
  #place(line(start: (0%, 0%), end: (100%, 100%), stroke: 0.5pt))
]
#rect(width: 100%, height: 40pt, fill: hatch, stroke: 0.5pt + black)

== Dotted background

#let dots = tiling(size: (10pt, 10pt))[
  #place(circle(radius: 1.2pt, fill: black))
]
#rect(width: 100%, height: 40pt, fill: dots, stroke: 0.5pt + black)

== Spacing creates gaps (tile color shows through)

#let crossed = tiling(size: (12pt, 12pt))[
  #place(line(start: (0%, 0%), end: (100%, 100%), stroke: 0.5pt))
  #place(line(start: (0%, 100%), end: (100%, 0%), stroke: 0.5pt))
]
#let crossed-spaced = tiling(
  size: (12pt, 12pt), spacing: (16pt, 16pt),
)[
  #place(line(start: (0%, 0%), end: (100%, 100%), stroke: 0.5pt))
  #place(line(start: (0%, 100%), end: (100%, 0%), stroke: 0.5pt))
]

#stack(dir: ltr, spacing: 8pt,
  rect(width: 4cm, height: 40pt, fill: crossed, stroke: 0.5pt + black),
  rect(width: 4cm, height: 40pt, fill: crossed-spaced, stroke: 0.5pt + black),
)

== Tiling on text (`relative: "parent"`)

#let rainbow-tile = tiling(
  size: (30pt, 30pt),
  relative: "parent",
  square(size: 30pt,
         fill: gradient.conic(..color.map.rainbow)),
)

#set text(20pt, weight: "bold", fill: rainbow-tile)
Tiled text spanning a single shared pattern.
#set text(fill: black, weight: "regular", size: 10pt)
