// Dynamic 04 — Cover function: default vs semi-transparent.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Default cover (`hide`)
#slide[
  First.
  #pause
  Second (hidden via `hide` until subslide 2).
]

== Semi-transparent cover
#show: touying-set-config.with(config-methods(
  cover: utils.semi-transparent-cover.with(alpha: 70%),
))
#slide[
  First.
  #pause
  Second (covered with a 70% semi-transparent rectangle).
]
