#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let conj(V)   = (V.at(0), -V.at(1))
#let normsq(V) = V.at(0) * V.at(0) + V.at(1) * V.at(1)
#let mul(V, W) = (
  V.at(0) * W.at(0) - V.at(1) * W.at(1),
  V.at(1) * W.at(0) + V.at(0) * W.at(1),
)
#let inv(V)    = (conj(V).at(0) / normsq(V), conj(V).at(1) / normsq(V))
#let div(V, W) = mul(V, inv(W))
#let arg(V)    = calc.atan2(..V) / 1rad
#let ang(V, W) = arg(div(W, V))

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [ang((1, 0), (0, 1)) = #ang((1, 0), (0, 1))])
})
