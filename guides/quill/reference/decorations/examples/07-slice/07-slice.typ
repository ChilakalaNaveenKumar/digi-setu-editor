// Decorations 07 — slice variants.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, $H$, slice(label: "1"), ctrl(1), 1, [\ ],
  1, 1, targ(), 1
)

#v(0.6em)

#quantum-circuit(
  1, $H$, slice(label: "2", n: 2, stroke: blue), ctrl(1), 1, [\ ],
  1, 1, targ(), 1, [\ ],
  3, $X$,
)
