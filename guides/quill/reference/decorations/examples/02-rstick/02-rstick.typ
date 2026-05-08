// Decorations 02 — rstick variants.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(1, rstick($|0〉$))

#v(0.6em)

#quantum-circuit(
  1, rstick($rho$, n: 2), [\ ],
  1
)

#v(0.6em)

#quantum-circuit(1, rstick($|psi〉$, brace: "]"))
