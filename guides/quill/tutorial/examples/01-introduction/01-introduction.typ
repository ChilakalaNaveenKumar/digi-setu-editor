// Tutorial 01 — first Quill circuit.
// A Hadamard gate, a phase rotation, then a measurement.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($H$), phase($theta.alt$), meter(), 1
)
