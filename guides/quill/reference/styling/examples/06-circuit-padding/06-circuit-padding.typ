// Styling 06 — circuit-padding (outer padding for annotations).

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  circuit-padding: (top: 12pt, left: 4pt),
  1, gate($H$),
  annotate(1, 0, (x, y) => place(
    dx: x, dy: y - 10pt,
    text(red)[*top label!*],
  )),
)
