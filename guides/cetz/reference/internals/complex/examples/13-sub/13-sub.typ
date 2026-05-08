#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let sub(V, W) = (V.at(0) - W.at(0), V.at(1) - W.at(1))

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [sub((1, 2), (3, 4)) = #repr(sub((1, 2), (3, 4)))])
})
