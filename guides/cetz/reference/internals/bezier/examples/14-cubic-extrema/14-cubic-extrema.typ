#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// The extrema of the cubic determine its tight bounding box. The
// outline below uses cetz.draw's debug AABB to make this visible.
#cetz.canvas(debug: true, {
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2))
})
