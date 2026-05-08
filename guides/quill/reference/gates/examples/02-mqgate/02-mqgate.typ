// Reference 02 — mqgate variants.
// (1) 3-wire bit-flip error gate.
// (2) Pass-through inner wire (n=4 with wire 2 passing through).
// (3) Inputs/outputs labelled inside the gate.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  wires: 3,
  1, mqgate($E$, n: 3), 1,
)

#v(0.6em)

#quantum-circuit(
  wires: 4,
  1, mqgate(
    n: 4,
    fill: none,
    pass-through: (2,),
    $E$
  ), 1
)

#v(0.6em)

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
