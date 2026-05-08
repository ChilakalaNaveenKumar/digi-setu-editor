#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Compass anchors of a rect

#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (2, 2), name: "r")
  for-each-anchor("r", exclude: ("start", "mid", "end"), name => {
    content((), box(inset: 1pt, fill: white, text(8pt, [#name])), angle: -30deg)
  })
})

== Path anchors

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (4, 0), name: "l")
  for pct in (0%, 25%, 50%, 75%, 100%) {
    circle((name: "l", anchor: pct), radius: .07, fill: red)
  }
})

== Custom anchors inside a group

#cetz.canvas({
  import cetz.draw: *
  group(name: "g", {
    circle((0, 0))
    anchor("here", (.4, .1))
    circle("here", radius: .1, fill: red)
  })
  circle("g.here", radius: .05, fill: green)
})

== Intersections become anchors

#cetz.canvas({
  import cetz.draw: *
  intersections("i", {
    circle((0, 0))
    line((-1, 0), (1, 0))
  })
  circle("i.0", radius: .07, fill: red)
  circle("i.1", radius: .07, fill: red)
})
