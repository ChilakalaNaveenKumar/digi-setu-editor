// Custom gates 02 — size-hint paired with draw-function.
// Force every such gate to 2cm wide.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#let always-wide(gate, draw-params) = {
  let m = measure(gate.content)
  (
    width: 2cm,
    height: m.height + 2 * draw-params.padding,
  )
}

#let draw-wide(gate, draw-params) = box(
  width: 2cm,
  fill: white,
  stroke: draw-params.wire,
  inset: draw-params.padding,
  align(center + horizon, gate.content),
)

#quantum-circuit(
  1, gate($H$,
    draw-function: draw-wide,
    size-hint: always-wide), 1,
)
