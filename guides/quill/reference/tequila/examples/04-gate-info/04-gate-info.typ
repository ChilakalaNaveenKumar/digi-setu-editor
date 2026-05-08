// Tequila 04 — generic single-qubit gate via tq.gate(...).
// (gate-info is documented in the manual but is internal in v0.7.2;
// use tq.gate / tq.mqgate as the public surface.)

#import "@preview/quill:0.7.2": *
#import "@preview/quill:0.7.2": tequila as tq
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  ..tq.build(
    tq.gate(0, $H$, fill: blue.lighten(70%)),
    tq.cx(0, 1),
  )
)
