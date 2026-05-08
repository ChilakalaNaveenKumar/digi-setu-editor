#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
// `gates.gate(...)` with the default-draw-shape draws an *unnamed* rect, so
// the port machinery cannot find `<id>.east`. To use the bare `gate(...)`
// you must supply a `draw-shape` that registers `name: id`. Import the
// underlying CeTZ draw namespace to write that callback.
#import "@preview/cetz:0.3.2": draw

#let named-rect(id, tl, tr, br, bl, fill, stroke) = {
  let f = draw.rect(bl, tr, fill: fill, stroke: stroke, name: id)
  return (f, tl, tr, br, bl)
}

#circuiteria.circuit({
  import circuiteria: *
  gates.gate(draw-shape: named-rect,
    x: 0, y: 0, w: 1.5, h: 1.5, id: "g")
  gates.gate(draw-shape: named-rect,
    x: 3, y: 0, w: 1.5, h: 1.5, id: "gi", inverted: "all")
  for el in ("g", "gi") {
    wire.stub(el + "-port-in0", "west")
    wire.stub(el + "-port-in1", "west")
    wire.stub(el + "-port-out", "east")
  }
})
