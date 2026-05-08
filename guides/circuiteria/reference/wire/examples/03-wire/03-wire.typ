#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *

  // Two blocks, three flavours of wire connecting them.
  element.block(x: 0, y: 0, w: 2, h: 2, id: "a",
    ports: (east: ((id: "out"),)))
  element.block(x: 5, y: 0, w: 2, h: 2, id: "b",
    ports: (west: ((id: "in"),)))

  // 1. Direct
  wire.wire("w-direct", ("a-port-out", "b-port-in"))

  // 2. Bus + slice + label
  element.block(x: 0, y: -3, w: 2, h: 2, id: "c",
    ports: (east: ((id: "out"),)))
  element.block(x: 5, y: -3, w: 2, h: 2, id: "d",
    ports: (west: ((id: "in"),)))
  wire.wire("w-bus", ("c-port-out", "d-port-in"),
    bus: true, name: "data", slice: (0, 7), color: blue)

  // 3. Dashed + directed (arrow at end)
  element.block(x: 0, y: -6, w: 2, h: 2, id: "e",
    ports: (east: ((id: "out"),)))
  element.block(x: 5, y: -6, w: 2, h: 2, id: "f",
    ports: (west: ((id: "in"),)))
  wire.wire("w-arr", ("e-port-out", "f-port-in"),
    dashed: true, directed: true, color: red)
})
