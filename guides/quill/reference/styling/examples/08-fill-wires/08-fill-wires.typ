// Styling 08 — fill-wires: true (default) vs false.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, $H$, ctrl(1), 1, [\ ],
  1, 1, targ(),
)

#v(0.6em)

#quantum-circuit(
  fill-wires: false,
  1, $H$, ctrl(1), 1, [\ ],
  1, 1, targ(),
)
