#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Inline body

#cetz.canvas({
  import cetz.draw: *
  intersections("i", {
    circle((0, 0))
    bezier((0, 0), (3, 0), (1, -1), (2, 1))
    line((0, -1), (0, 1))
    rect((1.5, -1), (2.5, 1))
  })
  for-each-anchor("i", (name) => {
    circle("i." + name, radius: .1, fill: blue)
  })
})

== By name

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0), name: "a")
  rect((0, 0), (1, 1), name: "b")
  intersections("i", "a", "b")
  for-each-anchor("i", (name) => {
    circle("i." + name, radius: .1, fill: blue)
  })
})
