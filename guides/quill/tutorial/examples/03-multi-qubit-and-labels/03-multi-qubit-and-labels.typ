// Tutorial 03 — multi-qubit gates + lstick/rstick.
// Bit-flip error correction circuit from the Quill manual.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  lstick($|psi〉$), ctrl(1), ctrl(2), mqgate($E_"bit"$, n: 3),
    ctrl(1), ctrl(2), targ(), rstick($|psi〉$), [\ ],
  lstick($|0〉$), targ(), 2, targ(), 1, ctrl(-1), 1, [\ ],
  lstick($|0〉$), 1, targ(), 2, targ(), ctrl(-1), 1
)
