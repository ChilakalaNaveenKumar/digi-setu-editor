// Custom gates 03 — data: parametric custom gate.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#let draw-tag(gate, draw-params) = {
  let stroke = draw-params.wire
  let info = gate.data
  let fill = info.color
  box(
    stroke: stroke,
    fill: fill,
    inset: draw-params.padding,
    radius: 3pt,
    [#info.emoji #gate.content],
  )
}

#quantum-circuit(
  1, gate("apple", draw-function: draw-tag,
    data: (color: red.lighten(70%), emoji: text("🍎"))), 1,
  gate("banana", draw-function: draw-tag,
    data: (color: yellow.lighten(50%), emoji: text("🍌"))), 1,
)
