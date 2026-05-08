// Tequila 01 — tq.build(...).
// H, two CNOTs, measurement onto a classical bit.

#import "@preview/quill:0.7.2": *
#import "@preview/quill:0.7.2": tequila as tq
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  ..tq.build(
    tq.h(0),
    tq.cx(0, 1),
    tq.cx(0, 2),
    tq.measure(0, 3),
  ),
  [\ ], [\ ], [\ ], setwire(2)
)
