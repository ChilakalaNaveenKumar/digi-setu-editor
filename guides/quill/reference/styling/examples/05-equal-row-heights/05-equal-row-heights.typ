// Styling 05 — equal-row-heights.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  equal-row-heights: true,
  row-spacing: 2pt, min-row-height: 4pt,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, $H$, targ(), $H$, 1, [\ ],
  2, ctrl(1), 2, [\ ],
  1, $H$, targ(), $H$, 1
)
