#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let re(V) = V.at(0)

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [re((3, 4)) = #re((3, 4))])
})
