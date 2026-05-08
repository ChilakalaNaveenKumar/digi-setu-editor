#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Per-call styling

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0), fill: aqua, stroke: 2pt + black)
  rect((1, -.5), (3, .5), fill: yellow.lighten(40%))
})

== Inherited via set-style

#cetz.canvas({
  import cetz.draw: *
  set-style(stroke: 2pt + red, fill: white)
  circle((0, 0))
  rect((1, -.5), (2, .5))
})

== Style root for a single shape

#cetz.canvas({
  import cetz.draw: *
  set-style(rect: (radius: 25%, fill: yellow.lighten(50%)))
  rect((0, 0), (1, 1))
  rect((1.5, 0), (2.5, 1))
})

== Layered inheritance via group

#cetz.canvas({
  import cetz.draw: *
  set-style(stroke: 1pt + gray)
  group({
    set-style(stroke: 2pt + red)
    line((0, 0), (1, 0))
  })
  line((0, .5), (1, .5))
})

== Marks (sub-style)

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 0), mark: (end: ">"))
  line((0, .5), (3, .5), mark: (start: "<", end: ">>"))
})
