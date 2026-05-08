#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let norm(V) = calc.sqrt(V.at(0) * V.at(0) + V.at(1) * V.at(1))
#let unit(V) = (V.at(0) / norm(V), V.at(1) / norm(V))

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [unit((3, 4)) = #repr(unit((3, 4)))])
})
