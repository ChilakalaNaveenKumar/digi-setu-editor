#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.transform-shear-x(0.3)
  content((0, 0), [shear-x(0.3) = #repr(m)])
})
