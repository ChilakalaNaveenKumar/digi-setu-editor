// Decorations 03 — midstick variants.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(1, midstick($cal(E)$), 1)

#v(0.6em)

#quantum-circuit(
  1, midstick($cal(E)^2$, n: 2), 1, [\ ],
  1, 1
)

#v(0.6em)

#quantum-circuit($H$, midstick($ dots $), $X$)
