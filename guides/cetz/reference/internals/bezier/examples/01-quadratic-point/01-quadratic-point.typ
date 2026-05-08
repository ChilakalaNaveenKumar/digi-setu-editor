#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// Equivalent: draw the quadratic curve and pick out a point at t = 0.5
// using the path interpolation coordinate (`50%`).
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (3, 0), (1.5, 2), name: "q")
  circle("q.50%", radius: .07, fill: red)
})
