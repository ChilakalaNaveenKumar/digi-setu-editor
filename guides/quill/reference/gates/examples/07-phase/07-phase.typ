// Reference 07 — phase() gate.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, phase($alpha$), 1, phase($beta$, open: true), 1
)
