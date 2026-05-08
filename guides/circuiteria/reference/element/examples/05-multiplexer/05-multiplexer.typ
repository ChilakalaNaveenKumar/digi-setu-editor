#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  element.multiplexer(
    x: 0, y: 0, w: 1, h: 3,
    id: "multiplexer",
    entries: 3,
  )
  wire.stub("multiplexer.north", "north")
  wire.stub("multiplexer-port-out", "east")

  element.multiplexer(
    x: 0, y: -4, w: 1, h: 3,
    id: "multiplexer2",
    entries: ("A", "B", "C"),
  )
  wire.stub("multiplexer2.south", "south")
  wire.stub("multiplexer2-port-out", "east")

  for i in range(3) {
    wire.stub("multiplexer-port-in"  + str(i), "west")
    wire.stub("multiplexer2-port-in" + str(i), "west")
  }
})
