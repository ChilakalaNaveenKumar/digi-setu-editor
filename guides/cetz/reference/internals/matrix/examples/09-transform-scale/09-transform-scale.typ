#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.transform-scale(2)
  content((0, 0), [scale(2) = #repr(m)])
})
