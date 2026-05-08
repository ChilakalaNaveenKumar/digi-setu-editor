#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let mul(V, W) = (
  V.at(0) * W.at(0) - V.at(1) * W.at(1),
  V.at(1) * W.at(0) + V.at(0) * W.at(1),
)

#cetz.canvas({
  import cetz.draw: *
  // (1+2i) * (3+4i) = -5 + 10i
  content((0, 0), [mul((1, 2), (3, 4)) = #repr(mul((1, 2), (3, 4)))])
})
