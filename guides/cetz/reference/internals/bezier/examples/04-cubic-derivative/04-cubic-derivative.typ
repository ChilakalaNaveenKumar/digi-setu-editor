#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `cubic-derivative` produces the tangent vector at a parameter t.
// Drawing the curve with a path-interpolation arrow at t = 0.5 shows the
// effect of that tangent visually.
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), name: "c", mark: (end: ">"))
})
