// Gallery 02 — Full adder built from gates: SUM = A⊕B⊕Cin,
// COUT = (A⊕B)·Cin + A·B.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *

  gates.gate-xor(x: 2,   y: 4,   w: 1.5, h: 1.5, id: "xor1")
  gates.gate-xor(x: 5.5, y: 3,   w: 1.5, h: 1.5, id: "xor2")
  gates.gate-and(x: 5.5, y: 1.5, w: 1.5, h: 1.5, id: "and1")
  gates.gate-and(x: 2,   y: 0,   w: 1.5, h: 1.5, id: "and2")
  gates.gate-or(x: 8,   y: 0.7, w: 1.5, h: 1.5, id: "or1")

  // Inputs.
  for (lbl, y) in (("A", 4.7), ("B", 3.7), ("Cin", 2)) {
    draw.content((-0.2, y), $#lbl$, anchor: "east")
  }
  draw.circle((0.5, 4.7), radius: 0.001, name: "jA")
  draw.circle((0.5, 3.7), radius: 0.001, name: "jB")
  draw.circle((0.5, 2.0), radius: 0.001, name: "jC")
  for j in ("jA", "jB", "jC") {
    wire.stub(j, "west", length: 0.4)
  }

  // First stage: A,B → xor1 and and2.
  wire.wire("a-xor1", ("jA", "xor1-port-in0"), style: "dodge")
  wire.wire("a-and2", ("jA", "and2-port-in0"), style: "dodge")
  wire.intersection("jA")
  wire.wire("b-xor1", ("jB", "xor1-port-in1"), style: "dodge")
  wire.wire("b-and2", ("jB", "and2-port-in1"), style: "dodge")
  wire.intersection("jB")

  // Second stage: xor1 + Cin → xor2 (sum), and into and1 (carry).
  draw.circle((4.6, 3.7), radius: 0.001, name: "jX")
  wire.wire("x1-jx", ("xor1-port-out", "jX"))
  wire.wire("jx-x2", ("jX", "xor2-port-in0"), style: "dodge")
  wire.wire("jx-a1", ("jX", "and1-port-in0"), style: "dodge")
  wire.intersection("jX")

  // Cin fan-out.
  draw.circle((4.6, 2), radius: 0.001, name: "jCin")
  wire.wire("c-jcin", ("jC", "jCin"))
  wire.wire("jcin-x2", ("jCin", "xor2-port-in1"), style: "dodge")
  wire.wire("jcin-a1", ("jCin", "and1-port-in1"), style: "dodge")
  wire.intersection("jCin")

  // OR collects (xor1·Cin) + (A·B).
  wire.wire("a1-or",  ("and1-port-out", "or1-port-in0"), style: "dodge")
  wire.wire("a2-or",  ("and2-port-out", "or1-port-in1"), style: "dodge")

  // Outputs.
  wire.stub("xor2-port-out", "east", length: 0.7)
  wire.stub("or1-port-out",  "east", length: 0.7)
  draw.content((rel: (1.0, 0), to: "xor2-port-out"), [SUM])
  draw.content((rel: (1.1, 0), to: "or1-port-out"),  [Cout])
})
