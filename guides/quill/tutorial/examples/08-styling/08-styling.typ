// Tutorial 08 — circuit styling.
// Dark-mode circuit, scaled-down circuit, equal-row-heights.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#box(fill: black, quantum-circuit(
  wire: .7pt + white,
  color: white,
  fill: black,
  1, $X$, ctrl(1), rstick([*?*]), [\ ],
  1, 1, targ(), meter(),
))

#v(0.6em)

#quantum-circuit(
  scale: 60%,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, 1, targ(), 2
)

#v(0.6em)

#quantum-circuit(
  equal-row-heights: true,
  row-spacing: 2pt, min-row-height: 4pt,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, $H$, targ(), $H$, 1, [\ ],
  2, ctrl(1), 2, [\ ],
  1, $H$, targ(), $H$, 1
)
