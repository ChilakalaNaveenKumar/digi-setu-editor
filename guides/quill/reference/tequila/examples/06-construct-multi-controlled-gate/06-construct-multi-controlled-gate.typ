// Tequila 06 — Toffoli (CCX) drawn by hand.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(2), 1, [\ ],
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)
