#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== xyz tuples

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0), radius: .15, fill: blue)
  circle((1, 1), radius: .15, fill: red)
})

== Polar

#cetz.canvas({
  import cetz.draw: *
  for a in (0deg, 45deg, 90deg, 135deg, 180deg, 225deg, 270deg, 315deg) {
    line((0, 0), (a, 1.5))
  }
})

== Relative + previous coordinate

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0), name: "a")
  circle((rel: (1, 0)), name: "b")        // 1 right of previous
  circle((rel: (1, 0), to: "a"))          // 1 right of "a"
})

== Anchor strings

#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (2, 1), name: "r")
  circle("r.north", radius: .1, fill: red)
  circle((name: "r", anchor: "south-east"), radius: .1, fill: blue)
})

== Path interpolation

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 1), name: "l")
  circle(("l.start", 50%, "l.end"), radius: .1, fill: green)
})
