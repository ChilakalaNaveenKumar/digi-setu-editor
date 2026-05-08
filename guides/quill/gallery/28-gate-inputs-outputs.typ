// Gallery 28 — gate with input / output labels.
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  wires: 3,
  1, mqgate($U$, n: 3, width: 5em,
    inputs: (
      (qubit: 0, n: 2, label: $x$),
      (qubit: 2, label: $y$)
    ),
    outputs: (
      (qubit: 0, n: 2, label: $x$),
      (qubit: 2, label: $y plus.o f(x)$)
    ),
  )
)
