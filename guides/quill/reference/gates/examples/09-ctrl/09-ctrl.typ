// Reference 09 — ctrl() variants.
// (1) CNOT, (2) CZ, (3) Open control with classical wire to a measurement.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)

#v(0.6em)

#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, ctrl(),  1,
)

#v(0.6em)

#quantum-circuit(
  1, ctrl(1, open: true, wire-count: 2), 1, [\ ],
  setwire(2), 1, gate($M$), 1,
)
