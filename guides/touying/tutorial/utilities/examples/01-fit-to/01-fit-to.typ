// Utilities 01 — fit-to-height and fit-to-width.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Fit a heading to the slide width
#slide[
  #utils.fit-to-width(1fr)[
    #text(weight: "bold")[A Very Long Presentation Title That Should Fill the Entire Slide Width]
  ]
  Some content below.
]

== Fit a table to the remaining height
#slide[
  #utils.fit-to-height(1fr)[
    #table(
      columns: (1fr, 1fr, 1fr),
      [A], [B], [C],
      [1], [2], [3],
      [4], [5], [6],
    )
  ]
]
