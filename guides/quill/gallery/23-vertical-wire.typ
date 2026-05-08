// Gallery 23 — plain vertical wire (no dots).
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(1, show-dot: false), 1, [\ ],
  1, ctrl(show-dot: false),    1,
)
