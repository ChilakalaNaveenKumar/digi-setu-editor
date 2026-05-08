// Gallery 01 — Half adder: A XOR B → SUM, A AND B → CARRY.
// Uses two "junction" intersections so A and B fan out cleanly.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *

  gates.gate-xor(x: 3, y: 2, w: 1.5, h: 1.5, id: "xor")
  gates.gate-and(x: 3, y: 0, w: 1.5, h: 1.5, id: "and")

  // Junction nodes for A and B.
  draw.circle((0, 2.4), radius: 0.001, name: "ja")
  draw.circle((0, 0.4), radius: 0.001, name: "jb")

  // Stubs labelling the inputs on the far left.
  wire.stub("ja", "west", length: 1)
  wire.stub("jb", "west", length: 1)
  draw.content((rel: (-1.3, 0), to: "ja"), $A$)
  draw.content((rel: (-1.3, 0), to: "jb"), $B$)

  // A → XOR.in0 and AND.in0.
  wire.wire("a-xor", ("ja", "xor-port-in0"), style: "zigzag", zigzag-ratio: 50%)
  wire.wire("a-and", ("ja", "and-port-in0"), style: "dodge")
  wire.intersection("ja")

  // B → XOR.in1 and AND.in1.
  wire.wire("b-xor", ("jb", "xor-port-in1"), style: "dodge")
  wire.wire("b-and", ("jb", "and-port-in1"), style: "zigzag", zigzag-ratio: 50%)
  wire.intersection("jb")

  // Outputs labelled SUM and CARRY.
  wire.stub("xor-port-out", "east", length: 1.2)
  wire.stub("and-port-out", "east", length: 1.2)
  draw.content((rel: (1.6, 0), to: "xor-port-out"), [SUM])
  draw.content((rel: (1.7, 0), to: "and-port-out"), [CARRY])
})
