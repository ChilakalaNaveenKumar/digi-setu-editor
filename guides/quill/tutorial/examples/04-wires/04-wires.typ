// Tutorial 04 — wires.
// Quantum, classical (n=2), and bundled (n=4) wires together.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, $A$, meter(n: 1), [\ ],
  setwire(2, stroke: blue), 2, ctrl(), 2, [\ ],
  1, $X$, setwire(0), 1, lstick($|0〉$), setwire(1), $Y$,
)

#v(1em)

#quantum-circuit(
  setwire(4, wire-distance: 1.5pt), 1, $U$, meter()
)
