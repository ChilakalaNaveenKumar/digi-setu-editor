// Gallery 05 — 4:1 multiplexer using the high-level `multiplexer`
// element. Inputs A, B, C, D; select bits S0, S1.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  element.multiplexer(
    x: 0, y: 0, w: 1.5, h: 5,
    id: "mux",
    entries: ("A", "B", "C", "D"),
    fill: util.colors.blue.lighten(70%),
  )
  // Open inputs on the west.
  for i in range(4) {
    wire.stub("mux-port-in" + str(i), "west", length: 1)
  }
  // Select bits.
  wire.stub("mux.south", "south", length: 1)
  draw.content((rel: (0, -1.4), to: "mux.south"),
    align(center)[$S_0 \  S_1$])
  // Output.
  wire.stub("mux-port-out", "east", length: 1.2)
  draw.content((rel: (1.6, 0), to: "mux-port-out"), [Y])
})
