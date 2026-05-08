// Decorations 05 — setwire().
// Switch to classical, cut + restart, then a 3-line bundle.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, $H$, setwire(2), 1, gate($M$), 1
)

#v(0.6em)

#quantum-circuit(
  1, $X$, setwire(0), 1, lstick($|0〉$), setwire(1), $Y$, 1
)

#v(0.6em)

#quantum-circuit(
  setwire(3, wire-distance: 1.5pt), 1, $U$, 1
)
