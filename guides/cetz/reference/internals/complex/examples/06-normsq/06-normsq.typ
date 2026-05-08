#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let normsq(V) = V.at(0) * V.at(0) + V.at(1) * V.at(1)

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [normsq((3, 4)) = #normsq((3, 4))])
})
