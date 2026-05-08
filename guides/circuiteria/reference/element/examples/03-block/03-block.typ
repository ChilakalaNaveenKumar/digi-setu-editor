#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  element.block(
    x: 0, y: 0, w: 2, h: 2, id: "block",
    ports: (
      north: ((id: "clk", clock: true),),
      west:  ((id: "in1", name: "A"),
              (id: "in2", name: "B")),
      east:  ((id: "out", name: "C"),),
    ),
  )
  wire.stub("block-port-clk", "north")
  wire.stub("block-port-in1", "west")
  wire.stub("block-port-in2", "west")
  wire.stub("block-port-out", "east")
})
