// Dynamic 05 — touying-reducer for CeTZ.
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/cetz:0.5.0"

#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(title: [CeTZ + Touying]),
)

== CeTZ animation
#slide[
  Cetz in Touying:
  #cetz-canvas({
    import cetz.draw: *

    rect((0, 0), (5, 5))
    (pause,)
    rect((0, 0), (1, 1))
    rect((1, 1), (2, 2))
    rect((2, 2), (3, 3))
    (pause,)
    line((0, 0), (2.5, 2.5), name: "line")
  })
]
