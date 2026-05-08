#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  wire.wire("w1", ((0, 0), (1, 1)), style: "zigzag")
  wire.wire("w2", ((0, 0), (1, -.5)),
            style: "zigzag", zigzag-ratio: 80%)
  wire.intersection("w1.zig")
  wire.intersection((1, 1), radius: .15, fill: red)
})
