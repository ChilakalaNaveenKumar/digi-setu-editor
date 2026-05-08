#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
// Circuiteria does not re-export the underlying CeTZ `draw` namespace.
// Import it explicitly when you want to call draw.circle / draw.line / etc.
// inside the circuit body. Use the same version Circuiteria depends on (0.3.2).
#import "@preview/cetz:0.3.2": draw

== Bare circuit (default length: 2em)

#circuiteria.circuit({
  import circuiteria: *
  element.block(x: 0, y: 0, w: 2, h: 2, id: "b",
    ports: (east: ((id: "out"),)))
  wire.stub("b-port-out", "east")
})

== Custom base unit

#circuiteria.circuit(length: 1cm, {
  import circuiteria: *
  element.block(x: 0, y: 0, w: 2, h: 2, id: "b",
    ports: (east: ((id: "out"),)))
  wire.stub("b-port-out", "east")
})

== Mixing CeTZ draw calls inside a circuit

#circuiteria.circuit({
  import circuiteria: *
  draw.circle((0, 0), radius: .1, fill: red, name: "ref")
  element.block(x: 1, y: -1, w: 2, h: 2, id: "b",
    ports: (west: ((id: "in"),)))
  wire.wire("w", ("ref", "b-port-in"))
})
