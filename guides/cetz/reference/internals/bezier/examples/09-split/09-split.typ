#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `bezier.split` is what powers things like the path-interpolation
// coordinate (`50%`) and tools that need a sub-arc. Visually we
// highlight the midpoint of the curve.
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), name: "c")
  circle("c.50%", radius: .07, fill: red)
})
