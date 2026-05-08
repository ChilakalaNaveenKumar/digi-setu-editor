// Styling 07 — wires: int and wires: array.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  wires: 3,
  1, mqgate($U$, n: 3), 1,
)

#v(0.6em)

#quantum-circuit(
  wires: (1, 1, 2),
  1, $H$, 1, [\ ],
  1, $H$, 1, [\ ],
  1, ctrl(-2, wire-count: 2), 1,
)
