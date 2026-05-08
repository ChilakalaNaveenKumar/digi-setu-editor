// Gallery 27 — many labels around a single gate.
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($Q$, label: (
    (content: "b", pos: top),
    (content: "b", pos: bottom),
    (content: "a", pos: left + top),
    (content: "c", pos: right + top, dy: 0pt, dx: 50%),
  )), 1
)
