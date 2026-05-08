#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Rotate on z (positional)

#cetz.canvas({
  import cetz.draw: *
  rotate(z: 45deg)
  rect((-1, -1), (1, 1))
})

== Rotate on y (3-D)

#cetz.canvas({
  import cetz.draw: *
  rotate(y: 80deg)
  circle((0, 0))
})
