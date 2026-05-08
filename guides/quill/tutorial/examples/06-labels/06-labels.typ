// Tutorial 06 — labels.
// Plain string label, custom position, multi-label dictionary,
// and a wire-label on a CNOT control wire.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($H$, label: "Hadamard"), 1
)

#v(0.6em)

#quantum-circuit(
  1, gate($H$, label: (content: "Hadamard", pos: bottom, dy: 0pt)), 1
)

#v(0.6em)

#quantum-circuit(
  1, gate(hide($H$), label: (
    (content: "lt", pos: left + top),
    (content: "t",  pos: top),
    (content: "rt", pos: right + top),
    (content: "l",  pos: left),
    (content: "c",  pos: center),
    (content: "r",  pos: right),
    (content: "lb", pos: left + bottom),
    (content: "b",  pos: bottom),
    (content: "rb", pos: right + bottom),
  )), 1
)

#v(0.6em)

#quantum-circuit(
  1, ctrl(1, wire-label: $phi$), 2,
    swap(1, wire-label: (
      content: rotate(-90deg, smallcaps("swap")),
      pos: left, dx: 0pt
    )), 1, [\ ], 10pt,
  1, ctrl(), 2, swap(), 1,
)
