// Demo 03 — Memory hierarchy: CPU → L1 → L2 → RAM, with a "miss" arrow
// going further down each level. Uses the `group` element to label
// each tier.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import "@preview/cetz:0.3.2": draw

= Memory hierarchy

#circuiteria.circuit({
  import circuiteria: *

  element.group(id: "core", name: [CPU core],
    stroke: (dash: "dashed"),
    {
      element.block(id: "alu", x: 0, y: 0, w: 1.6, h: 1.4,
        name: [ALU],
        ports: (east: ((id: "out"),)),
        fill: util.colors.green.lighten(70%))
      element.block(id: "rf", x: 0, y: 2, w: 1.6, h: 1.4,
        name: [Reg\ File],
        ports: (east: ((id: "out"),)),
        fill: util.colors.blue.lighten(70%))
    })

  element.block(x: 5,  y: 1, w: 1.6, h: 1.6, id: "l1",
    name: [L1],
    ports: (
      west: ((id: "cpu"),),
      east: ((id: "miss"),),
      south: ((id: "hit"),),
    ),
    fill: util.colors.orange.lighten(70%))

  element.block(x: 8,  y: 0.5, w: 1.6, h: 1.6, id: "l2",
    name: [L2],
    ports: (
      west: ((id: "in"),),
      east: ((id: "miss"),),
      south: ((id: "hit"),),
    ),
    fill: util.colors.orange.lighten(60%))

  element.block(x: 11, y: 0, w: 1.8, h: 1.6, id: "ram",
    name: [DRAM],
    ports: (west: ((id: "in"),), south: ((id: "out"),)),
    fill: util.colors.orange.lighten(50%))

  // Hot path.
  wire.wire("alu-l1",  ("alu-port-out", "l1-port-cpu"),
    style: "dodge")
  wire.wire("rf-l1",   ("rf-port-out",  "l1-port-cpu"),
    style: "dodge")
  wire.wire("l1-l2",   ("l1-port-miss", "l2-port-in"))
  wire.wire("l2-ram",  ("l2-port-miss", "ram-port-in"))

  // Hits funnel back up.
  wire.stub("l1-port-hit",  "south", length: 0.8)
  wire.stub("l2-port-hit",  "south", length: 0.8)
  wire.stub("ram-port-out", "south", length: 0.8)
  draw.content((rel: (0, -1), to: "l1-port-hit"),
    text(7pt)[hit (1ns)])
  draw.content((rel: (0, -1), to: "l2-port-hit"),
    text(7pt)[hit (10ns)])
  draw.content((rel: (0, -1), to: "ram-port-out"),
    text(7pt)[hit (100ns)])
})
