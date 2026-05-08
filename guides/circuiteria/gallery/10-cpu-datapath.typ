// Gallery 10 — Block-level CPU datapath: PC, instruction memory,
// register file, ALU, data memory, write-back mux.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *

  element.block(x: 0,  y: 0,  w: 1.4, h: 1.4, id: "pc",
    name: [PC],
    ports: (east: ((id: "out", name: "addr"),)),
    fill: util.colors.green.lighten(70%))

  element.block(x: 3,  y: -0.2, w: 1.8, h: 1.8, id: "imem",
    name: [I-MEM],
    ports: (
      west: ((id: "addr"),),
      east: ((id: "instr"),),
    ),
    fill: util.colors.orange.lighten(70%))

  element.block(x: 6.5, y: -0.5, w: 2.2, h: 2.4, id: "rf",
    name: [Reg\ File],
    ports: (
      west: ((id: "rs", name: "rs"),
             (id: "rt", name: "rt"),
             (id: "rd", name: "rd")),
      east: ((id: "a", name: "A"),
             (id: "b", name: "B")),
    ),
    fill: util.colors.blue.lighten(70%))

  element.alu(x: 11, y: 0, w: 1.4, h: 2.4, id: "alu",
    fill: util.colors.green.lighten(60%))

  element.block(x: 14, y: -0.2, w: 1.8, h: 1.8, id: "dmem",
    name: [D-MEM],
    ports: (
      west: ((id: "addr"), (id: "wdata")),
      east: ((id: "rdata"),),
    ),
    fill: util.colors.orange.lighten(70%))

  element.multiplexer(
    x: 17.5, y: 0, w: 1, h: 1.6,
    id: "wbmux",
    entries: ("ALU", "MEM"),
    fill: util.colors.blue.lighten(80%))

  // Wires.
  wire.wire("pc-imem", ("pc-port-out", "imem-port-addr"))
  wire.wire("imem-rs", ("imem-port-instr", "rf-port-rs"),
    style: "zigzag", zigzag-ratio: 30%)
  wire.wire("rf-aluA", ("rf-port-a", "alu-port-in1"),
    style: "zigzag", zigzag-ratio: 30%)
  wire.wire("rf-aluB", ("rf-port-b", "alu-port-in2"),
    style: "zigzag", zigzag-ratio: 30%)
  wire.wire("alu-dmem", ("alu-port-out", "dmem-port-addr"),
    style: "zigzag")
  wire.wire("alu-mux",  ("alu-port-out", "wbmux-port-in0"),
    style: "dodge")
  wire.wire("dmem-mux", ("dmem-port-rdata", "wbmux-port-in1"))
  wire.stub("wbmux-port-out", "east", length: 1.2)
  wire.stub("wbmux.south", "south", length: 0.8)
})
