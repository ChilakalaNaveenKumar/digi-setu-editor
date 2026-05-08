// Gallery 04 — 2:1 multiplexer realised from gates: Y = A·!S + B·S.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *

  gates.gate-not(x: 2.5, y: 1.5, w: 1.5, h: 1, id: "not")
  gates.gate-and(x: 5,   y: 1.7, w: 1.5, h: 1.5, id: "and-a")
  gates.gate-and(x: 5,   y: 0,   w: 1.5, h: 1.5, id: "and-b")
  gates.gate-or(x: 8,    y: 1,   w: 1.5, h: 1.5, id: "or")

  // Inputs.
  for (lbl, y) in (("A", 2.6), ("B", 0.8), ("S", -0.5)) {
    draw.content((-0.2, y), $#lbl$, anchor: "east")
  }
  draw.circle((0.5, 2.6), radius: 0.001, name: "jA")
  draw.circle((0.5, 0.8), radius: 0.001, name: "jB")
  draw.circle((0.5, -0.5), radius: 0.001, name: "jS")
  for j in ("jA", "jB", "jS") {
    wire.stub(j, "west", length: 0.4)
  }
  draw.circle((4, -0.5), radius: 0.001, name: "jSp")

  // S → NOT
  wire.wire("s-not", ("jS", "not-port-in0"), style: "dodge")
  // S → and-b in1 (passes through jSp)
  wire.wire("jS-jSp", ("jS", "jSp"))
  wire.wire("jSp-andb", ("jSp", "and-b-port-in1"), style: "dodge")
  wire.intersection("jS")

  // !S → and-a in1
  wire.wire("not-anda", ("not-port-out", "and-a-port-in1"), style: "dodge")

  // A → and-a in0
  wire.wire("a-anda", ("jA", "and-a-port-in0"), style: "dodge")
  // B → and-b in0
  wire.wire("b-andb", ("jB", "and-b-port-in0"), style: "dodge")

  // Combine in OR.
  wire.wire("anda-or", ("and-a-port-out", "or-port-in0"), style: "dodge")
  wire.wire("andb-or", ("and-b-port-out", "or-port-in1"), style: "dodge")

  wire.stub("or-port-out", "east", length: 0.7)
  draw.content((rel: (1.0, 0), to: "or-port-out"), [Y])
})
