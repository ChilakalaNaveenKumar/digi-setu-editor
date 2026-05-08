#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `cubic-t-for-distance` is what backs both arc-length-aware mark
// placement and arc-length-aware path interpolation. Here we mark the
// point that sits 25 % of the *arc length* along the curve via the
// `25%` path-interpolation coordinate, which uses this function.
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), name: "c")
  circle("c.25%", radius: .07, fill: red)
})
