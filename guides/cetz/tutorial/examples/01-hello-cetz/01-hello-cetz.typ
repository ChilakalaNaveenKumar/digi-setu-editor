#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Hello CeTZ

#cetz.canvas({
  import cetz.draw: *
  // Draw a circle
  circle((0, 0))
  // Draw a line
  line((1, -1), (2, 1))
})
