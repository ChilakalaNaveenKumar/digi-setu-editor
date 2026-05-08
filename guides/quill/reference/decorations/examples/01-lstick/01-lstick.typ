// Decorations 01 — lstick variants.
// Single-wire, multi-wire (default { brace), forced bracket.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(lstick($|0〉$), 1)

#v(0.6em)

#quantum-circuit(
  lstick($rho$, n: 2), 1, [\ ],
  1
)

#v(0.6em)

#quantum-circuit(lstick($|psi〉$, brace: "["), 1)
