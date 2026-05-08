#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let arg(V) = calc.atan2(..V) / 1rad

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [arg((1, 1)) = #arg((1, 1))])
  content((0, -.5), [arg((0, 1)) = #arg((0, 1))])
})
