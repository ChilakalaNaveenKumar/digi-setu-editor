// Decorations 08 — annotate.
// Simple Hadamard label, then a filled polygon across cell centres.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($H$), 1,
  annotate(1, 0, (x, y) => place(
    dx: x, dy: y - 1.2em,
    text(red, size: 8pt)[*Hadamard*],
  ))
)

#v(0.8em)

#quantum-circuit(
  1, $X$, 2, [\ ],
  1, 2, $Y$, [\ ],
  1, 1, $H$, meter(),
  annotate((1.5, 3.5, 2.5), (0.5, 1.5, 2.5), z: "above",
    ((x0, x1, x2), (y0, y1, y2)) => (
      content: polygon(
        (x0, y0), (x1, y1), (x2, y2),
        fill: rgb("#1020EE50"), stroke: .5pt + black
      ),
    ),
  )
)
