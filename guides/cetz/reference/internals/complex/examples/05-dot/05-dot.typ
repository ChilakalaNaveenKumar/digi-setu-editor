#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let conj(V) = (V.at(0), -V.at(1))
#let mul(V, W) = (
  V.at(0) * W.at(0) - V.at(1) * W.at(1),
  V.at(1) * W.at(0) + V.at(0) * W.at(1),
)
#let dot(V, W) = mul(V, conj(W)).at(0)

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [dot((1, 2), (3, 4)) = #dot((1, 2), (3, 4))])
})
