// Gallery 09 — 1-bit magnitude comparator: A=B (XNOR), A>B (A AND !B),
// A<B (!A AND B).

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  gates.gate-not(x: 2,    y: 2,   w: 1.2, h: 0.9, id: "nA")
  gates.gate-not(x: 2,    y: 3.5, w: 1.2, h: 0.9, id: "nB")

  gates.gate-and(x: 4.5,  y: 4.5, w: 1.5, h: 1.4, id: "agtb")
  gates.gate-xnor(x: 4.5, y: 2.7, w: 1.5, h: 1.5, id: "aeqb")
  gates.gate-and(x: 4.5,  y: 0.8, w: 1.5, h: 1.4, id: "altb")

  for (lbl, y) in (("A", 5.4), ("B", 0.5)) {
    draw.content((-0.2, y), $#lbl$, anchor: "east")
  }
  draw.circle((0.4, 5.4), radius: 0.001, name: "jA")
  draw.circle((0.4, 0.5), radius: 0.001, name: "jB")
  for j in ("jA", "jB") { wire.stub(j, "west", length: 0.4) }

  // A → A>B in0, XNOR in0, NOT(A).
  wire.wire("a-agtb",  ("jA", "agtb-port-in0"), style: "dodge")
  wire.wire("a-aeqb",  ("jA", "aeqb-port-in0"), style: "dodge")
  wire.wire("a-na",    ("jA", "nA-port-in0"),   style: "dodge")
  wire.intersection("jA")

  // B → NOT(B), XNOR in1, A<B in1.
  wire.wire("b-nb",    ("jB", "nB-port-in0"),   style: "dodge")
  wire.wire("b-aeqb",  ("jB", "aeqb-port-in1"), style: "dodge")
  wire.wire("b-altb",  ("jB", "altb-port-in1"), style: "dodge")
  wire.intersection("jB")

  // !A → A<B in0, !B → A>B in1.
  wire.wire("nA-altb", ("nA-port-out", "altb-port-in0"), style: "dodge")
  wire.wire("nB-agtb", ("nB-port-out", "agtb-port-in1"), style: "dodge")

  for (g, lbl) in (("agtb", $A>B$), ("aeqb", $A=B$), ("altb", $A<B$)) {
    wire.stub(g + "-port-out", "east", length: 0.7)
    draw.content((rel: (1, 0), to: g + "-port-out"), lbl)
  }
})
