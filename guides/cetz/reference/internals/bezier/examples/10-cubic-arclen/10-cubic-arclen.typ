#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2))
  // The arc length is what backs the `cubic-shorten` and
  // `cubic-t-for-distance` helpers used by mark placement.
  content((2, -1.6), [arc length is computed via Gauss–Legendre quadrature])
})
