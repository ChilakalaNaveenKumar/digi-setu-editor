// Demo 02 — MIPS-flavoured single-cycle datapath: PC, IMEM, register
// file, sign-extend, ALU, DMEM, write-back mux. Wires labelled where
// useful.

#set page(width: auto, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

= MIPS single-cycle datapath

#circuiteria.circuit({
  import circuiteria: *

  element.block(x: 0, y: 0, w: 1.4, h: 1.4, id: "pc", name: [PC],
    ports: (east: ((id: "out"),)),
    fill: util.colors.green.lighten(70%))

  element.block(x: 3, y: -0.4, w: 1.8, h: 2.2, id: "imem",
    name: [I-MEM],
    ports: (west: ((id: "addr"),), east: ((id: "instr"),)),
    fill: util.colors.orange.lighten(70%))

  element.block(x: 6.5, y: -1, w: 2.4, h: 3.4, id: "rf",
    name: [Reg\ File],
    ports: (
      west: ((id: "rs"), (id: "rt"), (id: "rd"), (id: "wd")),
      east: ((id: "a"), (id: "b")),
    ),
    fill: util.colors.blue.lighten(70%))

  element.extender(x: 6.5, y: -3, w: 2, h: 1, id: "sext",
    name: [Sign-ext],
    fill: util.colors.green.lighten(60%))

  element.alu(x: 11, y: -0.5, w: 1.6, h: 2.5, id: "alu",
    fill: util.colors.green.lighten(60%))

  element.block(x: 14.2, y: -0.4, w: 1.8, h: 2.2, id: "dmem",
    name: [D-MEM],
    ports: (
      west: ((id: "addr"), (id: "wd")),
      east: ((id: "rd"),),
    ),
    fill: util.colors.orange.lighten(70%))

  element.multiplexer(x: 17.5, y: -0.2, w: 1, h: 1.8,
    id: "wbmux", entries: ("ALU", "MEM"),
    fill: util.colors.blue.lighten(80%))

  // Forward path.
  wire.wire("pc-imem", ("pc-port-out", "imem-port-addr"))
  wire.wire("instr-rs", ("imem-port-instr", "rf-port-rs"),
    style: "zigzag", zigzag-ratio: 30%)
  wire.wire("rf-aluA", ("rf-port-a", "alu-port-in1"),
    style: "zigzag", zigzag-ratio: 25%)
  wire.wire("rf-aluB", ("rf-port-b", "alu-port-in2"),
    style: "zigzag", zigzag-ratio: 25%)
  wire.wire("alu-dmem", ("alu-port-out", "dmem-port-addr"),
    style: "zigzag")
  wire.wire("alu-mux",  ("alu-port-out", "wbmux-port-in0"),
    style: "dodge")
  wire.wire("dmem-mux", ("dmem-port-rd", "wbmux-port-in1"))
  wire.stub("wbmux-port-out", "east", length: 1.2)
  wire.stub("wbmux.south", "south", length: 0.8)

  // Open inputs / control signals.
  wire.stub("rf-port-rd", "west", length: 0.6)
  wire.stub("rf-port-wd", "west", length: 0.6)
  wire.stub("sext-port-in", "west", length: 0.6)
  wire.stub("sext-port-out", "east", length: 0.6)
})
