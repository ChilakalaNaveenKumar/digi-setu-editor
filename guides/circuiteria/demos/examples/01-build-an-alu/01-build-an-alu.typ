// Demo 01 — Build an ALU step by step.
// Stage 1: half adder. Stage 2: full adder. Stage 3: 4-bit adder.
// Stage 4: add/sub unit (XOR before B + Cin = sub flag).

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

= Stage 1 — Half adder

#circuiteria.circuit({
  import circuiteria: *
  gates.gate-xor(x: 2, y: 1.5, w: 1.4, h: 1.3, id: "xor")
  gates.gate-and(x: 2, y: 0,   w: 1.4, h: 1.3, id: "and")
  draw.circle((0.4, 2.1), radius: 0.001, name: "ja")
  draw.circle((0.4, 0.6), radius: 0.001, name: "jb")
  wire.stub("ja", "west", length: 0.6)
  wire.stub("jb", "west", length: 0.6)
  draw.content((-0.5, 2.1), $A$, anchor: "east")
  draw.content((-0.5, 0.6), $B$, anchor: "east")
  wire.wire("ax", ("ja", "xor-port-in0"), style: "dodge")
  wire.wire("aa", ("ja", "and-port-in0"), style: "dodge")
  wire.intersection("ja")
  wire.wire("bx", ("jb", "xor-port-in1"), style: "dodge")
  wire.wire("ba", ("jb", "and-port-in1"), style: "dodge")
  wire.intersection("jb")
  wire.stub("xor-port-out", "east", length: 0.7)
  wire.stub("and-port-out", "east", length: 0.7)
  draw.content((rel: (1, 0), to: "xor-port-out"), [SUM])
  draw.content((rel: (1.2, 0), to: "and-port-out"), [CARRY])
})

#v(8pt)

= Stage 2 — Full adder (the half-adder + 1 OR gate)

#circuiteria.circuit({
  import circuiteria: *
  element.block(
    x: 0, y: 0, w: 2.4, h: 2.4, id: "fa", name: [Full\ Adder],
    ports: (
      west:  ((id: "a", name: "A"), (id: "b", name: "B"),
              (id: "cin", name: "Cin")),
      east:  ((id: "s", name: "S"), (id: "cout", name: "Cout")),
    ),
    fill: util.colors.blue.lighten(70%),
  )
  for p in ("a", "b", "cin") { wire.stub("fa-port-" + p, "west", length: 0.7) }
  for p in ("s", "cout")     { wire.stub("fa-port-" + p, "east", length: 0.7) }
})

#v(8pt)

= Stage 3 — 4-bit ripple-carry chain

#circuiteria.circuit({
  import circuiteria: *
  let dx = 2.6
  for i in range(4) {
    element.block(x: i * dx, y: 0, w: 1.6, h: 2,
      id: "fa" + str(i), name: "FA" + str(i),
      ports: (
        north: ((id: "a"), (id: "b")),
        west:  ((id: "cin"),),
        east:  ((id: "cout"),),
        south: ((id: "s"),),
      ),
      fill: util.colors.green.lighten(70%))
  }
  for i in range(3) {
    wire.wire("c" + str(i),
      ("fa" + str(i) + "-port-cout", "fa" + str(i + 1) + "-port-cin"))
  }
  wire.stub("fa0-port-cin", "west", length: 0.6)
  wire.stub("fa3-port-cout", "east", length: 0.6)
  for i in range(4) {
    wire.stub("fa" + str(i) + "-port-a", "north", length: 0.5)
    wire.stub("fa" + str(i) + "-port-b", "north", length: 0.5)
    wire.stub("fa" + str(i) + "-port-s", "south", length: 0.5)
  }
})

#v(8pt)

= Stage 4 — Add/Sub unit: XOR each B-bit with the SUB flag

#circuiteria.circuit({
  import circuiteria: *
  for i in range(4) {
    gates.gate-xor(x: 0, y: i * 1.4, w: 1.2, h: 1, id: "x" + str(i))
  }
  element.block(x: 3, y: -0.5, w: 2, h: 6,
    id: "adder",
    name: [4-bit\ Adder],
    ports: (
      west: ((id: "a0"), (id: "a1"), (id: "a2"), (id: "a3"),
             (id: "b0"), (id: "b1"), (id: "b2"), (id: "b3"),
             (id: "cin")),
      east: ((id: "s0"), (id: "s1"), (id: "s2"), (id: "s3"),
             (id: "cout")),
    ),
    fill: util.colors.blue.lighten(70%))
  for i in range(4) {
    wire.wire("xb" + str(i),
      ("x" + str(i) + "-port-out", "adder-port-b" + str(i)),
      style: "dodge")
    wire.stub("x" + str(i) + "-port-in0", "west", length: 0.6)
  }
  for i in range(4) {
    wire.stub("adder-port-a" + str(i), "west", length: 0.6)
    wire.stub("adder-port-s" + str(i), "east", length: 0.6)
  }
  // SUB control: connects to all xor-in1 ports + cin.
  wire.stub("adder-port-cin",  "south", length: 0.7)
  for i in range(4) {
    wire.stub("x" + str(i) + "-port-in1", "south", length: 0.5)
  }
  wire.stub("adder-port-cout", "east", length: 0.6)
})
