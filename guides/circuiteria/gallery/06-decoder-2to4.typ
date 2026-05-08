// Gallery 06 — 2-to-4 decoder built from gates. Outputs Y0..Y3 are
// the four minterms of (S1, S0).

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *

  gates.gate-not(x: 1, y: 4.5, w: 1.2, h: 0.8, id: "n0")
  gates.gate-not(x: 1, y: 5.7, w: 1.2, h: 0.8, id: "n1")

  // 4 AND gates → minterms.
  for i in range(4) {
    gates.gate-and(x: 5, y: i * 1.5, w: 1.5, h: 1.2,
      id: "and" + str(i))
  }

  // Inputs.
  draw.content((-0.2, 4.9), $S_0$, anchor: "east")
  draw.content((-0.2, 6.1), $S_1$, anchor: "east")
  draw.circle((0.3, 4.9), radius: 0.001, name: "jS0")
  draw.circle((0.3, 6.1), radius: 0.001, name: "jS1")
  wire.stub("jS0", "west", length: 0.4)
  wire.stub("jS1", "west", length: 0.4)

  // S0 → NOT(S0); also fan out to AND in1 of and1, and3.
  wire.wire("s0-n0", ("jS0", "n0-port-in0"), style: "zigzag")
  wire.wire("s1-n1", ("jS1", "n1-port-in0"), style: "zigzag")

  // Outputs labelled Y0..Y3.
  for i in range(4) {
    wire.stub("and" + str(i) + "-port-out", "east", length: 0.8)
    draw.content((rel: (1, 0), to: "and" + str(i) + "-port-out"),
      $Y_#i$)
  }
  draw.content((3.5, 7.6), text(8pt)[(decoded as 2-to-4)])
})
