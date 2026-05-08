// Gallery 08 — 4-bit register: 4 D flip-flops sharing CLK and CLR.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  let dx = 3.5
  for i in range(4) {
    element.block(
      x: i * dx, y: 0, w: 2.2, h: 2.4,
      id: "ff" + str(i),
      name: "FF" + str(i),
      ports: (
        west:  ((id: "d", name: "D"),),
        north: ((id: "clk", clock: true),),
        south: ((id: "clr", name: "CLR"),),
        east:  ((id: "q", name: "Q"),),
      ),
      fill: util.colors.blue.lighten(70%),
    )
  }
  // Inputs D0..D3 from the left.
  for i in range(4) {
    wire.stub("ff" + str(i) + "-port-d", "west", length: 0.8)
    draw.content((rel: (-1.0, 0),
                  to: "ff" + str(i) + "-port-d"), $D_#i$)
    wire.stub("ff" + str(i) + "-port-q", "east", length: 0.8)
    draw.content((rel: (1.0, 0),
                  to: "ff" + str(i) + "-port-q"), $Q_#i$)
  }
  // Shared CLK bus across the top.
  draw.line((-1, 3.4), (3 * dx + 3, 3.4), name: "clk-bus")
  draw.content((-1.4, 3.4), [CLK], anchor: "east")
  for i in range(4) {
    wire.wire("clk" + str(i),
      ("ff" + str(i) + "-port-clk", (i * dx + 1.1, 3.4)))
    wire.intersection((i * dx + 1.1, 3.4))
  }
  // Shared CLR bus across the bottom.
  draw.line((-1, -1), (3 * dx + 3, -1), name: "clr-bus")
  draw.content((-1.4, -1), [CLR], anchor: "east")
  for i in range(4) {
    wire.wire("clr" + str(i),
      ("ff" + str(i) + "-port-clr", (i * dx + 1.1, -1)))
    wire.intersection((i * dx + 1.1, -1))
  }
})
