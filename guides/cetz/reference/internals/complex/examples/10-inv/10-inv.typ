#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let conj(V)   = (V.at(0), -V.at(1))
#let normsq(V) = V.at(0) * V.at(0) + V.at(1) * V.at(1)
#let inv(V)    = (conj(V).at(0) / normsq(V), conj(V).at(1) / normsq(V))

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [inv((3, 4)) = #repr(inv((3, 4)))])
})
