// Gallery 03 — 4-bit ripple-carry adder: 4 full adders chained via the
// carry. Each FA is drawn as a labelled `block` element.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  let dx = 3
  for i in range(4) {
    element.block(
      x: i * dx, y: 0, w: 2, h: 2,
      id: "fa" + str(i),
      name: "FA" + str(i),
      ports: (
        north: ((id: "a", name: "A"), (id: "b", name: "B")),
        west:  ((id: "cin", name: "Cin"),),
        east:  ((id: "cout", name: "Cout"),),
        south: ((id: "s", name: "S"),),
      ),
      fill: util.colors.blue.lighten(70%),
    )
  }
  // Chain the carry.
  for i in range(3) {
    wire.wire("c" + str(i),
      ("fa" + str(i) + "-port-cout", "fa" + str(i + 1) + "-port-cin"))
  }
  // Open Cin on the leftmost.
  wire.stub("fa0-port-cin", "west", length: 1)
  draw.content((rel: (-1.2, 0), to: "fa0-port-cin"), $C_"in"$)
  // Open Cout on the rightmost.
  wire.stub("fa3-port-cout", "east", length: 1)
  draw.content((rel: (1.5, 0), to: "fa3-port-cout"), $C_"out"$)
  // A_i, B_i inputs from above.
  for i in range(4) {
    wire.stub("fa" + str(i) + "-port-a", "north", length: 0.8)
    wire.stub("fa" + str(i) + "-port-b", "north", length: 0.8)
    draw.content((rel: (0, 1.1),
                  to: "fa" + str(i) + "-port-a"), $A_#i$)
    draw.content((rel: (0, 1.1),
                  to: "fa" + str(i) + "-port-b"), $B_#i$)
  }
  // Sum outputs going downward.
  for i in range(4) {
    wire.stub("fa" + str(i) + "-port-s", "south", length: 0.8)
    draw.content((rel: (0, -1.1),
                  to: "fa" + str(i) + "-port-s"), $S_#i$)
  }
})
