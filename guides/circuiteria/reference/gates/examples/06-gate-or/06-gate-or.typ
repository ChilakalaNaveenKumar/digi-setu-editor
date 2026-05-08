#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  gates.gate-or(x: 0, y: 0, w: 1.5, h: 1.5)
  gates.gate-or(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
})
