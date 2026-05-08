#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
// Need `draw.*` for the bare reference circle below.
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  draw.circle((0, 0), radius: .1, name: "p")
  wire.stub("p", "north", name: "north", length: 1)
  wire.stub("p", "east",  name: "east",  vertical: true)
  wire.stub("p", "south", name: "south", length: 15pt)
  wire.stub("p", "west",  name: "west",  length: 3em)
})
