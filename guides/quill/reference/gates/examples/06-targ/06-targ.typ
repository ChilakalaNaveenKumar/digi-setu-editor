// Reference 06 — targ() — CNOT target.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)
