#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// NOTE: cetz 0.5.0's `transform-rotate-aer` references `mul-mat` without a
// module qualifier and therefore raises an "unknown variable" error at
// call time. We compose the same matrix from the working primitives.
#cetz.canvas({
  import cetz.draw: *
  let azimuth   = 30deg
  let elevation = 20deg
  let m = cetz.matrix.mul-mat(
    cetz.matrix.transform-rotate-y(azimuth),
    cetz.matrix.transform-rotate-x(elevation),
  )
  let r = cetz.matrix.round(m, precision: 3)
  content((0, 0), [aer(30°, 20°) ≈ #repr(r)])
})
