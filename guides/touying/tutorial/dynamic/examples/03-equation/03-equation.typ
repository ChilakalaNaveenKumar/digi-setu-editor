// Dynamic 03 — Math equation animation.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Touying equation with `pause`
#slide[
  $
    f(x) &= pause x^2 + 2x + 1  \
         &= pause (x + 1)^2  \
  $
  #meanwhile
  Touying equation is very simple.
]

== Inside-equation `uncover`
#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)
  $
    f(x) &= pause x^2 + 2x + uncover("3-", 1)  \
         &= pause (x + 1)^2  \
  $
])
