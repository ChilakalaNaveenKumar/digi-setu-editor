// Reference 00 — bare quantum-circuit envelope.
// Bell-state preparation: H on q0, CNOT to q1.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  lstick($|0〉$), $H$, ctrl(1), 1, [\ ],
  lstick($|0〉$), 1, targ(),
)
