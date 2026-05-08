// Tequila 05 — equivalent of construct-two-qubit-gate (CNOT) using
// the public Quill API in v0.7.2.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)
