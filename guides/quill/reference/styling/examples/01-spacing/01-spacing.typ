// Styling 01 — spacing.
// Tight then wide circuit.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  row-spacing: 5pt,
  column-spacing: 5pt,
  gate-padding: 2pt,
  1, $A$, $B$, 1, [\ ],
  1, 1, $S$, 1
)

#v(0.8em)

#quantum-circuit(
  row-spacing: 18pt,
  column-spacing: 18pt,
  gate-padding: 6pt,
  lstick($|0〉$, n: 3), $H$, ctrl(1), ctrl(2), 1, rstick("GHZ", n: 3), [\ ],
  1, $H$, ctrl(), 1, $H$, 1, [\ ],
  1, $H$, 1, ctrl(), $H$, 1
)
