#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let cscale(V, t) = (V.at(0) * t, V.at(1) * t)

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [scale((3, 4), 2) = #repr(cscale((3, 4), 2))])
})
