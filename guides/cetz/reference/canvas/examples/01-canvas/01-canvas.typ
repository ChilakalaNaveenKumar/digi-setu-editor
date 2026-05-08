#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Bare canvas

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0))
})

== With debug + background + padding + stroke

#cetz.canvas(
  debug: true,
  background: aqua.lighten(70%),
  padding: .5,
  stroke: 1pt + black,
  {
    import cetz.draw: *
    rect((0, 0), (2, 1))
    circle((3, 0))
  },
)

== Custom basis (flip y axis)

#cetz.canvas(y: -1, {
  import cetz.draw: *
  // Now y grows downward, like Typst layout
  rect((0, 0), (2, 1))
  content((1, .5), [Flipped y])
})

== Inline baseline

A wee circle: #cetz.canvas(baseline: (0, 0), length: 0.6em, {
  import cetz.draw: *
  circle((0, 0), radius: 0.5, fill: blue)
}) inline.
