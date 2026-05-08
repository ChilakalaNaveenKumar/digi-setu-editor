// Styling 03 — scale=60% then scale=120%.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  scale: 60%,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, 1, targ(), 2
)

#v(0.6em)

#quantum-circuit(
  scale: 120%,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, 1, targ(), 2
)
