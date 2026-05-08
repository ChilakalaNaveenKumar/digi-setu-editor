// Custom gates 01 — vertical-edges + diamond render functions.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#let draw-quill-gate(gate, draw-params) = {
  let stroke = draw-params.wire
  let bg = draw-params.at("background", default: white)
  let fill = if gate.fill != none and gate.fill != auto { gate.fill }
             else if bg == auto { white }
             else { bg }
  box(
    gate.content,
    fill: fill,
    stroke: (left: stroke, right: stroke),
    inset: draw-params.padding,
  )
}

#let draw-diamond(gate, draw-params) = {
  let s = draw-params.wire
  let bg = draw-params.at("background", default: white)
  let fill = if gate.fill != none and gate.fill != auto { gate.fill }
             else if bg == auto { white }
             else { bg }
  box(
    rotate(45deg, box(
      gate.content,
      stroke: s,
      fill: fill,
      inset: draw-params.padding,
    )),
  )
}

#quantum-circuit(
  1, gate("Quill", draw-function: draw-quill-gate), 1,
)

#v(0.6em)

#quantum-circuit(
  1, gate($X$, draw-function: draw-diamond), 1
)
