#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
// Importing `draw` lets us write a custom `draw-shape:` callback. The
// callback MUST register a CeTZ element with `name: id` so that downstream
// port placement and wire stubs can resolve `<id>.east`, `<id>-port-...`.
#import "@preview/cetz:0.3.2": draw

== Custom `draw-shape` (rounded rectangle, named with `id`)

#let rounded-shape(id, tl, tr, br, bl, fill, stroke) = {
  let f = draw.rect(
    radius: 0.5em,
    inset: 0.5em,
    fill: fill,
    stroke: stroke,
    name: id,
    bl, tr,
  )
  return (f, tl, tr, br, bl)
}

#circuiteria.circuit({
  import circuiteria: *
  element.elmt(
    draw-shape: rounded-shape,
    x: 0, y: 0, w: 3, h: 2, id: "e",
    name: "elmt",
    ports: (
      west:  ((id: "in1"), (id: "in2")),
      east:  ((id: "out"),),
      north: ((id: "clk", clock: true),),
    ),
    fill: util.colors.yellow,
    debug: (ports: true),
  )
  wire.stub("e-port-clk", "north")
  wire.stub("e-port-in1", "west")
  wire.stub("e-port-in2", "west")
  wire.stub("e-port-out", "east")
})
