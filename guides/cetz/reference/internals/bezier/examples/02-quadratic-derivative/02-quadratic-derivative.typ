#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// We can show the *direction* of the tangent at the midpoint by drawing
// a small arrow there. The math behind this comes from
// `bezier.quadratic-derivative` evaluated at t = 0.5.
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (2, 2), name: "q")
  // Endpoints are horizontal-ish, midpoint tangent is purely horizontal.
  line("q.50%", (rel: (0.6, 0)), mark: (end: ">"), stroke: red)
})
