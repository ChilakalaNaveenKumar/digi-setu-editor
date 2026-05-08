// Gallery 07 — D flip-flop drawn as a labelled `block` with clock,
// asynchronous clear, and complementary outputs Q / !Q.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  element.block(
    x: 0, y: 0, w: 2.4, h: 3,
    id: "ff",
    name: "D-FF",
    ports: (
      west:  ((id: "d", name: "D"),),
      north: ((id: "clk", clock: true),),
      south: ((id: "clr", name: "CLR"),),
      east:  ((id: "q", name: "Q"),
              (id: "qbar", name: $overline(Q)$)),
    ),
    fill: util.colors.blue.lighten(70%),
  )

  wire.stub("ff-port-d",   "west",  length: 1)
  wire.stub("ff-port-clk", "north", length: 0.8)
  wire.stub("ff-port-clr", "south", length: 0.8)
  wire.stub("ff-port-q",   "east",  length: 1)
  wire.stub("ff-port-qbar", "east", length: 1)

  draw.content((rel: (-1.2, 0), to: "ff-port-d"), [D])
  draw.content((rel: (0, 1.0),  to: "ff-port-clk"), [CLK])
  draw.content((rel: (0, -1.0), to: "ff-port-clr"), [CLR])
  draw.content((rel: (1.2, 0),  to: "ff-port-q"), [Q])
  draw.content((rel: (1.4, 0),  to: "ff-port-qbar"), $overline(Q)$)
})
