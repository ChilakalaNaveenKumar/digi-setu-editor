// Reference 03 — meter variants.
// Plain meter, meter→classical wire, multi-qubit meter, custom body.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(1, meter(), 1)

#v(0.6em)

#quantum-circuit(
  1, meter(target: 1, label: $X$), 1, [\ ],
  setwire(2), 3,
)

#v(0.6em)

#quantum-circuit(
  wires: 2,
  1, meter(n: 2), 1,
)

#v(0.6em)

#let basis-meter(basis) = meter[
  #place(super(baseline: -0.4em, basis))
  #meter-symbol
]

#quantum-circuit(1, basis-meter[X], 1)
