#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  element.extender(
    x: 0, y: 0, w: 3, h: 1,
    id: "extender",
  )
  wire.stub("extender-port-in", "west")
  wire.stub("extender-port-out", "east")
})
