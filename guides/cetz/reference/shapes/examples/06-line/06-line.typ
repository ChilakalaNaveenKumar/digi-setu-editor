#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Single segment + polyline + closed polygon

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (1.5, 1))
  line((2, 0), (3, 0.5), (4, -0.5), (5, 0))
  line((6, 0), (6, 1), (7, 2), (8, 1), (8, 0), close: true)
})

== Border-to-border line between named elements

#cetz.canvas({
  import cetz.draw: *
  circle((1, 2), radius: .5, name: "a")
  rect((2, 1), (rel: (1, 1)), name: "b")
  line("a", "b")
})
