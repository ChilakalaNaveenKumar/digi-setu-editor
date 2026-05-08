// Reference 04 — permute() variants.
// Cyclic 3-qubit permutation, then no-bend version.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  wires: 3,
  1, permute(2, 0, 1), 1,
)

#v(0.6em)

#quantum-circuit(
  wires: 3,
  1, permute(2, 0, 1, bend: 0%), 1,
)
