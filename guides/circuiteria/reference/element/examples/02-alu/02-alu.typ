#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  element.alu(x: 0, y: 0, w: 1, h: 2, id: "alu")
  wire.stub("alu-port-in1", "west")
  wire.stub("alu-port-in2", "west")
  wire.stub("alu-port-out", "east")
})
