// Decorations 06 — gategroup variants.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($H$), gategroup(2, 3, label: "syndrome", stroke: blue),
  ctrl(1), $H$, $S$, [\ ],
  3, targ(),
)

#v(0.6em)

#quantum-circuit(
  1, $H$, $X$, $Y$, 1,
  gategroup(1, 3, x: 1, y: 0, fill: rgb("#a0d8ff40"),
    label: (content: "phase 1", pos: bottom)),
)
